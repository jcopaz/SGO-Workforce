"""Mapa operacional - piloto tecnico (Incremento 10).

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

import streamlit as st
from streamlit_folium import st_folium

from dados import carregar_jornadas, carregar_pulsos, gerar_pulsos_exemplo
from mapa import construir_mapa

st.set_page_config(page_title="SGO Workforce | Mapa (piloto)", layout="wide")

st.warning(
    "Piloto tecnico. Filtros de coordenacao, equipe, patio, sintoma e "
    "impacto ainda nao existem porque esses conceitos ainda nao foram "
    "modelados no sistema (ver docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md). "
    "Clusters de permanencia sao inferencia, nunca prova de presenca."
)

st.title("SGO Workforce | Mapa operacional (piloto)")

if "painel_diretorio_jornadas" not in st.session_state:
    st.session_state.painel_diretorio_jornadas = str(_RAIZ_PROJETO / "dados_locais" / "jornadas")
if "painel_diretorio_pulsos" not in st.session_state:
    st.session_state.painel_diretorio_pulsos = str(_RAIZ_PROJETO / "dados_locais" / "pulsos")

col_dir1, col_dir2 = st.columns(2)
with col_dir1:
    diretorio_jornadas = st.text_input(
        "Diretorio de jornadas persistidas", key="painel_diretorio_jornadas"
    )
with col_dir2:
    diretorio_pulsos = st.text_input(
        "Diretorio de pulsos GPS persistidos", key="painel_diretorio_pulsos"
    )

if not diretorio_jornadas or not diretorio_pulsos:
    st.warning("Informe os dois diretorios (jornadas e pulsos) para continuar.")
    st.stop()

jornadas, com_erro = carregar_jornadas(diretorio_jornadas)
if com_erro:
    st.error(f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem apagar.")

if not jornadas:
    st.info(
        "Nenhuma jornada encontrada. Gere dados de exemplo na pagina "
        "principal do painel primeiro."
    )
    st.stop()

opcoes_jornada = {
    f"{j.colaborador_matricula} - {j.inicio.isoformat() if j.inicio else '?'}": j for j in jornadas
}
rotulo_selecionado = st.selectbox(
    "Jornada", options=list(opcoes_jornada.keys()), key="painel_mapa_jornada_selecionada"
)
jornada_selecionada = opcoes_jornada[rotulo_selecionado]

if st.button("Gerar pulsos de exemplo para esta jornada (teste)"):
    gerar_pulsos_exemplo(diretorio_pulsos, jornada_selecionada)
    st.success("Pulsos de exemplo gravados.")

pulsos = carregar_pulsos(diretorio_pulsos, jornada_selecionada.id)

if not pulsos:
    st.info(
        "Nenhum pulso GPS encontrado para esta jornada nesse diretorio. "
        "Use o botao acima para gerar pulsos de exemplo."
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
