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

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import dados as dados_modulo
from dados import gerar_jornadas_exemplo
from workforce_core.entities import PulsoGps

_CAMINHO_MAPA = str(
    Path(__file__).resolve().parent.parent / "painel" / "telas" / "mapa_operacional.py"
)


@pytest.fixture(autouse=True)
def _limpar_cache_do_mapa():
    # painel/telas/mapa_operacional.py cacheia as chamadas de API com
    # `st.cache_data` (ADR-0049, fluidez) - o cache e por processo, nao
    # por instancia de AppTest, entao sem isso um teste vaza jornada/pulso
    # em cache pro proximo (todos usam a mesma URL/token fake de
    # `_preparar_secrets_de_teste`, mesma chave de cache).
    st.cache_data.clear()
    yield


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


# ----------------------------------------------------------------------
# Filtro de atividade/data/horario (ADR-0047, pedido do responsavel pelo
# produto em 2026-08-04). Os 5 pulsos de _pulsos_exemplo (8:00-8:04) caem
# dentro do evento secundario "DESLOCAMENTO_TESTE" (8:00-8:30) que
# gerar_jornadas_exemplo sempre cria - por isso o rotulo esperado no
# filtro e literalmente o codigo do motivo de teste (catalogo_completo()
# nao conhece "DESLOCAMENTO_TESTE", cai no proprio codigo - ver
# painel/dados.py::rotulo_motivo).
# ----------------------------------------------------------------------
def _preparar_tela_com_pulsos(tmp_path, monkeypatch):
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
    return at


def test_tela_mapa_filtro_atividade_lista_rotulos_presentes(tmp_path, monkeypatch):
    at = _preparar_tela_com_pulsos(tmp_path, monkeypatch)

    assert not at.exception
    seletor_atividade = at.selectbox(key="painel_mapa_filtro_atividade")
    assert "Todas as atividades" in seletor_atividade.options
    assert any(opcao.startswith("DESLOCAMENTO_TESTE") for opcao in seletor_atividade.options)


def test_tela_mapa_filtro_atividade_especifica_nao_quebra(tmp_path, monkeypatch):
    # set_value(date(...)) do date_input nao propaga de forma confiavel
    # neste AppTest/versao do Streamlit (reproduzido isolado, fora deste
    # app - bug/limitacao da propria ferramenta de teste, nao do app) -
    # o filtro de atividade (Selectbox.select) funciona normalmente, e a
    # correcao do filtro de data/horario em si ja e coberta por
    # tests/test_mapa.py::test_filtrar_pulsos_por_periodo_* (funcao pura).
    at = _preparar_tela_com_pulsos(tmp_path, monkeypatch)
    opcao_atividade = next(
        opcao
        for opcao in at.selectbox(key="painel_mapa_filtro_atividade").options
        if opcao.startswith("DESLOCAMENTO_TESTE")
    )

    at.selectbox(key="painel_mapa_filtro_atividade").select(opcao_atividade).run(timeout=30)

    assert not at.exception
    # os 5 pulsos de teste caem todos dentro do mesmo evento secundario -
    # filtrar por ele nao deveria excluir nenhum.
    textos_caption = " ".join(c.value for c in at.caption)
    assert "5 de 5 pulso(s)" in textos_caption
