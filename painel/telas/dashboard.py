"""Painel gerencial - piloto tecnico (Incremento 9, reorganizado no
ADR-0020). Aba "Análise de Dados" > "Visão geral".

Indicadores obrigatorios por perfil, filtros padrao, metas e periodicidade
de atualizacao sao decisoes pendentes
(docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 15.3 "Antes do
Incremento 9"). Este painel mostra apenas o que ja e calculavel com o
motor de dominio existente, para validar a integracao tecnica
Streamlit + ECharts - nao e o dashboard oficial validado com a operacao.
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


def _cartao_kpi(titulo: str, valor: str, subtitulo: str, cor: str = "blue") -> str:
    """HTML do card de KPI no estilo do SGO (painel/estilo.py)."""
    return (
        f'<div class="kpi-header-wrapper kpi-header-card kpi-border-{cor}">'
        f'<div class="kpi-header-title">{titulo}</div>'
        f'<div class="kpi-header-val">{valor}</div>'
        f'<div class="kpi-header-sub badge-{cor}">{subtitulo}</div>'
        f"</div>"
    )


st.warning(
    "Piloto técnico. Indicadores oficiais, filtros padrão, metas e "
    "periodicidade de atualização ainda são decisões pendentes "
    "(ver docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md). Os números "
    "vêm do motor de domínio já testado, mas o conjunto de indicadores "
    "não foi validado com a operação."
)

st.title("SGO Workforce | Visão geral (piloto)")

if "painel_fonte_dados" not in st.session_state:
    st.session_state.painel_fonte_dados = "Arquivo local"

fonte_dados = st.radio(
    "Fonte de dados",
    ["Arquivo local", "API (nuvem)"],
    key="painel_fonte_dados",
    horizontal=True,
    help=(
        "'Arquivo local' lê dados_locais/jornadas nesta máquina. "
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
        "Diretório de jornadas persistidas",
        key="painel_diretorio_jornadas",
    )

    if not diretorio:
        st.warning("Informe um diretório de jornadas para continuar.")
        st.stop()

    coluna_exemplo, _coluna_vazia = st.columns([1, 3])
    with coluna_exemplo:
        if st.button("Gerar dados de exemplo (teste)"):
            gerar_jornadas_exemplo(diretorio)
            st.success("Dados de exemplo gravados. Os números abaixo já refletem isso.")

    jornadas, com_erro = carregar_jornadas(diretorio)

    if com_erro:
        st.error(
            f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem "
            f"serem apagados: {', '.join(com_erro)}"
        )

    if not jornadas:
        st.info(
            "Nenhuma jornada encerrada encontrada nesse diretório. Use o botão "
            "acima para gerar dados de exemplo, ou aponte para um diretório "
            "gravado pelo motor de domínio (workforce_storage.RepositorioJornadaArquivo)."
        )
        st.stop()
else:
    if "painel_api_url" not in st.session_state:
        st.session_state.painel_api_url = _obter_secret_seguro("SYNC_API_URL")
    if "painel_api_token" not in st.session_state:
        st.session_state.painel_api_token = _obter_secret_seguro("SYNC_TOKEN")

    url_api = st.text_input(
        "URL do backend (ex.: https://sgo-workforce.onrender.com)",
        key="painel_api_url",
    )
    token_api = st.text_input(
        "Token de sincronização (SYNC_TOKEN)",
        key="painel_api_token",
        type="password",
    )

    if not url_api or not token_api:
        st.warning("Informe a URL do backend e o token de sincronização para continuar.")
        st.stop()

    try:
        jornadas, com_erro = carregar_jornadas_via_api(url_api, token_api)
    except requests.exceptions.RequestException as exc:
        st.error(f"Não foi possível buscar dados do backend: {exc}")
        st.stop()

    if com_erro:
        st.error(
            f"{len(com_erro)} jornada(s) recebida(s) do backend com estrutura "
            f"inválida, ignorada(s): {', '.join(com_erro)}"
        )

    if not jornadas:
        st.info(
            "Nenhuma jornada encerrada no backend ainda. Registre e sincronize "
            "uma jornada pela interface de campo, ou toque em 'Sincronizar "
            "agora' lá se já tiver uma em andamento."
        )
        st.stop()

st.subheader("Filtros")

_rotulo_sem_categoria = "SEM_CATEGORIA"


def _rotulo_categoria(categoria):
    return categoria.value if categoria is not None else _rotulo_sem_categoria


def _sanitizar_multiselect_state(chave, opcoes_validas):
    """Evita StreamlitAPIException quando as opções de um multiselect
    mudam entre reruns (ex.: trocar a fonte de dados muda a lista de
    colaboradores) e o valor salvo em session_state tem algo que não
    existe mais nas opções atuais - poda o que não é mais válido em vez de
    deixar o widget quebrar."""
    if chave in st.session_state:
        valido = [v for v in st.session_state[chave] if v in opcoes_validas]
        st.session_state[chave] = valido or list(opcoes_validas)


def _sanitizar_periodo_state(chave, minimo, maximo):
    """Mesma ideia de _sanitizar_multiselect_state, para o date_input de
    período: se o valor salvo ficou fora do novo intervalo min/max
    disponível, volta para o intervalo completo."""
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

# st.date_input com intervalo pode devolver só 1 data enquanto o usuário
# ainda está escolhendo o fim do período - usa o intervalo completo nesse
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
    st.info("Há jornadas no período filtrado, mas nenhuma está encerrada ainda.")
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
with c1:
    st.markdown(
        _cartao_kpi("Jornadas encerradas", str(resumo.quantidade_jornadas), "No período filtrado", "blue"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        _cartao_kpi("HH bruto total", formatar_horas(resumo.jornada_bruta_total), "Soma das jornadas", "gray"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        _cartao_kpi(
            "HH classificado", formatar_horas(resumo.tempo_classificado_total), "Atividade + pausas + eventos", "green"
        ),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        _cartao_kpi(
            "HH não classificado", formatar_horas(resumo.tempo_nao_classificado_total), "Lacunas sem evento", "red"
        ),
        unsafe_allow_html=True,
    )

st.subheader("Distribuição de HH por categoria")
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
