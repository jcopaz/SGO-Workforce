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
from datetime import date
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests
import streamlit as st
import streamlit.components.v1 as components

from dados import (
    agrupar_duracao_por_categoria,
    carregar_jornadas,
    carregar_jornadas_via_api,
    formatar_data_hora,
    formatar_horas,
    gerar_jornadas_exemplo,
    montar_linhas_eventos,
    montar_resumo,
)
from graficos import (
    grafico_distribuicao_pizza,
    grafico_evolucao_diaria,
    grafico_hh_por_categoria,
    grafico_hh_por_colaborador,
    grafico_motivos_treemap,
    renderizar_embutido,
)


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

st.subheader("Filtros")

_rotulo_sem_categoria = "SEM_CATEGORIA"


def _rotulo_categoria(categoria):
    return categoria.value if categoria is not None else _rotulo_sem_categoria


def _sanitizar_multiselect_state(chave, opcoes_validas):
    """Evita StreamlitAPIException quando as opcoes de um multiselect
    mudam entre reruns (ex.: trocar a fonte de dados muda a lista de
    colaboradores) e o valor salvo em session_state tem algo que nao
    existe mais nas opcoes atuais - poda o que nao e mais valido em vez de
    deixar o widget quebrar."""
    if chave in st.session_state:
        valido = [v for v in st.session_state[chave] if v in opcoes_validas]
        st.session_state[chave] = valido or list(opcoes_validas)


def _sanitizar_periodo_state(chave, minimo, maximo):
    """Mesma ideia de _sanitizar_multiselect_state, para o date_input de
    periodo: se o valor salvo ficou fora do novo intervalo min/max
    disponivel, volta para o intervalo completo."""
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

_sanitizar_multiselect_state("painel_filtro_colaborador", colaboradores_disponiveis)
_sanitizar_periodo_state("painel_filtro_periodo", data_min, data_max)

col_f1, col_f2 = st.columns(2)
with col_f1:
    colaboradores_selecionados = st.multiselect(
        "Colaborador",
        colaboradores_disponiveis,
        default=colaboradores_disponiveis,
        key="painel_filtro_colaborador",
    )
with col_f2:
    intervalo_datas = st.date_input(
        "Período (data de início da jornada)",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
        key="painel_filtro_periodo",
    )

# st.date_input com intervalo pode devolver so 1 data enquanto o usuario
# ainda esta escolhendo o fim do periodo - usa o intervalo completo nesse
# meio tempo em vez de quebrar o filtro.
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

resumo = montar_resumo(jornadas_filtradas)

if resumo.quantidade_jornadas == 0:
    st.info("Ha jornadas no periodo filtrado, mas nenhuma esta encerrada ainda.")
    st.stop()

linhas = montar_linhas_eventos(jornadas_filtradas)

categorias_disponiveis = sorted({_rotulo_categoria(linha.categoria) for linha in linhas})
motivos_disponiveis = sorted({linha.motivo for linha in linhas if linha.motivo is not None})

_sanitizar_multiselect_state("painel_filtro_categoria", categorias_disponiveis)
_sanitizar_multiselect_state("painel_filtro_motivo", motivos_disponiveis)

col_f3, col_f4 = st.columns(2)
with col_f3:
    categorias_selecionadas = st.multiselect(
        "Categoria",
        categorias_disponiveis,
        default=categorias_disponiveis,
        key="painel_filtro_categoria",
    )
with col_f4:
    motivos_selecionados = st.multiselect(
        "Motivo/justificativa (pausas e deslocamento/espera/apoio)",
        motivos_disponiveis,
        default=motivos_disponiveis,
        key="painel_filtro_motivo",
    )

linhas_filtradas = [
    linha
    for linha in linhas
    if _rotulo_categoria(linha.categoria) in categorias_selecionadas
    and (linha.motivo is None or linha.motivo in motivos_selecionados)
]

if not linhas_filtradas:
    st.warning("Nenhum evento corresponde aos filtros de categoria/motivo selecionados.")
    st.stop()

por_categoria_filtrado = agrupar_duracao_por_categoria(linhas_filtradas)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jornadas encerradas", resumo.quantidade_jornadas)
c2.metric("HH bruto total", formatar_horas(resumo.jornada_bruta_total))
c3.metric("HH classificado", formatar_horas(resumo.tempo_classificado_total))
c4.metric("HH nao classificado", formatar_horas(resumo.tempo_nao_classificado_total))

st.subheader("Distribuicao de HH por categoria")
col_barra, col_pizza = st.columns(2)
with col_barra:
    components.html(
        renderizar_embutido(grafico_hh_por_categoria(por_categoria_filtrado)),
        height=440,
        scrolling=False,
    )
with col_pizza:
    components.html(
        renderizar_embutido(grafico_distribuicao_pizza(por_categoria_filtrado)),
        height=440,
        scrolling=False,
    )

st.subheader("Evolução diária e por colaborador")
col_evolucao, col_colaborador = st.columns(2)
with col_evolucao:
    components.html(
        renderizar_embutido(grafico_evolucao_diaria(linhas_filtradas)),
        height=440,
        scrolling=False,
    )
with col_colaborador:
    components.html(
        renderizar_embutido(grafico_hh_por_colaborador(linhas_filtradas)),
        height=440,
        scrolling=False,
    )

st.subheader("HH por motivo/justificativa")
components.html(
    renderizar_embutido(grafico_motivos_treemap(linhas_filtradas)),
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
        for j in jornadas_filtradas
    ],
    width="stretch",
)
