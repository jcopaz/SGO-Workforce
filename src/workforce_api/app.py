"""API minima de sincronizacao (Incremento de sincronizacao real - piloto).

Contexto: interface_campo/ (PWA estatico, Cloudflare desde o ADR-0056)
grava jornadas so em IndexedDB do navegador e painel/ (Streamlit) so le
arquivos locais - nao existia nenhuma conexao real entre os dois
(ADR-0003, ADR-0004). Este modulo e o backend que os conecta: recebe
jornadas do app de campo e devolve a lista completa para o painel
consumir.

Decisoes de escopo-piloto (nao design de seguranca final - ver
docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md):
- Autenticacao por token fixo (variavel de ambiente SYNC_TOKEN) comparado
  no header X-Sync-Token. Sem SYNC_TOKEN configurada no servidor, toda
  chamada autenticada e recusada (fail closed, regra de ouro 9 do
  CLAUDE.md) - nunca aceita sem token so porque o servidor esqueceu de
  configurar.
- Persistencia em Postgres hospedado (RepositorioJornadaPostgres),
  injetada via Depends para poder ser substituida por
  RepositorioJornadaArquivo nos testes (sem precisar de Postgres real).
- Granularidade de sincronizacao e a jornada inteira, mesma decisao do
  ADR-0003 (nao ha sincronizacao de eventos individuais).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from workforce_storage.catalogo_rasf import apenas_ativos, carregar_catalogos_rasf
from workforce_storage.exceptions import ArquivoCorrompidoError
from workforce_storage.serializacao import (
    entrada_catalogo_de_dict,
    entrada_catalogo_para_dict,
    jornada_de_dict,
    jornada_para_dict,
    pulso_gps_de_dict,
    pulso_gps_para_dict,
)

from . import supabase_storage
from .repositorio_catalogo_postgres import RepositorioCatalogoPostgres
from .repositorio_continuacoes_postgres import RepositorioContinuacoesFalhaPostgres
from .repositorio_postgres import RepositorioJornadaPostgres
from .repositorio_pulsos_postgres import RepositorioPulsosGpsPostgres

app = FastAPI(title="SGO Workforce - API de sincronizacao (piloto)")

# CORS e enforcado pelo NAVEGADOR, nao pelo servidor - por isso o backend
# respondia normal (WebFetch/curl, sem navegador) mesmo com o app de
# campo real mostrando "sem conexao com o backend": a origem nova do
# Cloudflare (ADR-0056) nao estava na allowlist, so a antiga do Netlify.
# ORIGENS_PERMITIDAS (variavel de ambiente no Render) sobrescreve esta
# lista sem precisar de deploy novo - mas o padrao aqui tambem precisa
# ficar correto, pra quem nunca configurou a variavel (ou esqueceu de
# atualizar numa proxima migracao de hospedagem) nao cair nesse mesmo
# problema de novo.
_origens_padrao = (
    "https://sgoworkforce.mrslogistica.workers.dev,"
    "https://sgoworkforce.netlify.app,"
    "http://localhost:8000"
)
_origens = [
    origem.strip()
    for origem in os.environ.get("ORIGENS_PERMITIDAS", _origens_padrao).split(",")
    if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_repositorio_cache: RepositorioJornadaPostgres | None = None


def obter_repositorio() -> RepositorioJornadaPostgres:
    """Constroi o repositorio Postgres na primeira chamada (a partir de
    DATABASE_URL) e reaproveita a conexao nas seguintes.

    Sobrescrita em testes via app.dependency_overrides, para nao precisar
    de um Postgres real - ver tests/test_workforce_api.py.
    """
    global _repositorio_cache
    if _repositorio_cache is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise HTTPException(
                status_code=503,
                detail="Backend sem DATABASE_URL configurada - nao pode persistir.",
            )
        _repositorio_cache = RepositorioJornadaPostgres(dsn)
    return _repositorio_cache


_repositorio_pulsos_cache: RepositorioPulsosGpsPostgres | None = None


def obter_repositorio_pulsos() -> RepositorioPulsosGpsPostgres:
    """Mesmo padrao de obter_repositorio() - construido na primeira
    chamada, sobrescrito em testes via app.dependency_overrides."""
    global _repositorio_pulsos_cache
    if _repositorio_pulsos_cache is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise HTTPException(
                status_code=503,
                detail="Backend sem DATABASE_URL configurada - nao pode persistir.",
            )
        _repositorio_pulsos_cache = RepositorioPulsosGpsPostgres(dsn)
    return _repositorio_pulsos_cache


_repositorio_catalogo_cache: RepositorioCatalogoPostgres | None = None


def obter_repositorio_catalogo() -> RepositorioCatalogoPostgres:
    """Mesmo padrao de obter_repositorio() - construido na primeira
    chamada, sobrescrito em testes via app.dependency_overrides."""
    global _repositorio_catalogo_cache
    if _repositorio_catalogo_cache is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise HTTPException(
                status_code=503,
                detail="Backend sem DATABASE_URL configurada - nao pode persistir.",
            )
        _repositorio_catalogo_cache = RepositorioCatalogoPostgres(dsn)
    return _repositorio_catalogo_cache


_repositorio_continuacoes_cache: RepositorioContinuacoesFalhaPostgres | None = None


def obter_repositorio_continuacoes() -> RepositorioContinuacoesFalhaPostgres:
    """Mesmo padrao de obter_repositorio()/obter_repositorio_catalogo()."""
    global _repositorio_continuacoes_cache
    if _repositorio_continuacoes_cache is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise HTTPException(
                status_code=503,
                detail="Backend sem DATABASE_URL configurada - nao pode persistir.",
            )
        _repositorio_continuacoes_cache = RepositorioContinuacoesFalhaPostgres(dsn)
    return _repositorio_continuacoes_cache


def exigir_token(x_sync_token: str = Header(default="")) -> None:
    """Fail closed: sem SYNC_TOKEN configurada no servidor, nenhuma
    chamada autenticada e aceita - nunca um "modo aberto" por omissao de
    configuracao."""
    token_esperado = os.environ.get("SYNC_TOKEN")
    if not token_esperado:
        raise HTTPException(
            status_code=503,
            detail="Backend sem SYNC_TOKEN configurado - recusando por seguranca.",
        )
    if x_sync_token != token_esperado:
        raise HTTPException(status_code=401, detail="Token de sincronizacao invalido.")


@app.get("/saude")
def saude() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/jornadas", dependencies=[Depends(exigir_token)])
def receber_jornada(
    dados: Dict[str, Any], repositorio: RepositorioJornadaPostgres = Depends(obter_repositorio)
) -> Dict[str, str]:
    """Upsert idempotente por id (mesma garantia do ADR-0003: reenviar a
    mesma jornada nunca cria um segundo registro)."""
    try:
        jornada = jornada_de_dict(dados)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Jornada malformada: {exc}") from exc
    repositorio.salvar(jornada)
    return {"status": "recebido", "id": str(jornada.id)}


@app.get("/jornadas", dependencies=[Depends(exigir_token)])
def listar_jornadas(
    repositorio: RepositorioJornadaPostgres = Depends(obter_repositorio),
) -> List[Dict[str, Any]]:
    resultado: List[Dict[str, Any]] = []
    for jornada_id in repositorio.listar_ids():
        try:
            jornada = repositorio.carregar(jornada_id)
        except ArquivoCorrompidoError:
            continue
        resultado.append(jornada_para_dict(jornada))
    return resultado


@app.post("/pulsos", dependencies=[Depends(exigir_token)])
def receber_pulsos(
    dados: List[Dict[str, Any]],
    repositorio: RepositorioPulsosGpsPostgres = Depends(obter_repositorio_pulsos),
) -> Dict[str, Any]:
    """Recebe um lote de pulsos GPS (nao um pulso so - a interface de campo
    captura offline e so sincroniza tudo de uma vez ao encerrar a jornada,
    ver docs/70_ADR_0043_DECISOES_CAPTACAO_PERIODICA_PULSO_GPS.md). Upsert
    idempotente por id de cada pulso - reenviar o mesmo lote (ack perdido)
    nunca duplica."""
    try:
        pulsos = [pulso_gps_de_dict(item) for item in dados]
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Pulso malformado: {exc}") from exc
    repositorio.gravar_lote(pulsos)
    return {"status": "recebido", "quantidade": len(pulsos)}


@app.get("/pulsos", dependencies=[Depends(exigir_token)])
def listar_pulsos(
    jornada_id: str,
    repositorio: RepositorioPulsosGpsPostgres = Depends(obter_repositorio_pulsos),
) -> List[Dict[str, Any]]:
    """`jornada_id` e obrigatorio (nunca devolve pulsos de todo mundo de
    uma vez so) - mesmo padrao de GET /continuacoes-falha?matricula=..."""
    try:
        id_uuid = UUID(jornada_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="jornada_id invalido.") from exc
    pulsos = repositorio.ler_pulsos(id_uuid)
    return [pulso_gps_para_dict(pulso) for pulso in pulsos]


@app.post("/pulsos/expurgar", dependencies=[Depends(exigir_token)])
def expurgar_pulsos_antigos(
    dias: int = 90,
    dry_run: bool = True,
    repositorio: RepositorioPulsosGpsPostgres = Depends(obter_repositorio_pulsos),
) -> Dict[str, Any]:
    """Apaga permanentemente pulsos com mais de `dias` dias - mecanismo de
    retencao decidido no ADR-0043 (90 dias, o padrao aqui), implementado
    no ADR-0054. Acao manual (o painel expõe um botao em
    "Configuracoes" com confirmacao explicita) - nao ha agendamento
    automatico neste incremento (sem infraestrutura de cron no piloto).

    `dry_run=True` por padrao (ADR-0057, licao trazida do app irmao
    Gestao_OS: endpoint destrutivo default pra modo seguro) - so conta
    quantos pulsos seriam apagados, nao apaga nada. So apaga de verdade
    com `dry_run=false` explicito, o que o botao do painel ja faz depois
    da confirmacao do usuario.

    `dias < 1` e recusado (400) - protege contra um erro de digitacao
    (0 ou negativo) apagando o historico inteiro por engano. Mesmo token
    fixo dos demais endpoints (fail closed, regra de ouro 9)."""
    if dias < 1:
        raise HTTPException(status_code=400, detail="dias precisa ser pelo menos 1.")
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    if dry_run:
        seriam_apagados = repositorio.contar_pulsos_anteriores_a(data_limite)
        return {"dry_run": True, "seriam_apagados": seriam_apagados}
    apagados = repositorio.apagar_pulsos_anteriores_a(data_limite)
    return {"dry_run": False, "apagados": apagados}


@app.get("/catalogo", dependencies=[Depends(exigir_token)])
def listar_catalogo(
    repositorio: RepositorioCatalogoPostgres = Depends(obter_repositorio_catalogo),
) -> List[Dict[str, Any]]:
    """So retorna motivos ativos - a interface de campo nao deve oferecer
    um motivo desativado pelo admin."""
    return [entrada_catalogo_para_dict(entrada) for entrada in repositorio.listar(somente_ativos=True)]


@app.post("/catalogo", dependencies=[Depends(exigir_token)])
def upsert_catalogo(
    dados: Dict[str, Any],
    repositorio: RepositorioCatalogoPostgres = Depends(obter_repositorio_catalogo),
) -> Dict[str, str]:
    """Upsert por codigo (mesma garantia de idempotencia do ADR-0003) -
    usado pela tela de administracao do catalogo no painel."""
    try:
        entrada = entrada_catalogo_de_dict(dados)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Motivo malformado: {exc}") from exc
    repositorio.salvar(entrada)
    return {"status": "salvo", "codigo": entrada.codigo}


# Diretorio catalogos/ na raiz do repositorio (levado junto no deploy do
# Render, igual ao resto do codigo) - sintomas e componentes causadores do
# RASF, ver docs/48_ADR_0021_ATENDIMENTO_DE_FALHA_CAMPO.md. Sem tabela no
# Postgres: esses catalogos ainda nao tem fluxo de edicao/governanca
# definido (ao contrario do catalogo de motivos, ADR-0019), entao nao faz
# sentido administra-los pelo painel ainda - so servir o que ja existe.
_DIRETORIO_CATALOGOS_RASF = Path(__file__).resolve().parent.parent.parent / "catalogos"
_catalogo_rasf_cache: Optional[Dict[str, List[str]]] = None


def obter_catalogo_rasf() -> Dict[str, List[str]]:
    """Le catalogos/sintomas.csv e catalogos/componentes_causadores.csv
    uma unica vez por processo (os arquivos so mudam com um novo deploy)."""
    global _catalogo_rasf_cache
    if _catalogo_rasf_cache is None:
        catalogos = carregar_catalogos_rasf(_DIRETORIO_CATALOGOS_RASF)
        _catalogo_rasf_cache = {
            "sintomas": sorted(item.valor for item in apenas_ativos(catalogos.get("sintomas", []))),
            "componentes_causadores": sorted(
                item.valor for item in apenas_ativos(catalogos.get("componentes_causadores", []))
            ),
        }
    return _catalogo_rasf_cache


@app.get("/catalogo-rasf", dependencies=[Depends(exigir_token)])
def listar_catalogo_rasf() -> Dict[str, List[str]]:
    return obter_catalogo_rasf()


# ----------------------------------------------------------------------
# Fotos do atendimento de falha (D3 - Supabase Storage, ver
# docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md).
# A service_role key do Supabase fica so aqui (variavel de ambiente do
# backend) - a interface de campo nunca a recebe, so fala com estes dois
# endpoints usando o mesmo token de sincronizacao dos demais.
# ----------------------------------------------------------------------
@app.post("/fotos", dependencies=[Depends(exigir_token)])
async def enviar_foto(arquivo: UploadFile = File(...)) -> Dict[str, str]:
    conteudo = await arquivo.read()
    try:
        caminho = supabase_storage.enviar_foto(
            conteudo,
            arquivo.filename or "foto.jpg",
            arquivo.content_type or "application/octet-stream",
        )
    except supabase_storage.SupabaseStorageNaoConfiguradoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except supabase_storage.SupabaseStorageErro as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"caminho": caminho}


@app.get("/fotos/url", dependencies=[Depends(exigir_token)])
def obter_url_foto(caminho: str) -> Dict[str, str]:
    try:
        url = supabase_storage.gerar_url_assinada(caminho)
    except supabase_storage.SupabaseStorageNaoConfiguradoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except supabase_storage.SupabaseStorageErro as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"url": url}


# ----------------------------------------------------------------------
# Continuacoes de atendimento de falha (D4 - "Falha nao Concluida",
# transferencia entre colaboradores, ver docs/49_ADR_0022).
# ----------------------------------------------------------------------
@app.post("/continuacoes-falha", dependencies=[Depends(exigir_token)])
def criar_continuacao_falha(
    dados: Dict[str, Any],
    repositorio: RepositorioContinuacoesFalhaPostgres = Depends(obter_repositorio_continuacoes),
) -> Dict[str, str]:
    matricula_destino = dados.get("matricula_destino")
    dados_falha = dados.get("dados")
    if not matricula_destino or not isinstance(dados_falha, dict):
        raise HTTPException(
            status_code=400, detail="matricula_destino e dados sao obrigatorios."
        )
    continuacao_id = repositorio.criar(matricula_destino, dados_falha)
    return {"status": "criado", "id": str(continuacao_id)}


@app.get("/continuacoes-falha", dependencies=[Depends(exigir_token)])
def listar_continuacoes_falha(
    matricula: str,
    repositorio: RepositorioContinuacoesFalhaPostgres = Depends(obter_repositorio_continuacoes),
) -> List[Dict[str, Any]]:
    """So devolve continuacoes pendentes (nao consumidas) para a matricula
    informada - a interface de campo chama isto ao iniciar uma jornada."""
    return repositorio.listar_pendentes(matricula)


@app.post("/continuacoes-falha/{continuacao_id}/consumir", dependencies=[Depends(exigir_token)])
def consumir_continuacao_falha(
    continuacao_id: str,
    repositorio: RepositorioContinuacoesFalhaPostgres = Depends(obter_repositorio_continuacoes),
) -> Dict[str, str]:
    try:
        id_uuid = UUID(continuacao_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="id invalido.") from exc
    repositorio.marcar_consumida(id_uuid)
    return {"status": "consumida"}
