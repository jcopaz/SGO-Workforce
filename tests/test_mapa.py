"""Testes do Incremento 10: mapa operacional (Folium) e geracao de pulsos de exemplo.

mapa.py e testavel diretamente (folium.Map e um objeto Python comum, sem
depender do runtime do Streamlit) - o smoke test real do servidor
(`streamlit run`) fica em docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

from datetime import timedelta

import folium
import pytest

from dados import gerar_jornadas_exemplo, gerar_pulsos_exemplo
from mapa import _COR_MALHA_FERREA, _COR_PULSO_BRUTO, _COR_TRAJETORIA, construir_mapa


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


def test_construir_mapa_pulsos_brutos_em_amarelo(tmp_path):
    # Pedido do responsavel pelo produto em 2026-08-04: pulso bruto sempre
    # amarelo (a qualidade continua no popup, so deixou de ser codificada
    # por cor do marcador).
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert _COR_PULSO_BRUTO in html


def test_construir_mapa_trajetoria_vermelha_tracejada(tmp_path):
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
    assert _COR_TRAJETORIA in html
    assert "dashArray" in html  # folium traduz dash_array para a opcao Leaflet dashArray


def test_construir_mapa_camada_malha_ferrea_opcional(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    trilho = [(-19.97, -44.01), (-19.98, -44.02), (-19.99, -44.03)]

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        trilhos_ferrovia=[trilho],
    )
    html = mapa.get_root().render()
    assert "Malha ferrea MRS" in html
    assert _COR_MALHA_FERREA in html


def test_construir_mapa_sem_pulsos_ainda_mostra_malha_ferrea():
    # A malha ferrea e uma camada de referencia estatica - nao deveria
    # depender de existir alguma jornada/pulso pra aparecer.
    trilho = [(-19.97, -44.01), (-19.98, -44.02)]

    mapa = construir_mapa(
        [],
        distancia_simplificacao_metros=50,
        raio_cluster_metros=20,
        tempo_minimo_cluster=timedelta(minutes=5),
        trilhos_ferrovia=[trilho],
    )
    html = mapa.get_root().render()
    assert "Malha ferrea MRS" in html
