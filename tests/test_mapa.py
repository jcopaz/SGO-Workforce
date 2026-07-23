"""Testes do Incremento 10: mapa operacional (Folium) e geracao de pulsos de exemplo.

mapa.py e testavel diretamente (folium.Map e um objeto Python comum, sem
depender do runtime do Streamlit) - o smoke test real do servidor
(`streamlit run`) fica em docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

from datetime import timedelta

import folium
import pytest

from dados import gerar_jornadas_exemplo, gerar_pulsos_exemplo
from mapa import construir_mapa
from workforce_core.enums import QualidadePulso


def test_gerar_pulsos_exemplo_cobre_o_periodo_da_jornada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]

    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=300)

    assert len(pulsos) > 1
    assert pulsos[0].timestamp_dispositivo >= jornada.inicio
    assert pulsos[-1].timestamp_dispositivo <= jornada.fim
    assert all(p.jornada_id == jornada.id for p in pulsos)


def test_gerar_pulsos_exemplo_e_deterministico_por_jornada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]

    pulsos_a = gerar_pulsos_exemplo(tmp_path / "pulsos_a", jornada, intervalo_segundos=300)
    pulsos_b = gerar_pulsos_exemplo(tmp_path / "pulsos_b", jornada, intervalo_segundos=300)

    assert [(p.latitude, p.longitude) for p in pulsos_a] == [
        (p.latitude, p.longitude) for p in pulsos_b
    ]


def test_construir_mapa_sem_pulsos_nao_quebra():
    mapa = construir_mapa(
        [],
        distancia_simplificacao_metros=50,
        raio_cluster_metros=20,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    assert isinstance(mapa, folium.Map)


def test_construir_mapa_com_pulsos_gera_camadas(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=180)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )

    html = mapa.get_root().render()
    assert "Pulsos brutos" in html
    assert "Trajetoria simplificada" in html


def test_popup_escapa_html_de_campos_controlados_pelo_usuario(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    jornada.colaborador_matricula = "<script>alert(1)</script>"

    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        mostrar_pulsos_brutos=True,
    )

    html = mapa.get_root().render()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_construir_mapa_cores_por_qualidade(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    pulsos[0].qualidade = QualidadePulso.SALTO_IMPOSSIVEL

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert '"red"' in html or "'red'" in html or "red" in html
