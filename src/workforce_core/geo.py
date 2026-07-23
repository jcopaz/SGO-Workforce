"""Simplificacao de trajetoria e clusters de permanencia (Incremento 10).

Suporta o mapa operacional (docs/13_MAPA_OPERACIONAL.md): trajetoria
simplificada, clusters de permanencia, e "tempo no local" como inferencia
distinta do evento declarado ("Divergencia e indicador de qualidade, nao
prova automatica de irregularidade" - citado literalmente do doc, secao
"Tempo no local").

Nenhum limiar (distancia minima de simplificacao, raio e tempo minimo de
cluster) tem valor padrao - mesmo padrao ja adotado em
workforce_core.qualidade_gps: sao parametros de configuracao ainda nao
validados operacionalmente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from .entities import PulsoGps
from .qualidade_gps import distancia_metros


def simplificar_trajetoria(
    pulsos: List[PulsoGps], *, distancia_minima_metros: float
) -> List[PulsoGps]:
    """Mantem um ponto apenas se estiver a pelo menos `distancia_minima_metros`
    do ultimo ponto mantido - reduz o volume de pontos para desenho no mapa.
    Sempre preserva o primeiro e o ultimo pulso da sequencia (para a
    trajetoria nao "cortar" o inicio/fim real).

    docs/13_MAPA_OPERACIONAL.md, secao "Performance": "Simplificar
    trajetorias, agrupar pontos e limitar o periodo padrao."
    """
    if not pulsos:
        return []
    pulsos_ordenados = sorted(pulsos, key=lambda p: p.timestamp_dispositivo)
    simplificados = [pulsos_ordenados[0]]
    for pulso in pulsos_ordenados[1:]:
        if distancia_metros(simplificados[-1], pulso) >= distancia_minima_metros:
            simplificados.append(pulso)
    if simplificados[-1] is not pulsos_ordenados[-1]:
        simplificados.append(pulsos_ordenados[-1])
    return simplificados


@dataclass
class ClusterPermanencia:
    latitude_media: float
    longitude_media: float
    inicio: datetime
    fim: datetime
    quantidade_pulsos: int

    @property
    def duracao(self) -> timedelta:
        return self.fim - self.inicio


def agrupar_permanencia(
    pulsos: List[PulsoGps], *, raio_metros: float, tempo_minimo: timedelta
) -> List[ClusterPermanencia]:
    """Agrupa pulsos consecutivos proximos entre si (raio_metros a partir do
    ponto anterior do mesmo grupo) e retorna apenas os grupos cujo
    intervalo de tempo total seja >= tempo_minimo.

    E uma inferencia (docs/13_MAPA_OPERACIONAL.md, secao "Tempo no
    local"), nunca deve ser tratada como prova - sempre distinta do
    evento declarado (Atividade/EventoSecundario) que o colaborador
    registrou.
    """
    if not pulsos:
        return []

    pulsos_ordenados = sorted(pulsos, key=lambda p: p.timestamp_dispositivo)
    grupos: List[List[PulsoGps]] = []
    grupo_atual = [pulsos_ordenados[0]]

    for pulso in pulsos_ordenados[1:]:
        if distancia_metros(grupo_atual[-1], pulso) <= raio_metros:
            grupo_atual.append(pulso)
        else:
            grupos.append(grupo_atual)
            grupo_atual = [pulso]
    grupos.append(grupo_atual)

    clusters: List[ClusterPermanencia] = []
    for grupo in grupos:
        inicio = grupo[0].timestamp_dispositivo
        fim = grupo[-1].timestamp_dispositivo
        if fim - inicio < tempo_minimo:
            continue
        clusters.append(
            ClusterPermanencia(
                latitude_media=sum(p.latitude for p in grupo) / len(grupo),
                longitude_media=sum(p.longitude for p in grupo) / len(grupo),
                inicio=inicio,
                fim=fim,
                quantidade_pulsos=len(grupo),
            )
        )
    return clusters
