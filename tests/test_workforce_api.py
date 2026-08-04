"""Testes da API de sincronizacao (src/workforce_api/app.py).

Sem Postgres real disponivel neste ambiente de desenvolvimento
(docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md), o repositorio
injetado via app.dependency_overrides e RepositorioJornadaArquivo (ja
testado em tests/test_persistencia.py) apontando para um diretorio
temporario - a API e testada de ponta a ponta sem depender de um banco de
verdade. A conexao real com Postgres continua como validacao pendente.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from workforce_core.catalogo import Categoria, ClassificacaoHH, EntradaCatalogo
from workforce_core.engine import MotorJornada
from workforce_core.entities import PulsoGps
from workforce_storage.repositorio_jornada import RepositorioJornadaArquivo
from workforce_storage.repositorio_pulsos_gps import RepositorioPulsosGpsArquivo
from workforce_storage.serializacao import pulso_gps_para_dict

from workforce_api import supabase_storage as _supabase_storage_modulo
from workforce_api.app import (
    app,
    exigir_token,
    obter_repositorio,
    obter_repositorio_catalogo,
    obter_repositorio_continuacoes,
    obter_repositorio_pulsos,
)

TOKEN_TESTE = "token-de-teste-nao-usar-em-producao"


@pytest.fixture
def cliente_pulsos(tmp_path, monkeypatch):
    # Mesmo espirito da fixture `cliente` (jornadas): sem Postgres real
    # disponivel, injeta RepositorioPulsosGpsArquivo (ja testado em
    # tests/test_gps.py) apontando pra um diretorio temporario no lugar de
    # RepositorioPulsosGpsPostgres - a mesma forma publica (gravar_lote/
    # ler_pulsos) faz a API nao notar diferenca.
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    repositorio = RepositorioPulsosGpsArquivo(tmp_path)
    app.dependency_overrides[obter_repositorio_pulsos] = lambda: repositorio
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(obter_repositorio_pulsos, None)


def _pulso_dict(jornada_id, segundos, **kwargs):
    pulso = PulsoGps(
        jornada_id=jornada_id,
        colaborador_matricula="12345",
        latitude=kwargs.get("lat", 0.0),
        longitude=kwargs.get("lon", 0.0),
        precisao_metros=kwargs.get("precisao", 10.0),
        timestamp_dispositivo=datetime(2026, 1, 1, 8, 0, 0) + timedelta(seconds=segundos),
    )
    return pulso_gps_para_dict(pulso)


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
# /pulsos (ADR-0042/0043 - Fase 1 da captacao real de geolocalizacao) -
# mesmos casos de /jornadas, adaptados pra lote (POST recebe uma lista, nao
# um objeto so) e pra GET exigir jornada_id como query param obrigatorio.
# ----------------------------------------------------------------------
def test_pulsos_post_sem_token_e_401(cliente_pulsos):
    resposta = cliente_pulsos.post("/pulsos", json=[_pulso_dict(uuid4(), 0)])
    assert resposta.status_code == 401


def test_pulsos_post_com_token_errado_e_401(cliente_pulsos):
    resposta = cliente_pulsos.post(
        "/pulsos",
        json=[_pulso_dict(uuid4(), 0)],
        headers={"X-Sync-Token": "token-errado"},
    )
    assert resposta.status_code == 401


def test_pulsos_get_sem_sync_token_configurado_e_503(tmp_path, monkeypatch):
    monkeypatch.delenv("SYNC_TOKEN", raising=False)
    repositorio = RepositorioPulsosGpsArquivo(tmp_path)
    app.dependency_overrides[obter_repositorio_pulsos] = lambda: repositorio
    try:
        cliente = TestClient(app)
        resposta = cliente.get(
            "/pulsos", params={"jornada_id": str(uuid4())}, headers={"X-Sync-Token": "qualquer"}
        )
        assert resposta.status_code == 503
    finally:
        app.dependency_overrides.pop(obter_repositorio_pulsos, None)


def test_pulsos_lote_valido_aparece_no_get_seguinte_em_ordem(cliente_pulsos):
    jornada_id = uuid4()
    headers = {"X-Sync-Token": TOKEN_TESTE}
    # Fora de ordem de proposito (120s depois vem antes de 0s) - o GET
    # precisa devolver em ordem cronologica pelo timestamp do dispositivo,
    # nao pela ordem de chegada no lote.
    lote = [_pulso_dict(jornada_id, 120), _pulso_dict(jornada_id, 0), _pulso_dict(jornada_id, 60)]

    resposta_post = cliente_pulsos.post("/pulsos", json=lote, headers=headers)
    assert resposta_post.status_code == 200
    assert resposta_post.json() == {"status": "recebido", "quantidade": 3}

    resposta_get = cliente_pulsos.get(
        "/pulsos", params={"jornada_id": str(jornada_id)}, headers=headers
    )
    assert resposta_get.status_code == 200
    timestamps = [p["timestamp_dispositivo"] for p in resposta_get.json()]
    assert timestamps == sorted(timestamps)


def test_pulsos_lote_repetido_faz_upsert_sem_duplicar(cliente_pulsos):
    jornada_id = uuid4()
    headers = {"X-Sync-Token": TOKEN_TESTE}
    lote = [_pulso_dict(jornada_id, 0), _pulso_dict(jornada_id, 60)]

    cliente_pulsos.post("/pulsos", json=lote, headers=headers)
    cliente_pulsos.post("/pulsos", json=lote, headers=headers)  # reenvio (ack perdido)

    resposta_get = cliente_pulsos.get(
        "/pulsos", params={"jornada_id": str(jornada_id)}, headers=headers
    )
    assert len(resposta_get.json()) == 2


def test_pulsos_get_so_devolve_da_jornada_pedida(cliente_pulsos):
    jornada_a, jornada_b = uuid4(), uuid4()
    headers = {"X-Sync-Token": TOKEN_TESTE}
    cliente_pulsos.post("/pulsos", json=[_pulso_dict(jornada_a, 0)], headers=headers)
    cliente_pulsos.post("/pulsos", json=[_pulso_dict(jornada_b, 0)], headers=headers)

    resposta = cliente_pulsos.get(
        "/pulsos", params={"jornada_id": str(jornada_a)}, headers=headers
    )
    ids_jornada = {p["jornada_id"] for p in resposta.json()}
    assert ids_jornada == {str(jornada_a)}


def test_pulsos_post_malformado_e_400(cliente_pulsos):
    resposta = cliente_pulsos.post(
        "/pulsos",
        json=[{"id": "nao-e-uuid-valido"}],
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 400


def test_pulsos_get_sem_jornada_id_e_422(cliente_pulsos):
    # jornada_id e query param obrigatorio - FastAPI valida isso sozinho
    # antes mesmo do endpoint rodar.
    resposta = cliente_pulsos.get("/pulsos", headers={"X-Sync-Token": TOKEN_TESTE})
    assert resposta.status_code == 422


def test_pulsos_get_com_jornada_id_invalido_e_400(cliente_pulsos):
    resposta = cliente_pulsos.get(
        "/pulsos", params={"jornada_id": "nao-e-uuid"}, headers={"X-Sync-Token": TOKEN_TESTE}
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


# ----------------------------------------------------------------------
# /catalogo-rasf (sintomas e componentes causadores - docs/48_ADR_0021)
# ----------------------------------------------------------------------
@pytest.fixture
def cliente_rasf(monkeypatch):
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    return TestClient(app)


def test_get_catalogo_rasf_sem_token_e_401(cliente_rasf):
    resposta = cliente_rasf.get("/catalogo-rasf")
    assert resposta.status_code == 401


def test_get_catalogo_rasf_retorna_sintomas_e_componentes_reais(cliente_rasf):
    resposta = cliente_rasf.get("/catalogo-rasf", headers={"X-Sync-Token": TOKEN_TESTE})
    assert resposta.status_code == 200
    dados = resposta.json()

    assert "sintomas" in dados
    assert "componentes_causadores" in dados
    assert len(dados["sintomas"]) == 53
    assert len(dados["componentes_causadores"]) == 148
    assert "FUSÍVEL" in dados["componentes_causadores"]


# ----------------------------------------------------------------------
# /fotos e /fotos/url (upload para Supabase Storage - D3, ver
# docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md)
# ----------------------------------------------------------------------
@pytest.fixture
def cliente_fotos(monkeypatch):
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    return TestClient(app)


def test_post_fotos_sem_token_e_401(cliente_fotos):
    resposta = cliente_fotos.post(
        "/fotos", files={"arquivo": ("foto.jpg", b"conteudo", "image/jpeg")}
    )
    assert resposta.status_code == 401


def test_post_fotos_sucesso_devolve_caminho(cliente_fotos, monkeypatch):
    monkeypatch.setattr(_supabase_storage_modulo, "enviar_foto", lambda *a, **k: "abc-foto.jpg")
    resposta = cliente_fotos.post(
        "/fotos",
        files={"arquivo": ("foto.jpg", b"conteudo", "image/jpeg")},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 200
    assert resposta.json() == {"caminho": "abc-foto.jpg"}


def test_post_fotos_sem_supabase_configurado_e_503(cliente_fotos, monkeypatch):
    def levanta(*_args, **_kwargs):
        raise _supabase_storage_modulo.SupabaseStorageNaoConfiguradoError("sem config")

    monkeypatch.setattr(_supabase_storage_modulo, "enviar_foto", levanta)
    resposta = cliente_fotos.post(
        "/fotos",
        files={"arquivo": ("foto.jpg", b"conteudo", "image/jpeg")},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 503


def test_post_fotos_erro_supabase_e_502(cliente_fotos, monkeypatch):
    def levanta(*_args, **_kwargs):
        raise _supabase_storage_modulo.SupabaseStorageErro("recusado")

    monkeypatch.setattr(_supabase_storage_modulo, "enviar_foto", levanta)
    resposta = cliente_fotos.post(
        "/fotos",
        files={"arquivo": ("foto.jpg", b"conteudo", "image/jpeg")},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 502


def test_get_fotos_url_sem_token_e_401(cliente_fotos):
    resposta = cliente_fotos.get("/fotos/url", params={"caminho": "abc-foto.jpg"})
    assert resposta.status_code == 401


def test_get_fotos_url_sucesso(cliente_fotos, monkeypatch):
    monkeypatch.setattr(
        _supabase_storage_modulo, "gerar_url_assinada", lambda *a, **k: "https://exemplo/url-assinada"
    )
    resposta = cliente_fotos.get(
        "/fotos/url",
        params={"caminho": "abc-foto.jpg"},
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 200
    assert resposta.json() == {"url": "https://exemplo/url-assinada"}


# ----------------------------------------------------------------------
# /continuacoes-falha (transferencia entre colaboradores - D4, ver
# docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md)
# ----------------------------------------------------------------------
class _RepositorioContinuacoesFalso:
    """Repositorio em memoria, mesmo espirito de _RepositorioCatalogoFalso -
    permite testar os endpoints /continuacoes-falha sem Postgres real."""

    def __init__(self):
        self._registros: dict[str, dict] = {}

    def criar(self, matricula_destino, dados):
        from uuid import uuid4

        continuacao_id = uuid4()
        self._registros[str(continuacao_id)] = {
            "matricula_destino": matricula_destino,
            "dados": dados,
            "consumida": False,
        }
        return continuacao_id

    def listar_pendentes(self, matricula_destino):
        return [
            {"id": id_, "dados": registro["dados"]}
            for id_, registro in self._registros.items()
            if registro["matricula_destino"] == matricula_destino and not registro["consumida"]
        ]

    def marcar_consumida(self, continuacao_id):
        registro = self._registros.get(str(continuacao_id))
        if registro:
            registro["consumida"] = True


@pytest.fixture
def cliente_continuacoes(monkeypatch):
    monkeypatch.setenv("SYNC_TOKEN", TOKEN_TESTE)
    repositorio = _RepositorioContinuacoesFalso()
    app.dependency_overrides[obter_repositorio_continuacoes] = lambda: repositorio
    try:
        yield TestClient(app), repositorio
    finally:
        app.dependency_overrides.pop(obter_repositorio_continuacoes, None)


def test_post_continuacoes_falha_sem_token_e_401(cliente_continuacoes):
    cliente, _repositorio = cliente_continuacoes
    resposta = cliente.post(
        "/continuacoes-falha",
        json={"matricula_destino": "99999", "dados": {"nota": "1"}},
    )
    assert resposta.status_code == 401


def test_post_continuacoes_falha_cria_e_aparece_no_get(cliente_continuacoes):
    cliente, _repositorio = cliente_continuacoes
    headers = {"X-Sync-Token": TOKEN_TESTE}
    dados = {"matricula_destino": "99999", "dados": {"nota": "1", "ativo": "A"}}

    resposta_post = cliente.post("/continuacoes-falha", json=dados, headers=headers)
    assert resposta_post.status_code == 200

    resposta_get = cliente.get(
        "/continuacoes-falha", params={"matricula": "99999"}, headers=headers
    )
    assert resposta_get.status_code == 200
    pendentes = resposta_get.json()
    assert len(pendentes) == 1
    assert pendentes[0]["dados"]["nota"] == "1"


def test_get_continuacoes_falha_filtra_por_matricula(cliente_continuacoes):
    cliente, _repositorio = cliente_continuacoes
    headers = {"X-Sync-Token": TOKEN_TESTE}
    cliente.post(
        "/continuacoes-falha",
        json={"matricula_destino": "11111", "dados": {"nota": "1"}},
        headers=headers,
    )

    resposta_get = cliente.get(
        "/continuacoes-falha", params={"matricula": "99999"}, headers=headers
    )
    assert resposta_get.json() == []


def test_post_continuacao_falha_consumir_remove_da_listagem(cliente_continuacoes):
    cliente, _repositorio = cliente_continuacoes
    headers = {"X-Sync-Token": TOKEN_TESTE}
    resposta_post = cliente.post(
        "/continuacoes-falha",
        json={"matricula_destino": "99999", "dados": {"nota": "1"}},
        headers=headers,
    )
    continuacao_id = resposta_post.json()["id"]

    resposta_consumir = cliente.post(
        f"/continuacoes-falha/{continuacao_id}/consumir", headers=headers
    )
    assert resposta_consumir.status_code == 200

    resposta_get = cliente.get(
        "/continuacoes-falha", params={"matricula": "99999"}, headers=headers
    )
    assert resposta_get.json() == []


def test_post_continuacoes_falha_malformado_e_400(cliente_continuacoes):
    cliente, _repositorio = cliente_continuacoes
    resposta = cliente.post(
        "/continuacoes-falha",
        json={"matricula_destino": "99999"},  # falta "dados"
        headers={"X-Sync-Token": TOKEN_TESTE},
    )
    assert resposta.status_code == 400
