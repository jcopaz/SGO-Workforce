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
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from dados import gerar_jornadas_exemplo

_CAMINHO_FALHAS = str(Path(__file__).resolve().parent.parent / "painel" / "telas" / "falhas.py")


def test_tela_falhas_roda_sem_excecao_com_dados_de_exemplo(tmp_path):
    # gerar_jornadas_exemplo(quantidade=2) grava exatamente 1 atendimento
    # de falha (na jornada 0) - suficiente para exercitar todo o caminho
    # "com dados", não só o "sem dados" (st.info + st.stop()).
    gerar_jornadas_exemplo(tmp_path, quantidade=2)

    at = AppTest.from_file(_CAMINHO_FALHAS)
    at.session_state["painel_fonte_dados"] = "Arquivo local"
    at.session_state["painel_diretorio_jornadas"] = str(tmp_path)
    at.run(timeout=30)

    assert not at.exception
    # 2 tabelas: "Ocorrências por ativo" e "Todos os atendimentos do período".
    assert len(at.dataframe) == 2
    textos = " ".join(m.value for m in at.markdown)
    assert "Total de ocorrências" in textos
    assert "EXEMPLO-1" not in textos  # nota vai na tabela, não no texto solto


def test_tela_falhas_sem_jornada_mostra_info_sem_quebrar(tmp_path):
    # Diretorio vazio (nenhuma jornada persistida) - caminho "sem dado
    # nenhum", que precisa terminar em st.info + st.stop(), nunca em
    # excecao.
    at = AppTest.from_file(_CAMINHO_FALHAS)
    at.session_state["painel_fonte_dados"] = "Arquivo local"
    at.session_state["painel_diretorio_jornadas"] = str(tmp_path)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(m.value for m in at.markdown) + " ".join(i.value for i in at.info)
    assert "Nenhuma jornada encontrada" in textos
