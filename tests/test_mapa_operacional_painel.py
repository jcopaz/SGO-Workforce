"""Teste de ponta a ponta da tela "Mapa operacional" do painel
(Incremento 10), via `streamlit.testing.v1.AppTest` - mesmo padrão de
`tests/test_dashboard_painel.py`/`tests/test_falhas_painel.py`, ver
docstring em `test_falhas_painel.py` para a justificativa.

ADR-0042/0043 (Fase 1, backend real de pulsos): a tela não lê mais
diretório local de jornadas/pulsos - fonte de dados é sempre a API
(nuvem), com URL/token vindos exclusivamente de `st.secrets`. Os testes
aqui simulam isso via `AppTest.secrets` e substituem
`dados.carregar_jornadas_via_api`/`dados.carregar_pulsos_via_api` por
versões falsas (não há backend real disponível no teste).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from streamlit.testing.v1 import AppTest

import dados as dados_modulo
from dados import gerar_jornadas_exemplo
from workforce_core.entities import PulsoGps

_CAMINHO_MAPA = str(
    Path(__file__).resolve().parent.parent / "painel" / "telas" / "mapa_operacional.py"
)


def _preparar_secrets_de_teste(at: AppTest) -> None:
    at.secrets["SYNC_API_URL"] = "https://backend-de-teste.invalido"
    at.secrets["SYNC_TOKEN"] = "token-de-teste"


def _pulsos_exemplo(jornada_id):
    base = datetime(2026, 1, 1, 8, 0, 0)
    return [
        PulsoGps(
            jornada_id=jornada_id,
            colaborador_matricula="12345",
            latitude=-23.5505 + i * 0.001,
            longitude=-46.6333,
            precisao_metros=10.0,
            timestamp_dispositivo=base + timedelta(minutes=i),
        )
        for i in range(5)
    ]


def test_tela_mapa_roda_sem_excecao_com_pulsos(tmp_path, monkeypatch):
    jornadas_exemplo = gerar_jornadas_exemplo(tmp_path, quantidade=1)
    jornada = jornadas_exemplo[0]
    pulsos = _pulsos_exemplo(jornada.id)

    monkeypatch.setattr(
        dados_modulo, "carregar_jornadas_via_api", lambda url, token: (jornadas_exemplo, [])
    )
    monkeypatch.setattr(
        dados_modulo,
        "carregar_pulsos_via_api",
        lambda url, token, jornada_id: (pulsos, []),
    )

    at = AppTest.from_file(_CAMINHO_MAPA)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception


def test_tela_mapa_sem_pulsos_mostra_info_sem_quebrar(tmp_path, monkeypatch):
    jornadas_exemplo = gerar_jornadas_exemplo(tmp_path, quantidade=1)

    monkeypatch.setattr(
        dados_modulo, "carregar_jornadas_via_api", lambda url, token: (jornadas_exemplo, [])
    )
    monkeypatch.setattr(
        dados_modulo, "carregar_pulsos_via_api", lambda url, token, jornada_id: ([], [])
    )

    at = AppTest.from_file(_CAMINHO_MAPA)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(i.value for i in at.info)
    assert "Nenhum pulso GPS encontrado" in textos


def test_tela_mapa_sem_jornada_mostra_info_sem_quebrar(monkeypatch):
    monkeypatch.setattr(dados_modulo, "carregar_jornadas_via_api", lambda url, token: ([], []))

    at = AppTest.from_file(_CAMINHO_MAPA)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(i.value for i in at.info)
    assert "Nenhuma jornada encerrada no backend ainda" in textos


def test_tela_mapa_sem_secrets_mostra_erro_sem_quebrar():
    at = AppTest.from_file(_CAMINHO_MAPA)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "Backend não configurado" in textos
