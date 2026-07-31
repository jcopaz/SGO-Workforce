"""Falhas - tempo de atendimento (ADR-0029). Aba "Análise de Dados" >
"Falhas".

Preenche a aba "Falhas/RASF" prevista desde `docs/11_TELAS_E_UX.md` e
`docs/12_DASHBOARDS_ECHARTS.md` ("Top sintomas, causas, ações, sistemas,
componentes, impacto, reincidência e HH consumido") mas nunca construída
até este incremento - pedido explícito do responsável do produto, com
uma visão de referência (ranking por duração + KPIs + distribuição por
motivo) de outro painel operacional da MRS.

Mesma disciplina das demais telas: números vêm só do motor de domínio já
testado (`workforce_core.consolidacao`), sem indicador oficial validado
com a operação.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st
import streamlit.components.v1 as components

from dados import (
    carregar_jornadas,
    carregar_jornadas_via_api,
    contagem_atendimentos_por_ativo,
    contagem_atendimentos_por_sintoma,
    formatar_data_hora,
    formatar_horas,
    montar_linhas_atendimento_falha,
    resumo_atendimentos_falha_do_periodo,
)
from graficos import grafico_donut_contagem, grafico_ranking_duracao_falhas, renderizar_embutido


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


def _cartao_kpi(titulo: str, valor: str, subtitulo: str, cor: str = "blue") -> str:
    return (
        f'<div class="kpi-header-wrapper kpi-header-card kpi-border-{cor}">'
        f'<div class="kpi-header-title">{titulo}</div>'
        f'<div class="kpi-header-val">{valor}</div>'
        f'<div class="kpi-header-sub badge-{cor}">{subtitulo}</div>'
        f"</div>"
    )


st.warning(
    "Piloto técnico. Nenhum indicador de falha aqui foi validado com a "
    "operação - ver docs/12_DASHBOARDS_ECHARTS.md. Duração usa o tempo "
    "total decorrido do atendimento (início ao encerramento), não o HH "
    "líquido do colaborador."
)

st.title("SGO Workforce | Falhas - tempo de atendimento (piloto)")

# Mesmas chaves de session_state da Visão geral (painel/telas/dashboard.py)
# - fonte de dados e credenciais da API são configuração global do painel,
# não deveriam pedir para o gestor reconfigurar em cada aba.
if "painel_fonte_dados" not in st.session_state:
    st.session_state.painel_fonte_dados = "Arquivo local"

fonte_dados = st.radio(
    "Fonte de dados",
    ["Arquivo local", "API (nuvem)"],
    key="painel_fonte_dados",
    horizontal=True,
)

jornadas = []
com_erro = []

if fonte_dados == "Arquivo local":
    if "painel_diretorio_jornadas" not in st.session_state:
        st.session_state.painel_diretorio_jornadas = str(_RAIZ_PROJETO / "dados_locais" / "jornadas")

    diretorio = st.text_input("Diretório de jornadas persistidas", key="painel_diretorio_jornadas")
    if not diretorio:
        st.warning("Informe um diretório de jornadas para continuar.")
        st.stop()

    jornadas, com_erro = carregar_jornadas(diretorio)
    if com_erro:
        st.error(
            f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem "
            f"serem apagados: {', '.join(com_erro)}"
        )
    if not jornadas:
        st.info(
            "Nenhuma jornada encontrada nesse diretório. Gere dados de exemplo na "
            "página 'Visão geral' primeiro."
        )
        st.stop()
else:
    if "painel_api_url" not in st.session_state:
        st.session_state.painel_api_url = _obter_secret_seguro("SYNC_API_URL")
    if "painel_api_token" not in st.session_state:
        st.session_state.painel_api_token = _obter_secret_seguro("SYNC_TOKEN")

    url_api = st.text_input("URL do backend", key="painel_api_url")
    token_api = st.text_input("Token de sincronização (SYNC_TOKEN)", key="painel_api_token", type="password")
    if not url_api or not token_api:
        st.warning("Informe a URL do backend e o token de sincronização para continuar.")
        st.stop()

    try:
        jornadas, com_erro = carregar_jornadas_via_api(url_api, token_api)
    except requests.exceptions.RequestException as exc:
        st.error(f"Não foi possível buscar dados do backend: {exc}")
        st.stop()
    if com_erro:
        st.error(f"{len(com_erro)} jornada(s) recebida(s) do backend com estrutura inválida, ignorada(s).")
    if not jornadas:
        st.info("Nenhuma jornada no backend ainda.")
        st.stop()

st.subheader("Filtros")


def _sanitizar_multiselect_state(chave, opcoes_validas):
    if chave in st.session_state:
        valido = [v for v in st.session_state[chave] if v in opcoes_validas]
        st.session_state[chave] = valido or list(opcoes_validas)


def _sanitizar_periodo_state(chave, minimo, maximo):
    if chave in st.session_state:
        valor = st.session_state[chave]
        fora_do_intervalo = not (
            isinstance(valor, tuple)
            and len(valor) == 2
            and minimo <= valor[0] <= maximo
            and minimo <= valor[1] <= maximo
        )
        if fora_do_intervalo:
            st.session_state[chave] = (minimo, maximo)


colaboradores_disponiveis = sorted({j.colaborador_matricula for j in jornadas})
datas_jornada = [j.inicio.date() for j in jornadas if j.inicio is not None]
data_min = min(datas_jornada) if datas_jornada else date.today()
data_max = max(datas_jornada) if datas_jornada else date.today()

# Chaves próprias desta página (não compartilhadas com a Visão geral): o
# conjunto de colaboradores/datas relevante para falhas pode divergir do
# conjunto geral de jornadas.
_sanitizar_multiselect_state("painel_falhas_filtro_colaborador", colaboradores_disponiveis)
_sanitizar_periodo_state("painel_falhas_filtro_periodo", data_min, data_max)

col_f1, col_f2 = st.columns(2)
with col_f1:
    colaboradores_selecionados = st.multiselect(
        "Colaborador",
        colaboradores_disponiveis,
        default=colaboradores_disponiveis,
        key="painel_falhas_filtro_colaborador",
    )
with col_f2:
    intervalo_datas = st.date_input(
        "Período (data de início da jornada)",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
        key="painel_falhas_filtro_periodo",
    )

if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
    data_inicio_filtro, data_fim_filtro = intervalo_datas
else:
    data_inicio_filtro, data_fim_filtro = data_min, data_max

jornadas_filtradas = [
    j
    for j in jornadas
    if j.colaborador_matricula in colaboradores_selecionados
    and j.inicio is not None
    and data_inicio_filtro <= j.inicio.date() <= data_fim_filtro
]

if not jornadas_filtradas:
    st.warning("Nenhuma jornada corresponde aos filtros de colaborador/período selecionados.")
    st.stop()

linhas = montar_linhas_atendimento_falha(jornadas_filtradas)

if not linhas:
    st.info(
        "Nenhum atendimento de falha encontrado no período/colaboradores filtrados. "
        "Atendimentos de falha são registrados na interface de campo com o botão "
        "'Iniciar atendimento de falha'."
    )
    st.stop()

resumo = resumo_atendimentos_falha_do_periodo(linhas)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        _cartao_kpi("Total de ocorrências", str(resumo.quantidade), "No período filtrado", "blue"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        _cartao_kpi(
            "Tempo médio por ocorrência",
            formatar_horas(resumo.duracao_media) if resumo.duracao_media is not None else "--",
            "Início ao encerramento",
            "gray",
        ),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        _cartao_kpi(
            "Maior duração",
            formatar_horas(resumo.maior_duracao) if resumo.maior_duracao is not None else "--",
            "Pior caso do período",
            "red",
        ),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        _cartao_kpi(
            "Duração total das ocorrências",
            formatar_horas(resumo.duracao_total),
            "Soma de todos os atendimentos",
            "green",
        ),
        unsafe_allow_html=True,
    )

st.subheader("Ranking por duração e distribuição por sintoma")
col_ranking, col_donut = st.columns([3, 2])
with col_ranking:
    components.html(
        renderizar_embutido(grafico_ranking_duracao_falhas(linhas)),
        height=500,
        scrolling=False,
    )
with col_donut:
    components.html(
        renderizar_embutido(
            grafico_donut_contagem("Ocorrências por sintoma", contagem_atendimentos_por_sintoma(linhas))
        ),
        height=440,
        scrolling=False,
    )

st.subheader("Ocorrências por ativo")
contagem_ativo = contagem_atendimentos_por_ativo(linhas)
total_ativo = sum(contagem_ativo.values())
st.dataframe(
    [{"Ativo": ativo, "Qtd. registros": quantidade} for ativo, quantidade in sorted(
        contagem_ativo.items(), key=lambda item: item[1], reverse=True
    )]
    + [{"Ativo": "Total", "Qtd. registros": total_ativo}],
    width="stretch",
    hide_index=True,
)

st.subheader("Todos os atendimentos do período")
st.dataframe(
    [
        {
            "Colaborador": linha.colaborador_matricula,
            "Nota": linha.nota or "--",
            "Ativo": linha.ativo or "--",
            "Sintoma": linha.sintoma or "--",
            "Objeto": linha.objeto or "--",
            "Início": formatar_data_hora(linha.inicio),
            "Fim": formatar_data_hora(linha.fim),
            "Duração": formatar_horas(linha.duracao),
        }
        for linha in sorted(linhas, key=lambda linha: linha.duracao, reverse=True)
    ],
    width="stretch",
)
