"""Teste de ponta a ponta da tela "Visão geral" do painel (Incremento 9),
via `streamlit.testing.v1.AppTest` - mesmo padrão de
`tests/test_falhas_painel.py`, ver docstring lá para a justificativa.

ADR-0041: a tela não lê mais "Arquivo local" nem pede URL/token na UI -
fonte de dados é sempre a API (nuvem), com URL/token vindos exclusivamente
de `st.secrets`. Os testes aqui simulam isso via `AppTest.secrets` e
substituem `dados.carregar_jornadas_via_api` por uma versão falsa (não há
backend real disponível no teste).
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

import dados as dados_modulo
from dados import gerar_jornadas_exemplo

_CAMINHO_DASHBOARD = str(Path(__file__).resolve().parent.parent / "painel" / "telas" / "dashboard.py")


def _preparar_secrets_de_teste(at: AppTest) -> None:
    at.secrets["SYNC_API_URL"] = "https://backend-de-teste.invalido"
    at.secrets["SYNC_TOKEN"] = "token-de-teste"


def test_tela_dashboard_roda_sem_excecao_com_dados_de_exemplo(tmp_path, monkeypatch):
    jornadas_exemplo = gerar_jornadas_exemplo(tmp_path, quantidade=3)
    monkeypatch.setattr(
        dados_modulo, "carregar_jornadas_via_api", lambda url, token: (jornadas_exemplo, [])
    )

    at = AppTest.from_file(_CAMINHO_DASHBOARD)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(m.value for m in at.markdown)
    assert "Jornadas encerradas" in textos
    assert "HH bruto total" in textos


def test_tela_dashboard_sem_jornada_mostra_info_sem_quebrar(monkeypatch):
    monkeypatch.setattr(dados_modulo, "carregar_jornadas_via_api", lambda url, token: ([], []))

    at = AppTest.from_file(_CAMINHO_DASHBOARD)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(m.value for m in at.markdown) + " ".join(i.value for i in at.info)
    assert "Nenhuma jornada encerrada no backend ainda" in textos


def test_tela_dashboard_sem_secrets_mostra_erro_sem_quebrar():
    at = AppTest.from_file(_CAMINHO_DASHBOARD)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "Backend não configurado" in textos
