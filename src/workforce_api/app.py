"""API minima de sincronizacao (Incremento de sincronizacao real - piloto).

Contexto: interface_campo/ (PWA no Netlify) grava jornadas so em IndexedDB
do navegador e painel/ (Streamlit) so le arquivos locais - nao existia
nenhuma conexao real entre os dois (ADR-0003, ADR-0004). Este modulo e o
backend que os conecta: recebe jornadas do app de campo e devolve a lista
completa para o painel consumir.

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
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from workforce_storage.catalogo_rasf import apenas_ativos, carregar_catalogos_rasf
from workforce_storage.exceptions import ArquivoCorrompidoError
from workforce_storage.serializacao import (
    entrada_catalogo_de_dict,
    entrada_catalogo_para_dict,
    jornada_de_dict,
    jornada_para_dict,
)

from .repositorio_catalogo_postgres import RepositorioCatalogoPostgres
from .repositorio_postgres import RepositorioJornadaPostgres

app = FastAPI(title="SGO Workforce - API de sincronizacao (piloto)")

_origens_padrao = "https://sgoworkforce.netlify.app,http://localhost:8000"
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
