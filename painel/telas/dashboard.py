"""Painel gerencial - piloto tecnico (Incremento 9, reorganizado no
ADR-0020, dashboard ampliado no ADR-0031). Aba "Análise de Dados" >
"Visão geral".

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
    carregar_jornadas_via_api,
    contagem_e_duracao_media_por_motivo,
    fatiar_linha_do_tempo_por_dia,
    formatar_data_hora,
    formatar_horas,
    horas_produtiva_nao_rentavel_do_resumo,
    montar_linhas_eventos,
    montar_resumo,
    rotulo_categoria,
    utilizacao_hh_do_resumo,
    utilizacao_hh_por_colaborador,
)
from graficos import (
    grafico_distribuicao_pizza,
    grafico_evolucao_diaria,
    grafico_gauge_percentual,
    grafico_hh_por_categoria,
    grafico_hh_por_colaborador,
    grafico_hh_por_motivo,
    grafico_linha_do_tempo,
    grafico_sankey_colaborador_categoria,
    grafico_scatter_duracao_frequencia,
    grafico_utilizacao_por_colaborador,
    renderizar_embutido,
)
from workforce_core.consolidacao import linha_do_tempo


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

col_titulo, col_sync = st.columns([5, 1])
with col_titulo:
    st.title("SGO Workforce | Visão geral (piloto)")
with col_sync:
    st.write("")  # alinhamento vertical com o titulo
    if st.button("🔄 Sincronizar dados", width="stretch"):
        st.toast("Sincronizando com o backend...", icon="🔄")

# Fonte de dados fixa em API (nuvem, ADR-0041) - pedido explicito do
# responsavel do produto: os dados sempre vem do backend sincronizado
# pela interface de campo, "Arquivo local" so existia pra
# desenvolvimento/teste. Sem selecao visivel de fonte/URL/token - as
# credenciais vem exclusivamente de st.secrets (nunca digitadas na
# tela). O botao "Sincronizar dados" acima e so uma reafirmacao visual:
# toda interacao (filtro, botao, o que for) ja dispara um rerun do
# Streamlit, que ja busca os dados de novo no backend - nao ha cache
# aqui ainda, entao os dados ja estao sempre atualizados sem esse
# botao. Ver docs/*_ADR_0041_*.md.
url_api = _obter_secret_seguro("SYNC_API_URL")
token_api = _obter_secret_seguro("SYNC_TOKEN")

if not url_api or not token_api:
    st.error(
        "Backend não configurado. Defina os secrets `SYNC_API_URL` e "
        "`SYNC_TOKEN` (Streamlit Cloud: Settings → Secrets) para o "
        "painel funcionar."
    )
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


def _sanitizar_selectbox_state(chave, opcoes_validas):
    """Mesma ideia de _sanitizar_multiselect_state, para um st.selectbox
    de valor unico (ADR-0051: seletor de colaborador da linha do tempo,
    que precisa ficar dentro do que o multiselect principal ja escolheu,
    e esse conjunto muda entre reruns)."""
    if chave in st.session_state and st.session_state[chave] not in opcoes_validas:
        st.session_state[chave] = opcoes_validas[0] if opcoes_validas else None


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

categorias_disponiveis = sorted({rotulo_categoria(linha.categoria) for linha in linhas})
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
    if rotulo_categoria(linha.categoria) in categorias_selecionadas
    and (linha.motivo is None or linha.motivo in motivos_selecionados)
]

if not linhas_filtradas:
    st.warning("Nenhum evento corresponde aos filtros de categoria/motivo selecionados.")
    st.stop()

por_categoria_filtrado = agrupar_duracao_por_categoria(linhas_filtradas)
fracao_utilizacao_hh = utilizacao_hh_do_resumo(resumo)
horas_produtiva_nao_rentavel = horas_produtiva_nao_rentavel_do_resumo(resumo)

c1, c2, c3, c4, c5, c6 = st.columns(6)
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
with c5:
    st.markdown(
        _cartao_kpi(
            "Utilização HH",
            f"{fracao_utilizacao_hh * 100:.1f}%" if fracao_utilizacao_hh is not None else "--",
            "Rentável / Total (ADR-0027)",
            "blue",
        ),
        unsafe_allow_html=True,
    )
with c6:
    st.markdown(
        _cartao_kpi(
            "HH produtivo não rentável",
            formatar_horas(horas_produtiva_nao_rentavel),
            "Deslocamento, preparo, treinamento etc. (ADR-0028)",
            "gray",
        ),
        unsafe_allow_html=True,
    )

with st.expander("Indicadores", expanded=True):
    col_gauge, col_performance = st.columns(2)
    with col_gauge:
        if fracao_utilizacao_hh is None:
            st.info("Sem HH bruto no período filtrado para calcular Utilização HH.")
        else:
            st.caption("Utilização HH (Produtivo rentável / Total)")
            components.html(
                renderizar_embutido(grafico_gauge_percentual("Utilização HH", fracao_utilizacao_hh)),
                height=340,
                scrolling=False,
            )
    with col_performance:
        st.info(
            "Performance (Tempo Planejado / Tempo Real) ainda não aparece aqui: "
            "o sistema não tem, hoje, nenhuma fonte de tempo planejado por "
            "atividade/OS (ver docs/23_DECISOES_PENDENTES.md). A fórmula já "
            "está pronta em `workforce_core.consolidacao.performance` para "
            "quando essa fonte existir."
        )

with st.expander("Produtividade por colaborador", expanded=True):
    st.caption(
        "Utilização HH individual - quem está convertendo mais período de "
        "trabalho em manutenção rentável (EE17/EE21), no mesmo filtro de "
        "colaborador/período acima."
    )
    utilizacao_por_colaborador = utilizacao_hh_por_colaborador(jornadas_filtradas)
    components.html(
        renderizar_embutido(grafico_utilizacao_por_colaborador(utilizacao_por_colaborador)),
        height=530,
        scrolling=False,
    )

with st.expander("Distribuição de HH por categoria", expanded=True):
    # Barra em largura cheia (nao em coluna): ate 19 categorias com
    # rotulo rotacionado precisam de largura de verdade - espremer num
    # meio de tela reabriria o mesmo risco de rotulo cortado que motivou
    # o ADR-0032/0033 (grid com containLabel evita o corte, mas nao evita
    # o rotulo ficar ilegivel de tao comprimido).
    st.caption("HH por categoria")
    components.html(
        renderizar_embutido(grafico_hh_por_categoria(por_categoria_filtrado)),
        height=560,
        scrolling=False,
    )
    st.caption("Distribuição percentual")
    components.html(
        renderizar_embutido(grafico_distribuicao_pizza(por_categoria_filtrado)),
        height=560,
        scrolling=False,
    )

with st.expander("Evolução diária de HH", expanded=True):
    components.html(
        renderizar_embutido(grafico_evolucao_diaria(linhas_filtradas)),
        height=480,
        scrolling=False,
    )

with st.expander("Duração média x frequência por motivo", expanded=True):
    dados_motivo = contagem_e_duracao_media_por_motivo(linhas_filtradas)
    if not dados_motivo:
        st.info("Nenhum evento com motivo (pausa/deslocamento/espera/apoio) no filtro atual.")
    else:
        components.html(
            renderizar_embutido(grafico_scatter_duracao_frequencia(dados_motivo)),
            height=520,
            scrolling=False,
        )

with st.expander("HH por colaborador (detalhado por categoria)", expanded=True):
    components.html(
        renderizar_embutido(grafico_hh_por_colaborador(linhas_filtradas)),
        height=560,
        scrolling=False,
    )

with st.expander("HH por motivo/justificativa", expanded=True):
    _grafico_motivo, _altura_motivo = grafico_hh_por_motivo(linhas_filtradas)
    components.html(
        renderizar_embutido(_grafico_motivo),
        height=_altura_motivo + 30,
        scrolling=False,
    )

with st.expander("Fluxo de HH: colaborador → categoria", expanded=True):
    components.html(
        renderizar_embutido(grafico_sankey_colaborador_categoria(linhas_filtradas)),
        height=620,
        scrolling=False,
    )

with st.expander("Linha do tempo do colaborador", expanded=True):
    st.caption(
        "Sequência de apontamentos ao longo dos dias, no horário real em que "
        "aconteceram - todos os dias do período filtrado acima para o "
        "colaborador escolhido aqui."
    )
    _sanitizar_selectbox_state("painel_linha_tempo_colaborador", colaboradores_selecionados)
    colaborador_linha_tempo = st.selectbox(
        "Colaborador",
        options=colaboradores_selecionados,
        key="painel_linha_tempo_colaborador",
    )
    jornadas_do_colaborador = [
        j for j in jornadas_filtradas if j.colaborador_matricula == colaborador_linha_tempo
    ]
    segmentos_por_dia: dict = {}
    for jornada_do_colaborador in jornadas_do_colaborador:
        for dia, segmentos in fatiar_linha_do_tempo_por_dia(linha_do_tempo(jornada_do_colaborador)).items():
            segmentos_por_dia.setdefault(dia, []).extend(segmentos)
    if segmentos_por_dia:
        components.html(
            renderizar_embutido(grafico_linha_do_tempo(segmentos_por_dia)),
            height=560,
            scrolling=False,
        )
    else:
        st.info("Nenhum apontamento encontrado para este colaborador no período filtrado.")

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
