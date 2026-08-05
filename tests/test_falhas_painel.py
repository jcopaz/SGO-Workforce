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

from datetime import datetime, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

import dados as dados_modulo
from dados import gerar_jornadas_exemplo
from workforce_core import MotorJornada

_CAMINHO_FALHAS = str(Path(__file__).resolve().parent.parent / "painel" / "telas" / "falhas.py")


def _jornada_com_foto_de_falha():
    # ADR-0054: exibicao de foto no painel - upload existia desde o
    # ADR-0022, mas gerar_jornadas_exemplo nunca preenche foto_caminho
    # (nao e o foco dela), entao a jornada de exemplo padrao nunca
    # exercita esse caminho - jornada minima construida direto pelo motor
    # so pra este teste.
    motor = MotorJornada("MATRICULA-FOTO-001")
    inicio = datetime(2026, 8, 1, 8, 0)
    motor.iniciar_jornada(inicio)
    motor.iniciar_atendimento_falha(inicio)
    motor.registrar_dados_falha(
        nota="NOTA-FOTO-1",
        ativo="ATIVO-FOTO",
        sintoma="Sintoma com foto",
        objeto="Componente com foto",
        observacao="Teste com foto.",
        foto_caminho="falhas/2026/08/foto-teste.jpg",
    )
    motor.encerrar_atividade(inicio + timedelta(minutes=30))
    motor.encerrar_jornada(inicio + timedelta(minutes=30))
    return motor.jornada


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


def test_tela_falhas_sem_foto_nao_mostra_secao_de_fotos(tmp_path, monkeypatch):
    # gerar_jornadas_exemplo nunca preenche foto_caminho - a secao "Fotos
    # de atendimentos" so deveria existir quando ha pelo menos um
    # atendimento com foto (ver docstring de falhas.py).
    jornadas_exemplo = gerar_jornadas_exemplo(tmp_path, quantidade=2)
    monkeypatch.setattr(
        dados_modulo, "carregar_jornadas_via_api", lambda url, token: (jornadas_exemplo, [])
    )

    at = AppTest.from_file(_CAMINHO_FALHAS)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    assert not any("Fotos de atendimentos" in exp.label for exp in at.expander)


def test_tela_falhas_com_foto_permite_carregar_via_botao(monkeypatch):
    jornada = _jornada_com_foto_de_falha()
    monkeypatch.setattr(dados_modulo, "carregar_jornadas_via_api", lambda url, token: ([jornada], []))

    chamadas = []

    def _url_foto_falsa(url, token, caminho):
        chamadas.append((url, token, caminho))
        return "https://exemplo.invalido/foto-assinada.jpg"

    monkeypatch.setattr(dados_modulo, "obter_url_foto_falha", _url_foto_falsa)

    at = AppTest.from_file(_CAMINHO_FALHAS)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)
    assert not at.exception
    assert any("Fotos de atendimentos" in exp.label for exp in at.expander)
    assert chamadas == []  # nao busca a URL antes de clicar no botao

    botao_carregar = next(b for b in at.button if b.label == "🖼️ Carregar foto")
    botao_carregar.click().run(timeout=30)

    assert not at.exception
    assert chamadas == [
        ("https://backend-de-teste.invalido", "token-de-teste", "falhas/2026/08/foto-teste.jpg")
    ]


def test_tela_falhas_sem_secrets_mostra_erro_sem_quebrar():
    # Nenhum secret configurado - precisa avisar com st.error + st.stop(),
    # nunca deixar a tela quebrar tentando chamar a API sem credenciais.
    at = AppTest.from_file(_CAMINHO_FALHAS)
    at.run(timeout=30)

    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "Backend não configurado" in textos
