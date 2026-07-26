"""Painel gerencial - piloto tecnico (Incremento 9).

Indicadores obrigatorios por perfil, filtros padrao, metas e periodicidade
de atualizacao sao decisoes pendentes
(docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 15.3 "Antes do
Incremento 9"). Este painel mostra apenas o que ja e calculavel com o
motor de dominio existente (Incrementos 1-8), para validar a integracao
tecnica Streamlit + ECharts - nao e o dashboard oficial validado com a
operacao.

Rodar com: streamlit run painel/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests
import streamlit as st
import streamlit.components.v1 as components

from dados import (
    carregar_jornadas,
    carregar_jornadas_via_api,
    formatar_data_hora,
    formatar_horas,
    gerar_jornadas_exemplo,
    montar_resumo,
)
from graficos import grafico_distribuicao_pizza, grafico_hh_por_categoria, renderizar_embutido


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    """Le st.secrets sem derrubar o painel se nao houver secrets.toml
    configurado (uso local, sem Streamlit Cloud)."""
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


st.set_page_config(page_title="SGO Workforce | Painel (piloto)", layout="wide")

st.warning(
    "Piloto tecnico. Indicadores oficiais, filtros padrao, metas e "
    "periodicidade de atualizacao ainda sao decisoes pendentes "
    "(ver docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md). Os numeros "
    "vem do motor de dominio ja testado, mas o conjunto de indicadores "
    "nao foi validado com a operacao."
)

st.title("SGO Workforce | Painel gerencial (piloto)")

if "painel_fonte_dados" not in st.session_state:
    st.session_state.painel_fonte_dados = "Arquivo local"

fonte_dados = st.radio(
    "Fonte de dados",
    ["Arquivo local", "API (nuvem)"],
    key="painel_fonte_dados",
    horizontal=True,
    help=(
        "'Arquivo local' le dados_locais/jornadas nesta maquina. "
        "'API (nuvem)' busca as jornadas sincronizadas pela interface de "
        "campo no backend real (docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md)."
    ),
)

jornadas = []
com_erro = []

if fonte_dados == "Arquivo local":
    if "painel_diretorio_jornadas" not in st.session_state:
        st.session_state.painel_diretorio_jornadas = str(
            _RAIZ_PROJETO / "dados_locais" / "jornadas"
        )

    diretorio = st.text_input(
        "Diretorio de jornadas persistidas",
        key="painel_diretorio_jornadas",
    )

    if not diretorio:
        st.warning("Informe um diretorio de jornadas para continuar.")
        st.stop()

    coluna_exemplo, _coluna_vazia = st.columns([1, 3])
    with coluna_exemplo:
        if st.button("Gerar dados de exemplo (teste)"):
            gerar_jornadas_exemplo(diretorio)
            st.success("Dados de exemplo gravados. Os numeros abaixo ja refletem isso.")

    jornadas, com_erro = carregar_jornadas(diretorio)

    if com_erro:
        st.error(
            f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem "
            f"serem apagados: {', '.join(com_erro)}"
        )

    if not jornadas:
        st.info(
            "Nenhuma jornada encerrada encontrada nesse diretorio. Use o botao "
            "acima para gerar dados de exemplo, ou aponte para um diretorio "
            "gravado pelo motor de dominio (workforce_storage.RepositorioJornadaArquivo)."
        )
        st.stop()
else:
    if "painel_api_url" not in st.session_state:
        st.session_state.painel_api_url = _obter_secret_seguro("SYNC_API_URL")
    if "painel_api_token" not in st.session_state:
        st.session_state.painel_api_token = _obter_secret_seguro("SYNC_TOKEN")

    url_api = st.text_input(
        "URL do backend (ex.: https://sgo-workforce-api.onrender.com)",
        key="painel_api_url",
    )
    token_api = st.text_input(
        "Token de sincronizacao (SYNC_TOKEN)",
        key="painel_api_token",
        type="password",
    )

    if not url_api or not token_api:
        st.warning("Informe a URL do backend e o token de sincronizacao para continuar.")
        st.stop()

    try:
        jornadas, com_erro = carregar_jornadas_via_api(url_api, token_api)
    except requests.exceptions.RequestException as exc:
        st.error(f"Nao foi possivel buscar dados do backend: {exc}")
        st.stop()

    if com_erro:
        st.error(
            f"{len(com_erro)} jornada(s) recebida(s) do backend com estrutura "
            f"invalida, ignorada(s): {', '.join(com_erro)}"
        )

    if not jornadas:
        st.info(
            "Nenhuma jornada encerrada no backend ainda. Registre e sincronize "
            "uma jornada pela interface de campo, ou toque em 'Sincronizar "
            "agora' la se ja tiver uma em andamento."
        )
        st.stop()

resumo = montar_resumo(jornadas)

if resumo.quantidade_jornadas == 0:
    st.info("Ha jornadas no diretorio, mas nenhuma esta encerrada ainda.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jornadas encerradas", resumo.quantidade_jornadas)
c2.metric("HH bruto total", formatar_horas(resumo.jornada_bruta_total))
c3.metric("HH classificado", formatar_horas(resumo.tempo_classificado_total))
c4.metric("HH nao classificado", formatar_horas(resumo.tempo_nao_classificado_total))

st.subheader("Distribuicao de HH por categoria")
col_barra, col_pizza = st.columns(2)
with col_barra:
    components.html(
        renderizar_embutido(grafico_hh_por_categoria(resumo.por_categoria)),
        height=440,
        scrolling=False,
    )
with col_pizza:
    components.html(
        renderizar_embutido(grafico_distribuicao_pizza(resumo.por_categoria)),
        height=440,
        scrolling=False,
    )

st.subheader("Jornadas carregadas")
st.dataframe(
    [
        {
            "Colaborador": j.colaborador_matricula,
            "Estado": j.estado.value,
            "Início": formatar_data_hora(j.inicio),
            "Fim": formatar_data_hora(j.fim),
        }
        for j in jornadas
    ],
    width="stretch",
)
