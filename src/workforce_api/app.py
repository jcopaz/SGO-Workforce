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
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from workforce_storage.exceptions import ArquivoCorrompidoError
from workforce_storage.serializacao import jornada_de_dict, jornada_para_dict

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
