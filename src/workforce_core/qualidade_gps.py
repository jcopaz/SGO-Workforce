"""Avaliacao de qualidade de pulsos GPS (Incremento 7).

Implementa a regra de docs/08_GPS_PULSOS_E_PRIVACIDADE.md, secao
"Qualidade": "Nao inferir presenca exata quando a precisao for ruim...
Pontos impossiveis, saltos e velocidade incompativel devem ser marcados,
nao sobrescritos."

Nenhum limiar numerico (precisao minima aceitavel, velocidade maxima
plausivel) e definido aqui - sao decisoes de negocio explicitamente
pendentes (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 15.3
"Antes do Incremento 7"). Toda funcao exige o limiar como parametro
explicito de quem chama; nao ha valor padrao inventado.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from .entities import PulsoGps
from .enums import QualidadePulso

RAIO_TERRA_METROS = 6_371_000.0


def distancia_metros(a: PulsoGps, b: PulsoGps) -> float:
    """Distancia em linha reta (formula de haversine) entre dois pulsos."""
    lat1, lon1, lat2, lon2 = map(radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_METROS * asin(sqrt(h))


def velocidade_implicita_metros_segundo(anterior: PulsoGps, atual: PulsoGps) -> float:
    """Velocidade media implicita entre dois pulsos consecutivos, em m/s.

    Retorna infinito se os timestamps forem iguais (distancia percorrida
    em tempo zero) e houver deslocamento - situacao que ja e, por si so,
    um salto impossivel.
    """
    delta_segundos = (atual.timestamp_dispositivo - anterior.timestamp_dispositivo).total_seconds()
    dist = distancia_metros(anterior, atual)
    if delta_segundos <= 0:
        return float("inf") if dist > 0 else 0.0
    return dist / delta_segundos


def avaliar_pulso(
    atual: PulsoGps,
    anterior: PulsoGps | None,
    *,
    precisao_maxima_aceitavel_metros: float,
    velocidade_maxima_plausivel_metros_segundo: float,
) -> QualidadePulso:
    """Classifica a qualidade de um pulso, sem alterar seus dados originais.

    A precisao original do dispositivo nunca e descartada por esta funcao -
    ela apenas devolve uma classificacao para o pulso ser marcado pelo
    chamador (docs/08: "marcados, nao sobrescritos").
    """
    if atual.precisao_metros > precisao_maxima_aceitavel_metros:
        return QualidadePulso.PRECISAO_RUIM

    if anterior is not None:
        velocidade = velocidade_implicita_metros_segundo(anterior, atual)
        if velocidade > velocidade_maxima_plausivel_metros_segundo:
            return QualidadePulso.SALTO_IMPOSSIVEL

    if (
        atual.velocidade_metros_segundo is not None
        and atual.velocidade_metros_segundo > velocidade_maxima_plausivel_metros_segundo
    ):
        return QualidadePulso.VELOCIDADE_INCOMPATIVEL

    return QualidadePulso.OK
