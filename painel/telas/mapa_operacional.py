"""Mapa operacional - piloto tecnico (Incremento 10; captacao real de GPS
completa desde o ADR-0042 ao ADR-0045 - backend, captura periodica na
interface de campo e GPS obrigatorio; estilo visual, malha ferrea da MRS
e filtro por atividade/data/horario do ADR-0046/ADR-0047).

Camadas, popup e filtros de docs/13_MAPA_OPERACIONAL.md. Filtros que
dependem de conceitos ainda nao modelados (coordenacao, equipe, patio,
impacto) nao existem aqui - ver
docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

from __future__ import annotations

import sys
from datetime import time, timedelta
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from dados import (
    carregar_jornadas_via_api,
    carregar_pulsos_via_api,
    fatiar_linha_do_tempo_por_dia,
    filtrar_pulsos_por_periodo,
    formatar_data_hora,
)
from graficos import grafico_linha_do_tempo, renderizar_embutido
from malha_ferrea import carregar_trilhos_malha_mrs
from mapa import construir_mapa, cor_por_rotulo, rotulo_classificacao_pulso
from workforce_core.catalogo import catalogo_completo
from workforce_core.consolidacao import classificar_instante, linha_do_tempo
from workforce_core.fuso_horario import para_horario_brasil


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


# Cache das chamadas ao backend (ADR-0049, pedido do responsavel pelo
# produto em 2026-08-04 - fluidez, Streamlit reexecuta o script inteiro a
# cada slider/filtro mexido). Sem isso, ajustar qualquer um dos 7 widgets
# da tela (atividade/data/horario x2/simplificacao/cluster/tempo) refazia
# as duas chamadas de rede (`carregar_jornadas_via_api`/
# `carregar_pulsos_via_api`, timeout de 60s pro cold start do Render) do
# zero a cada interacao. TTL de 60s (mesmo numero do timeout de rede -
# nao e coincidencia, o dado nao muda mais rapido que isso na pratica) -
# "Sincronizar dados" abaixo limpa o cache na hora pra nunca segurar um
# refresh manual pedido explicitamente. Os wrappers ficam aqui (nao em
# dados.py) porque dados.py e deliberadamente livre de Streamlit, pra
# continuar testavel com pytest puro (ver docstring do modulo).
@st.cache_data(ttl=60, show_spinner=False)
def _carregar_jornadas_cache(url: str, token: str):
    return carregar_jornadas_via_api(url, token)


@st.cache_data(ttl=60, show_spinner=False)
def _carregar_pulsos_cache(url: str, token: str, jornada_id):
    return carregar_pulsos_via_api(url, token, jornada_id)


st.warning(
    "Piloto tecnico. Filtros de coordenacao, equipe, patio, sintoma e "
    "impacto ainda nao existem porque esses conceitos ainda nao foram "
    "modelados no sistema (ver docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md). "
    "Clusters de permanencia sao inferencia, nunca prova de presenca."
)

col_titulo, col_sync = st.columns([5, 1])
with col_titulo:
    st.title("SGO Workforce | Mapa operacional (piloto)")
with col_sync:
    st.write("")  # alinhamento vertical com o titulo
    if st.button("🔄 Sincronizar dados", width="stretch", key="mapa_sincronizar"):
        _carregar_jornadas_cache.clear()
        _carregar_pulsos_cache.clear()
        st.toast("Sincronizando com o backend...", icon="🔄")

# Fonte de dados fixa em API (nuvem, ADR-0041) - ver mesmo comentario em
# painel/telas/dashboard.py. Pulsos vem do backend real desde a Fase 1 do
# ADR seguinte a este (backend /pulsos) - ate a Fase 2 (captacao na
# interface de campo) existir, toda jornada real vai aparecer sem pulso
# nenhum, o que e o estado real do sistema, nao um bug desta tela.
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
    jornadas, com_erro = _carregar_jornadas_cache(url_api, token_api)
except requests.exceptions.RequestException as exc:
    st.error(f"Não foi possível buscar dados do backend: {exc}")
    st.stop()

if com_erro:
    st.error(f"{len(com_erro)} jornada(s) recebida(s) do backend com estrutura inválida, ignorada(s).")

if not jornadas:
    st.info("Nenhuma jornada encerrada no backend ainda.")
    st.stop()

opcoes_jornada = {
    f"{j.colaborador_matricula} - {formatar_data_hora(j.inicio)}": j for j in jornadas
}
rotulo_selecionado = st.selectbox(
    "Jornada", options=list(opcoes_jornada.keys()), key="painel_mapa_jornada_selecionada"
)
jornada_selecionada = opcoes_jornada[rotulo_selecionado]

try:
    pulsos, pulsos_com_erro = _carregar_pulsos_cache(url_api, token_api, jornada_selecionada.id)
except requests.exceptions.RequestException as exc:
    st.error(f"Não foi possível buscar pulsos GPS do backend: {exc}")
    st.stop()

if pulsos_com_erro:
    st.error(f"{len(pulsos_com_erro)} pulso(s) recebido(s) com estrutura inválida, ignorado(s).")

if not pulsos:
    st.info(
        "Nenhum pulso GPS encontrado para esta jornada no backend. Isso "
        "acontece se a jornada foi registrada antes da captação periódica "
        "de GPS (ADR-0045) ou se o colaborador ainda não sincronizou os "
        "dados desta jornada."
    )
    st.stop()

# Classificacao por atividade/pausa/evento (ADR-0047) - base do filtro de
# atividade e da cor de cada pulso no mapa. catalogo_completo() tolera
# ausencia de backend/rede (fallback offline, mesmo padrao ja usado nos
# demais filtros do painel).
catalogo = catalogo_completo()
rotulos_por_pulso = {
    pulso.id: rotulo_classificacao_pulso(
        classificar_instante(jornada_selecionada, pulso.timestamp_dispositivo), catalogo
    )
    for pulso in pulsos
}
marco_inicio = min(pulsos, key=lambda p: p.timestamp_dispositivo)
marco_fim = max(pulsos, key=lambda p: p.timestamp_dispositivo)

col_atividade, col_data, col_hora_ini, col_hora_fim = st.columns(4)
with col_atividade:
    opcoes_atividade = ["Todas as atividades"] + sorted(set(rotulos_por_pulso.values()))
    atividade_selecionada = st.selectbox(
        "Atividade", options=opcoes_atividade, key="painel_mapa_filtro_atividade"
    )
with col_data:
    data_filtro = st.date_input(
        "Data dos pulsos",
        value=para_horario_brasil(marco_inicio.timestamp_dispositivo).date(),
        key="painel_mapa_filtro_data",
    )
with col_hora_ini:
    hora_inicial = st.time_input(
        "Horário inicial", value=time(0, 0), key="painel_mapa_filtro_hora_inicial"
    )
with col_hora_fim:
    hora_final = st.time_input(
        "Horário final", value=time(23, 59, 59), key="painel_mapa_filtro_hora_final"
    )

pulsos_filtrados = filtrar_pulsos_por_periodo(pulsos, data_filtro, hora_inicial, hora_final)
if atividade_selecionada != "Todas as atividades":
    pulsos_filtrados = [
        pulso for pulso in pulsos_filtrados if rotulos_por_pulso[pulso.id] == atividade_selecionada
    ]

cor_por_pulso = {pulso.id: cor_por_rotulo(rotulos_por_pulso[pulso.id]) for pulso in pulsos_filtrados}

if not pulsos_filtrados:
    st.info("Nenhum pulso encontrado para o filtro atual (atividade/data/horário).")

st.caption(f"{len(pulsos_filtrados)} de {len(pulsos)} pulso(s) exibido(s) para esta jornada.")

col_a, col_b, col_c = st.columns(3)
with col_a:
    distancia_simplificacao = st.slider(
        "Distancia minima de simplificacao (m) - nao e valor oficial",
        min_value=0,
        max_value=500,
        value=50,
        key="painel_mapa_distancia_simplificacao",
    )
with col_b:
    raio_cluster = st.slider(
        "Raio de cluster de permanencia (m) - nao e valor oficial",
        min_value=1,
        max_value=200,
        value=20,
        key="painel_mapa_raio_cluster",
    )
with col_c:
    tempo_minimo_cluster_minutos = st.slider(
        "Tempo minimo de permanencia (min) - nao e valor oficial",
        min_value=1,
        max_value=60,
        value=5,
        key="painel_mapa_tempo_minimo_cluster",
    )

mapa = construir_mapa(
    pulsos_filtrados,
    distancia_simplificacao_metros=float(distancia_simplificacao),
    raio_cluster_metros=float(raio_cluster),
    tempo_minimo_cluster=timedelta(minutes=tempo_minimo_cluster_minutos),
    trilhos_ferrovia=carregar_trilhos_malha_mrs(),
    cor_por_pulso=cor_por_pulso,
    marco_inicio=marco_inicio,
    marco_fim=marco_fim,
)

# Linha do tempo do dia selecionado (ADR-0051, pedido do responsavel pelo
# produto em 2026-08-04) - ao lado do mapa, sempre a mesma data escolhida
# no filtro "Data dos pulsos" acima (nunca a faixa de horario, que so
# afeta os pulsos/trajetoria do mapa - a linha do tempo mostra o dia
# inteiro pra manter o contexto de antes/depois).
segmentos_do_dia = fatiar_linha_do_tempo_por_dia(linha_do_tempo(jornada_selecionada)).get(data_filtro, [])

col_mapa, col_linha_tempo = st.columns([2, 1])
with col_mapa:
    st_folium(
        mapa,
        width="100%",
        height=560,
        key="painel_mapa_folium",
        returned_objects=[],  # nada do retorno e usado - pan/zoom/clique no
        # mapa nunca deveria reexecutar o script inteiro (ADR-0049, fluidez).
    )
with col_linha_tempo:
    st.caption(f"Linha do tempo - {data_filtro.strftime('%d/%m/%Y')}")
    if segmentos_do_dia:
        components.html(
            renderizar_embutido(grafico_linha_do_tempo({data_filtro: segmentos_do_dia})),
            height=560,
            scrolling=False,
        )
    else:
        st.info("Nenhum apontamento registrado nesta jornada no dia selecionado.")
