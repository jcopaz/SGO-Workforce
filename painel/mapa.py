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
from typing import List, Optional, Tuple

import folium

from workforce_core.entities import PulsoGps
from workforce_core.geo import ClusterPermanencia, agrupar_permanencia, simplificar_trajetoria

# Estilo pedido pelo responsavel pelo produto em 2026-08-04: pulso bruto em
# amarelo (a qualidade continua disponivel no popup, so deixou de ser
# codificada por cor - ver _popup_pulso), trajetoria simplificada em
# vermelho tracejado-pontilhado, basemap claro (cartodbpositron, prioriza
# legibilidade de ruas) e a malha ferrea da MRS em cima, bem escura, pra
# contrastar com o basemap claro.
_COR_PULSO_BRUTO = "#FFC107"
_COR_BORDA_PULSO_BRUTO = "#B8860B"
_COR_TRAJETORIA = "#E53935"
_COR_MALHA_FERREA = "#212121"
_TILES_BASEMAP = "cartodbpositron"

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
    trilhos_ferrovia: Optional[List[List[Tuple[float, float]]]] = None,
) -> folium.Map:
    """Monta o mapa com as camadas de docs/13_MAPA_OPERACIONAL.md que ja
    sao possiveis com o que existe hoje: pulsos brutos, trajetoria
    simplificada, clusters de permanencia e (opcional) a malha ferrea da
    MRS como camada de referencia (`painel/malha_ferrea.py`).

    Pinos de inicio/fim de evento, falhas por sintoma/impacto e heatmap de
    HH ficam para quando houver mais volume de dados reais para validar a
    utilidade de cada camada adicional (ver ADR-0010).
    """
    mapa = folium.Map(location=_centro(pulsos), zoom_start=14 if pulsos else 4, tiles=_TILES_BASEMAP)

    if trilhos_ferrovia:
        camada_ferrovia = folium.FeatureGroup(name="Malha ferrea MRS", show=True)
        for trilho in trilhos_ferrovia:
            folium.PolyLine(
                locations=trilho,
                color=_COR_MALHA_FERREA,
                weight=2,
                opacity=0.85,
                tooltip="Malha ferrea MRS",
            ).add_to(camada_ferrovia)
        camada_ferrovia.add_to(mapa)

    if not pulsos:
        if trilhos_ferrovia:
            folium.LayerControl(collapsed=False).add_to(mapa)
        return mapa

    if mostrar_pulsos_brutos:
        camada_brutos = folium.FeatureGroup(name="Pulsos brutos", show=False)
        for pulso in pulsos:
            folium.CircleMarker(
                location=(pulso.latitude, pulso.longitude),
                radius=4,
                color=_COR_BORDA_PULSO_BRUTO,
                weight=1,
                fill=True,
                fill_color=_COR_PULSO_BRUTO,
                fill_opacity=0.9,
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
            color=_COR_TRAJETORIA,
            weight=3,
            opacity=0.8,
            dash_array="10,6,2,6",
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
