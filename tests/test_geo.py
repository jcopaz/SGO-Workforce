"""Testes do Incremento 10: simplificacao de trajetoria e clusters de permanencia.

Cobre docs/13_MAPA_OPERACIONAL.md, secoes "Performance" e "Tempo no local".
"""

from datetime import datetime, timedelta
from uuid import uuid4

from workforce_core.entities import PulsoGps
from workforce_core.geo import agrupar_permanencia, simplificar_trajetoria


def _dt(segundos):
    return datetime(2026, 1, 1, 8, 0, 0) + timedelta(seconds=segundos)


def _pulso(segundos, lat, lon):
    return PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="12345",
        latitude=lat,
        longitude=lon,
        precisao_metros=10,
        timestamp_dispositivo=_dt(segundos),
    )


def test_simplificar_trajetoria_lista_vazia():
    assert simplificar_trajetoria([], distancia_minima_metros=10) == []


def test_simplificar_trajetoria_mantem_pontos_distantes():
    pulsos = [
        _pulso(0, 0.0, 0.0),
        _pulso(60, 0.01, 0.0),  # ~1.1km, bem alem do limiar
        _pulso(120, 0.02, 0.0),
    ]
    simplificados = simplificar_trajetoria(pulsos, distancia_minima_metros=100)
    assert len(simplificados) == 3


def test_simplificar_trajetoria_descarta_pontos_muito_proximos_mas_preserva_extremos():
    pulsos = [
        _pulso(0, 0.0, 0.0),
        _pulso(10, 0.0000001, 0.0),  # a poucos centimetros, deve ser descartado
        _pulso(20, 0.0000002, 0.0),  # idem
        _pulso(30, 0.01, 0.0),  # ~1.1km, deve ser mantido
    ]
    simplificados = simplificar_trajetoria(pulsos, distancia_minima_metros=50)

    assert simplificados[0] is pulsos[0]
    assert simplificados[-1] is pulsos[-1]
    assert len(simplificados) == 2


def test_simplificar_trajetoria_ordena_por_timestamp():
    pulsos = [
        _pulso(120, 0.02, 0.0),
        _pulso(0, 0.0, 0.0),
        _pulso(60, 0.01, 0.0),
    ]
    simplificados = simplificar_trajetoria(pulsos, distancia_minima_metros=100)
    assert [p.timestamp_dispositivo for p in simplificados] == sorted(
        p.timestamp_dispositivo for p in pulsos
    )


def test_agrupar_permanencia_lista_vazia():
    assert agrupar_permanencia([], raio_metros=20, tempo_minimo=timedelta(minutes=1)) == []


def test_agrupar_permanencia_detecta_cluster_parado():
    # 5 pulsos praticamente no mesmo lugar, ao longo de 10 minutos.
    pulsos = [_pulso(i * 120, 0.0, 0.0) for i in range(6)]  # 0,2,4,6,8,10 min

    clusters = agrupar_permanencia(pulsos, raio_metros=5, tempo_minimo=timedelta(minutes=5))

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.quantidade_pulsos == 6
    assert cluster.duracao == timedelta(minutes=10)
    assert cluster.latitude_media == 0.0


def test_agrupar_permanencia_ignora_grupo_curto_demais():
    pulsos = [_pulso(0, 0.0, 0.0), _pulso(30, 0.0, 0.0)]  # so 30s parado

    clusters = agrupar_permanencia(pulsos, raio_metros=5, tempo_minimo=timedelta(minutes=5))
    assert clusters == []


def test_agrupar_permanencia_separa_dois_locais_distintos():
    parado_1 = [_pulso(i * 60, 0.0, 0.0) for i in range(6)]  # 0..5 min, lat=0
    em_movimento = [_pulso(360, 0.005, 0.0)]  # ~555m de salto - novo grupo
    parado_2 = [_pulso(360 + i * 60, 0.005, 0.0) for i in range(6)]  # outro local parado

    pulsos = parado_1 + em_movimento + parado_2

    clusters = agrupar_permanencia(pulsos, raio_metros=5, tempo_minimo=timedelta(minutes=4))

    assert len(clusters) == 2
    assert clusters[0].latitude_media == 0.0
    assert abs(clusters[1].latitude_media - 0.005) < 1e-9
