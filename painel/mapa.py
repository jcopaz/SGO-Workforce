"""Construcao do mapa operacional com Folium (Incremento 10).

docs/13_MAPA_OPERACIONAL.md define objetivos, camadas, popup e filtros.
Filtros que dependem de conceitos ainda nao modelados no sistema
(coordenacao, equipe, patio, impacto) nao sao implementados aqui - ver
docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.

Nenhum limiar de simplificacao/cluster tem valor padrao embutido (mesmo
padrao de workforce_core.qualidade_gps e workforce_core.geo) - sao sempre
parametros explicitos de quem chama.
"""

from __future__ import annotations

import html
from datetime import timedelta
from typing import List, Tuple

import folium

from workforce_core.entities import PulsoGps
from workforce_core.enums import QualidadePulso
from workforce_core.geo import ClusterPermanencia, agrupar_permanencia, simplificar_trajetoria

_COR_POR_QUALIDADE = {
    QualidadePulso.OK: "green",
    QualidadePulso.PRECISAO_RUIM: "orange",
    QualidadePulso.SALTO_IMPOSSIVEL: "red",
    QualidadePulso.VELOCIDADE_INCOMPATIVEL: "red",
    QualidadePulso.NAO_AVALIADO: "gray",
}

_LOCAL_SEM_DADOS = (-15.7801, -47.9292)  # Brasilia - fallback visual quando nao ha nenhum pulso


def _centro(pulsos: List[PulsoGps]) -> Tuple[float, float]:
    if not pulsos:
        return _LOCAL_SEM_DADOS
    return (
        sum(p.latitude for p in pulsos) / len(pulsos),
        sum(p.longitude for p in pulsos) / len(pulsos),
    )


def _popup_pulso(pulso: PulsoGps) -> str:
    linhas = [
        f"Colaborador: {html.escape(pulso.colaborador_matricula)}",
        f"Horario: {html.escape(pulso.timestamp_dispositivo.isoformat())}",
        f"Precisao: {pulso.precisao_metros:.0f} m",
        f"Qualidade: {html.escape(pulso.qualidade.value)}",
    ]
    return "<br>".join(linhas)


def _popup_cluster(cluster: ClusterPermanencia) -> str:
    linhas = [
        "Cluster de permanencia (inferencia, nao prova de presenca)",
        f"Inicio: {html.escape(cluster.inicio.isoformat())}",
        f"Fim: {html.escape(cluster.fim.isoformat())}",
        f"Duracao: {html.escape(str(cluster.duracao))}",
        f"Pulsos no cluster: {cluster.quantidade_pulsos}",
    ]
    return "<br>".join(linhas)


def construir_mapa(
    pulsos: List[PulsoGps],
    *,
    distancia_simplificacao_metros: float,
    raio_cluster_metros: float,
    tempo_minimo_cluster: timedelta,
    mostrar_pulsos_brutos: bool = True,
) -> folium.Map:
    """Monta o mapa com as camadas de docs/13_MAPA_OPERACIONAL.md que ja
    sao possiveis com o que existe hoje: pulsos brutos (marcados por
    qualidade), trajetoria simplificada e clusters de permanencia.

    Pinos de inicio/fim de evento, falhas por sintoma/impacto e heatmap de
    HH ficam para quando houver mais volume de dados reais para validar a
    utilidade de cada camada adicional (ver ADR-0010).
    """
    mapa = folium.Map(location=_centro(pulsos), zoom_start=14 if pulsos else 4)

    if not pulsos:
        return mapa

    if mostrar_pulsos_brutos:
        camada_brutos = folium.FeatureGroup(name="Pulsos brutos", show=False)
        for pulso in pulsos:
            folium.CircleMarker(
                location=(pulso.latitude, pulso.longitude),
                radius=3,
                color=_COR_POR_QUALIDADE.get(pulso.qualidade, "gray"),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(_popup_pulso(pulso), max_width=300),
            ).add_to(camada_brutos)
        camada_brutos.add_to(mapa)

    trajetoria = simplificar_trajetoria(
        pulsos, distancia_minima_metros=distancia_simplificacao_metros
    )
    if len(trajetoria) > 1:
        camada_trajetoria = folium.FeatureGroup(name="Trajetoria simplificada", show=True)
        folium.PolyLine(
            locations=[(p.latitude, p.longitude) for p in trajetoria],
            color="blue",
            weight=3,
            opacity=0.7,
        ).add_to(camada_trajetoria)
        camada_trajetoria.add_to(mapa)

    clusters = agrupar_permanencia(
        pulsos, raio_metros=raio_cluster_metros, tempo_minimo=tempo_minimo_cluster
    )
    if clusters:
        camada_clusters = folium.FeatureGroup(name="Clusters de permanencia (inferencia)", show=True)
        for cluster in clusters:
            folium.CircleMarker(
                location=(cluster.latitude_media, cluster.longitude_media),
                radius=8 + min(cluster.quantidade_pulsos, 20),
                color="purple",
                fill=True,
                fill_opacity=0.4,
                popup=folium.Popup(_popup_cluster(cluster), max_width=300),
            ).add_to(camada_clusters)
        camada_clusters.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)
    return mapa
