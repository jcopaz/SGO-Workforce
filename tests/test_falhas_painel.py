"""Teste de ponta a ponta da tela "Falhas" do painel (ADR-0029), via
`streamlit.testing.v1.AppTest` - executa o script real
(`painel/telas/falhas.py`) num runtime Streamlit "bare mode", a diferença
de todos os outros testes de `painel/` (que testam só `dados.py`/
`graficos.py` sem Streamlit, ver docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md).

Único jeito, sem navegador real, de pegar um erro que só aparece quando o
script inteiro roda (import, session_state, ordem dos widgets) - a mesma
classe de risco que já causou o "ImportError no Streamlit Cloud" nunca
reproduzido localmente (ver CHANGELOG). Não substitui teste manual em
navegador/celular real.

ADR-0041: a tela não lê mais "Arquivo local" nem pede URL/token na UI -
fonte de dados é sempre a API (nuvem), com URL/token vindos exclusivamente
de `st.secrets`. Os testes aqui simulam isso via `AppTest.secrets` e
substituem `dados.carregar_jornadas_via_api` por uma versão falsa (nao ha
backend real disponivel no teste).
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

import dados as dados_modulo
from dados import gerar_jornadas_exemplo

_CAMINHO_FALHAS = str(Path(__file__).resolve().parent.parent / "painel" / "telas" / "falhas.py")


def _preparar_secrets_de_teste(at: AppTest) -> None:
    at.secrets["SYNC_API_URL"] = "https://backend-de-teste.invalido"
    at.secrets["SYNC_TOKEN"] = "token-de-teste"


def test_tela_falhas_roda_sem_excecao_com_dados_de_exemplo(tmp_path, monkeypatch):
    # gerar_jornadas_exemplo(quantidade=2) grava exatamente 1 atendimento
    # de falha (na jornada 0) - suficiente para exercitar todo o caminho
    # "com dados", não só o "sem dados" (st.info + st.stop()). Grava em
    # arquivo só pra reaproveitar o gerador existente - a tela em si não
    # lê do diretório, lê do retorno de `carregar_jornadas_via_api`
    # (substituído abaixo).
    jornadas_exemplo = gerar_jornadas_exemplo(tmp_path, quantidade=2)
    monkeypatch.setattr(
        dados_modulo, "carregar_jornadas_via_api", lambda url, token: (jornadas_exemplo, [])
    )

    at = AppTest.from_file(_CAMINHO_FALHAS)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    # 2 tabelas: "Ocorrências por ativo" e "Todos os atendimentos do período".
    assert len(at.dataframe) == 2
    textos = " ".join(m.value for m in at.markdown)
    assert "Total de ocorrências" in textos
    assert "EXEMPLO-1" not in textos  # nota vai na tabela, não no texto solto


def test_tela_falhas_sem_jornada_mostra_info_sem_quebrar(monkeypatch):
    # Backend responde sem nenhuma jornada - caminho "sem dado nenhum",
    # que precisa terminar em st.info + st.stop(), nunca em exceção.
    monkeypatch.setattr(dados_modulo, "carregar_jornadas_via_api", lambda url, token: ([], []))

    at = AppTest.from_file(_CAMINHO_FALHAS)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(m.value for m in at.markdown) + " ".join(i.value for i in at.info)
    assert "Nenhuma jornada no backend ainda" in textos


def test_tela_falhas_sem_secrets_mostra_erro_sem_quebrar():
    # Nenhum secret configurado - precisa avisar com st.error + st.stop(),
    # nunca deixar a tela quebrar tentando chamar a API sem credenciais.
    at = AppTest.from_file(_CAMINHO_FALHAS)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "Backend não configurado" in textos
