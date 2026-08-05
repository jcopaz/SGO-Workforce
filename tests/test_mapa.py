"""Testes do Incremento 10: mapa operacional (Folium) e geracao de pulsos de exemplo.

mapa.py e testavel diretamente (folium.Map e um objeto Python comum, sem
depender do runtime do Streamlit) - o smoke test real do servidor
(`streamlit run`) fica em docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

import json
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import folium
import pytest

from dados import filtrar_pulsos_por_periodo, gerar_jornadas_exemplo, gerar_pulsos_exemplo
from mapa import (
    _COR_MALHA_FERREA,
    _COR_PULSO_BRUTO,
    _COR_SEM_ATIVIDADE,
    _COR_TRAJETORIA,
    construir_mapa,
    cor_por_rotulo,
    rotulo_classificacao_pulso,
)
from workforce_core.consolidacao import ClassificacaoInstante
from workforce_core.entities import PulsoGps


def _contido(rotulo: str, html: str) -> bool:
    """Confere se `rotulo` aparece no HTML gerado pelo Folium, cru ou
    escapado como `json.dumps` (padrao `ensure_ascii=True`) grava nomes de
    camada dentro do <script> do LayerControl - "ç"/"ó" viram literalmente
    "\\u00e7"/"\\u00f3" no HTML, nao o caractere em si (mesmo fenomeno de
    `_contido` em test_painel.py, so que no Folium em vez do pyecharts)."""
    return rotulo in html or json.dumps(rotulo)[1:-1] in html


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
    # Pedido do responsavel pelo produto em 2026-08-04 (ADR-0049): pulsos
    # brutos sao sempre desenhados direto no mapa (sem FeatureGroup/toggle
    # proprio - ja sao selecionaveis pelos filtros de atividade/data/
    # horario da tela) - so a trajetoria continua como camada nomeada/
    # togglable no LayerControl.
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
    assert html.count("L.circleMarker(") >= len(pulsos)  # um marcador por pulso, sempre visivel
    assert _contido("Traçar trajetória", html)


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


def test_construir_mapa_malha_ferrea_sempre_visivel_sem_toggle(tmp_path):
    # ADR-0049: malha ferrea desenhada direto no mapa, nunca como camada
    # nomeada/togglable - "Malha ferrea MRS" aqui e so o texto do tooltip
    # de cada trecho, nao um nome de FeatureGroup no LayerControl.
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
    # Nunca vira uma entrada do LayerControl (so "Tracar trajetoria" e).
    assert '"Malha ferrea MRS" :' not in html


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


# ----------------------------------------------------------------------
# Rotulo/cor por classificacao (pedido do responsavel pelo produto em
# 2026-08-04, ver ADR-0047) e marcos de inicio/fim.
# ----------------------------------------------------------------------
def test_rotulo_classificacao_pulso_por_tipo():
    assert rotulo_classificacao_pulso(ClassificacaoInstante("ATIVIDADE", None)) == "Atividade"
    assert (
        rotulo_classificacao_pulso(ClassificacaoInstante("ATENDIMENTO_FALHA", None))
        == "Atendimento de falha"
    )
    assert rotulo_classificacao_pulso(ClassificacaoInstante("SEM_ATIVIDADE", None)) == "Sem atividade"


def test_rotulo_classificacao_pulso_pausa_usa_rotulo_motivo():
    # Sem catalogo informado, rotulo_motivo cai no proprio codigo (ver
    # painel/dados.py::rotulo_motivo).
    rotulo = rotulo_classificacao_pulso(ClassificacaoInstante("PAUSA", "EE02"))
    assert "EE02" in rotulo


def test_cor_por_rotulo_e_deterministica():
    assert cor_por_rotulo("EE02 - Refeicao") == cor_por_rotulo("EE02 - Refeicao")
    assert cor_por_rotulo("Sem atividade") == _COR_SEM_ATIVIDADE


def test_cor_por_rotulo_rotulos_diferentes_tendem_a_cores_diferentes():
    cores = {cor_por_rotulo(f"Categoria {i}") for i in range(8)}
    assert len(cores) > 1  # nao deveria colapsar tudo numa cor so


def test_construir_mapa_marcos_de_inicio_e_fim(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        marco_inicio=pulsos[0],
        marco_fim=pulsos[-1],
    )
    html = mapa.get_root().render()
    assert "Inicio da jornada" in html
    assert "Fim da jornada" in html
    assert '"green"' in html
    assert '"red"' in html
    # Marcos sao desenhados direto no mapa (ADR-0049) - nunca viram uma
    # camada nomeada/togglable no LayerControl.
    assert "Inicio e fim" not in html


def test_construir_mapa_cor_por_pulso_sobrescreve_amarelo_padrao(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    cor_customizada = "#1E88E5"
    cor_por_pulso = {pulso.id: cor_customizada for pulso in pulsos}

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        cor_por_pulso=cor_por_pulso,
    )
    html = mapa.get_root().render()
    assert cor_customizada in html
    assert _COR_PULSO_BRUTO not in html


# ----------------------------------------------------------------------
# Filtro de data + faixa de horario (pedido do responsavel pelo produto
# em 2026-08-04, ver ADR-0047).
# ----------------------------------------------------------------------
def test_filtrar_pulsos_por_periodo_faixa_do_dia_inteiro_nao_filtra_nada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    data_jornada = pulsos[0].timestamp_dispositivo.date()

    filtrados = filtrar_pulsos_por_periodo(pulsos, data_jornada, time(0, 0), time(23, 59, 59))
    assert filtrados == pulsos


def test_filtrar_pulsos_por_periodo_data_diferente_devolve_vazio(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    filtrados = filtrar_pulsos_por_periodo(pulsos, date(1999, 1, 1), time(0, 0), time(23, 59, 59))
    assert filtrados == []


def test_filtrar_pulsos_por_periodo_estreita_por_horario(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    data_jornada = pulsos[0].timestamp_dispositivo.date()
    inicio = pulsos[0].timestamp_dispositivo.time()

    filtrados = filtrar_pulsos_por_periodo(pulsos, data_jornada, inicio, inicio)
    assert filtrados == [pulsos[0]]


def test_filtrar_pulsos_por_periodo_converte_utc_para_horario_de_brasilia():
    # Bug que este filtro evita (mesma familia do ADR-0047): um pulso as
    # 23h de Brasilia (02h UTC do dia seguinte) precisa continuar
    # aparecendo no filtro do dia certo (Brasilia), nao do dia UTC.
    pulso_23h_brasilia = PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="12345",
        latitude=-23.5,
        longitude=-46.6,
        precisao_metros=10.0,
        timestamp_dispositivo=datetime(2026, 8, 5, 2, 0, tzinfo=timezone.utc),  # 04/08 23h em Brasilia
    )

    filtrados = filtrar_pulsos_por_periodo(
        [pulso_23h_brasilia], date(2026, 8, 4), time(22, 0), time(23, 59, 59)
    )
    assert filtrados == [pulso_23h_brasilia]
