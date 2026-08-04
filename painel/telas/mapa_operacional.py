"""Mapa operacional - piloto tecnico (Incremento 10, backend real de
pulsos na Fase 1 da captacao de geolocalizacao - ver
docs/69_ADR_0042_LEVANTAMENTO_LACUNAS_GPS_PULSOS.md e
docs/70_ADR_0043_DECISOES_CAPTACAO_PERIODICA_PULSO_GPS.md).

Camadas, popup e filtros de docs/13_MAPA_OPERACIONAL.md. Filtros que
dependem de conceitos ainda nao modelados (coordenacao, equipe, patio,
impacto) nao existem aqui - ver
docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st
from streamlit_folium import st_folium

from dados import carregar_jornadas_via_api, carregar_pulsos_via_api, formatar_data_hora
from mapa import construir_mapa


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


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
    jornadas, com_erro = carregar_jornadas_via_api(url_api, token_api)
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
    pulsos, pulsos_com_erro = carregar_pulsos_via_api(url_api, token_api, jornada_selecionada.id)
except requests.exceptions.RequestException as exc:
    st.error(f"Não foi possível buscar pulsos GPS do backend: {exc}")
    st.stop()

if pulsos_com_erro:
    st.error(f"{len(pulsos_com_erro)} pulso(s) recebido(s) com estrutura inválida, ignorado(s).")

if not pulsos:
    st.info(
        "Nenhum pulso GPS encontrado para esta jornada no backend. A captação "
        "periódica de GPS na interface de campo ainda não existe (ver "
        "docs/69_ADR_0042_LEVANTAMENTO_LACUNAS_GPS_PULSOS.md) - isso é o "
        "estado real do sistema hoje, não um erro desta tela."
    )
    st.stop()

st.caption(f"{len(pulsos)} pulso(s) carregado(s) para esta jornada.")

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
    pulsos,
    distancia_simplificacao_metros=float(distancia_simplificacao),
    raio_cluster_metros=float(raio_cluster),
    tempo_minimo_cluster=timedelta(minutes=tempo_minimo_cluster_minutos),
)

st_folium(mapa, width="100%", height=560, key="painel_mapa_folium")
