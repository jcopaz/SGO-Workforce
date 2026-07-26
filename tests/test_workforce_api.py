"""Testes da API de sincronizacao (src/workforce_api/app.py).

Sem Postgres real disponivel neste ambiente de desenvolvimento
(docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md), o repositorio
injetado via app.dependency_overrides e RepositorioJornadaArquivo (ja
testado em tests/test_persistencia.py) apontando para um diretorio
temporario - a API e testada de ponta a ponta sem depender de um banco de
verdade. A conexao real com Postgres continua como validacao pendente.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from workforce_core.catalogo import Categoria, ClassificacaoHH, EntradaCatalogo
from workforce_core.engine import MotorJornada
from workforce_storage.repositorio_jornada import RepositorioJornadaArquivo

from workforce_api.app import app, exigir_token, obter_repositorio, obter_repositorio_catalogo

TOKEN_TESTE = "token-de-teste-nao-usar-em-producao"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    repositorio = RepositorioJornadaArquivo(tmp_path)
    app.dependency_overrides[obter_repositorio] = lambda: repositorio
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(obter_repositorio, None)


class _RepositorioCatalogoFalso:
    """Repositorio de catalogo em memoria, mesmo espirito de
    RepositorioJornadaArquivo nos testes de /jornadas - permite testar os
    endpoints /catalogo sem Postgres real."""

    def __init__(self):
        self._entradas: dict[str, EntradaCatalogo] = {}

    def salvar(self, entrada: EntradaCatalogo) -> None:
        self._entradas[entrada.codigo] = entrada

    def listar(self, *, somente_ativos: bool = True):
        valores = list(self._entradas.values())
        if somente_ativos:
            valores = [entrada for entrada in valores if entrada.ativo]
        return sorted(valores, key=lambda entrada: entrada.codigo)


@pytest.fixture
def cliente_catalogo(monkeypatch):
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    repositorio = _RepositorioCatalogoFalso()
    app.dependency_overrides[obter_repositorio_catalogo] = lambda: repositorio
    try:
        yield TestClient(app), repositorio
    finally:
        app.dependency_overrides.pop(obter_repositorio_catalogo, None)


def _jornada_encerrada_dict():
    from datetime import datetime

    motor = MotorJornada("12345")
    motor.iniciar_jornada(datetime(2026, 1, 1, 8, 0))
    motor.iniciar_atividade(datetime(2026, 1, 1, 8, 10))
    motor.encerrar_atividade(datetime(2026, 1, 1, 12, 0))
    motor.encerrar_jornada(datetime(2026, 1, 1, 12, 10))

    from workforce_storage.serializacao import jornada_para_dict

    return jornada_para_dict(motor.jornada)


def test_saude_nao_exige_token(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_post_sem_token_e_401(cliente):
    resposta = cliente.post("/jornadas", json=_jornada_encerrada_dict())
    assert resposta.status_code == 401


def test_post_com_token_errado_e_401(cliente):
    resposta = cliente.post(
        "/jornadas",
        json=_jornada_encerrada_dict(),
        headers={"X-Sync-Token": "token-errado"},
    )
    assert resposta.status_code == 401


def test_get_sem_sync_token_configurado_e_503(tmp_path, monkeypatch):
    monkeypatch.delenv("SYNC_TOKEN", raising=False)
    repositorio = RepositorioJornadaArquivo(tmp_path)
    app.dependency_overrides[obter_repositorio] = lambda: repositorio
    try:
        cliente = TestClient(app)
        resposta = cliente.get("/jornadas", headers={"X-Sync-Token": "qualquer"})
        assert resposta.status_code == 503
    finally:
        app.dependency_overrides.pop(obter_repositorio, None)


def test_post_valido_aparece_no_get_seguinte(cliente):
    dados = _jornada_encerrada_dict()

    resposta_post = cliente.post(
        "/jornadas", json=dados, headers={"X-Sync-Token": TOKEN_TESTE}
    )
    assert resposta_post.status_code == 200
    assert resposta_post.json()["id"] == dados["id"]

    resposta_get = cliente.get("/jornadas", headers={"X-Sync-Token": TOKEN_TESTE})
    assert resposta_get.status_code == 200
    ids_recebidos = [j["id"] for j in resposta_get.json()]
    assert dados["id"] in ids_recebidos


def test_post_repetido_faz_upsert_sem_duplicar(cliente):
    dados = _jornada_encerrada_dict()
    headers = {"X-Sync-Token": TOKEN_TESTE}

    cliente.post("/jornadas", json=dados, headers=headers)
    cliente.post("/jornadas", json=dados, headers=headers)

    resposta_get = cliente.get("/jornadas", headers=headers)
    ids_recebidos = [j["id"] for j in resposta_get.json()]
    assert ids_recebidos.count(dados["id"]) == 1


def test_post_malformado_e_400(cliente):
    resposta = cliente.post(
        "/jornadas",
        json={"id": "nao-e-uuid-valido"},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 400


# ----------------------------------------------------------------------
# /catalogo (catalogo dinamico de motivos - docs/46_ADR_0019)
# ----------------------------------------------------------------------
def test_get_catalogo_sem_token_e_401(cliente_catalogo):
    cliente, _repositorio = cliente_catalogo
    resposta = cliente.get("/catalogo")
    assert resposta.status_code == 401


def test_post_catalogo_cria_e_aparece_no_get(cliente_catalogo):
    cliente, _repositorio = cliente_catalogo
    headers = {"X-Sync-Token": TOKEN_TESTE}
    dados = {
        "codigo": "EE99",
        "descricao": "Motivo de teste",
        "categoria": Categoria.REUNIAO.value,
        "classificacao_hh": ClassificacaoHH.NAO_DEFINIDO.value,
        "tipo_registro": "pausa",
        "ativo": True,
    }

    resposta_post = cliente.post("/catalogo", json=dados, headers=headers)
    assert resposta_post.status_code == 200
    assert resposta_post.json()["codigo"] == "EE99"

    resposta_get = cliente.get("/catalogo", headers=headers)
    assert resposta_get.status_code == 200
    codigos = [motivo["codigo"] for motivo in resposta_get.json()]
    assert "EE99" in codigos


def test_post_catalogo_upsert_nao_duplica(cliente_catalogo):
    cliente, _repositorio = cliente_catalogo
    headers = {"X-Sync-Token": TOKEN_TESTE}
    dados = {"codigo": "EE99", "descricao": "V1", "tipo_registro": "pausa"}

    cliente.post("/catalogo", json=dados, headers=headers)
    dados["descricao"] = "V2"
    cliente.post("/catalogo", json=dados, headers=headers)

    resposta_get = cliente.get("/catalogo", headers=headers)
    motivos = [m for m in resposta_get.json() if m["codigo"] == "EE99"]
    assert len(motivos) == 1
    assert motivos[0]["descricao"] == "V2"


def test_get_catalogo_omite_inativos(cliente_catalogo):
    cliente, repositorio = cliente_catalogo
    repositorio.salvar(EntradaCatalogo(codigo="EE00", descricao="Inativo", ativo=False))

    resposta_get = cliente.get("/catalogo", headers={"X-Sync-Token": TOKEN_TESTE})
    codigos = [motivo["codigo"] for motivo in resposta_get.json()]
    assert "EE00" not in codigos


def test_post_catalogo_malformado_e_400(cliente_catalogo):
    cliente, _repositorio = cliente_catalogo
    resposta = cliente.post(
        "/catalogo",
        json={"descricao": "sem codigo obrigatorio"},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 400
