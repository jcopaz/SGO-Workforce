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

import hashlib
import html
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import folium

from dados import rotulo_motivo
from workforce_core.catalogo import CatalogoMotivos
from workforce_core.consolidacao import ClassificacaoInstante
from workforce_core.entities import PulsoGps
from workforce_core.enums import QualidadePulso
from workforce_core.fuso_horario import para_horario_brasil
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

# Pulso marcado como suspeito por workforce_core.qualidade_gps (ADR-0054,
# limiares aprovados em painel/dados.py) ganha borda vermelha grossa
# tracejada - continua desenhado (docs/08: "marcados, nao apagados"), so
# fica visualmente distinguivel do resto. NAO_AVALIADO (pulso antigo,
# capturado antes do ADR-0054, ou de fonte que nunca reclassifica) conta
# como confiavel aqui de proposito - "sem avaliacao" nao e "reprovado".
_COR_QUALIDADE_SUSPEITA = "#D50000"
_QUALIDADES_CONFIAVEIS = frozenset({QualidadePulso.OK, QualidadePulso.NAO_AVALIADO})

_LOCAL_SEM_DADOS = (-15.7801, -47.9292)  # Brasilia - fallback visual quando nao ha nenhum pulso

# Paleta qualitativa (cores bem distinguiveis entre si) para colorir pulsos
# por atividade/pausa/evento (pedido do responsavel pelo produto em
# 2026-08-04, ver ADR-0047). Atribuicao por hash estavel do rotulo (nao
# por ordem de aparicao) - mesmo codigo (ex.: "EE02 - Refeicao") sempre
# cai na mesma cor, em qualquer jornada, sem precisar manter um registro
# global de codigo->cor.
_PALETA_CATEGORIAS = [
    "#1E88E5",  # azul
    "#FB8C00",  # laranja
    "#43A047",  # verde
    "#8E24AA",  # roxo
    "#00ACC1",  # ciano
    "#F4511E",  # laranja avermelhado
    "#3949AB",  # indigo
    "#7CB342",  # verde-lima
    "#D81B60",  # rosa
    "#6D4C41",  # marrom
    "#00897B",  # verde-azulado
    "#C0CA33",  # amarelo-esverdeado
]
_COR_SEM_ATIVIDADE = "#9E9E9E"  # cinza - jornada aberta, nada especifico em andamento


def rotulo_classificacao_pulso(
    classificacao: ClassificacaoInstante, catalogo: Optional[CatalogoMotivos] = None
) -> str:
    """Rotulo legivel para filtro/legenda a partir de uma
    `ClassificacaoInstante` (`workforce_core.consolidacao.classificar_instante`).
    Reaproveita o mesmo formato "codigo - descricao" ja usado em
    `painel/dados.py::rotulo_motivo` para pausa/evento secundario."""
    if classificacao.tipo == "ATIVIDADE":
        return "Atividade"
    if classificacao.tipo == "ATENDIMENTO_FALHA":
        return "Atendimento de falha"
    if classificacao.tipo == "SEM_ATIVIDADE":
        return "Sem atividade"
    # PAUSA e EVENTO_SECUNDARIO sempre tem motivo.
    return rotulo_motivo(classificacao.motivo, catalogo)


def cor_por_rotulo(rotulo: str) -> str:
    """Cor deterministica (mesmo rotulo -> mesma cor sempre, em qualquer
    processo/jornada) via hash estavel - `hash()` nativo do Python varia
    entre execucoes (PYTHONHASHSEED aleatorio por padrao), por isso usa
    hashlib."""
    if rotulo == "Sem atividade":
        return _COR_SEM_ATIVIDADE
    indice = int(hashlib.md5(rotulo.encode("utf-8")).hexdigest(), 16) % len(_PALETA_CATEGORIAS)
    return _PALETA_CATEGORIAS[indice]


def _centro(pulsos: List[PulsoGps]) -> Tuple[float, float]:
    if not pulsos:
        return _LOCAL_SEM_DADOS
    return (
        sum(p.latitude for p in pulsos) / len(pulsos),
        sum(p.longitude for p in pulsos) / len(pulsos),
    )


def _horario_legivel(momento) -> str:
    """Horario de Brasilia, formato dd/mm/aaaa hh:mm:ss - mesma conversao
    de painel/dados.py::formatar_data_hora (fonte unica de apresentacao
    de horario), evita repetir isoformat() cru (UTC, tecnico demais pro
    popup) em cada camada do mapa."""
    convertido = para_horario_brasil(momento)
    return convertido.strftime("%d/%m/%Y %H:%M:%S") if convertido is not None else "--"


def _popup_pulso(pulso: PulsoGps) -> str:
    linhas = [
        f"Colaborador: {html.escape(pulso.colaborador_matricula)}",
        f"Horario: {html.escape(_horario_legivel(pulso.timestamp_dispositivo))}",
        f"Precisao: {pulso.precisao_metros:.0f} m",
        f"Qualidade: {html.escape(pulso.qualidade.value)}",
    ]
    return "<br>".join(linhas)


def _popup_cluster(cluster: ClusterPermanencia) -> str:
    linhas = [
        "Cluster de permanencia (inferencia, nao prova de presenca)",
        f"Inicio: {html.escape(_horario_legivel(cluster.inicio))}",
        f"Fim: {html.escape(_horario_legivel(cluster.fim))}",
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
    cor_por_pulso: Optional[Dict[UUID, str]] = None,
    marco_inicio: Optional[PulsoGps] = None,
    marco_fim: Optional[PulsoGps] = None,
) -> folium.Map:
    """Monta o mapa com as camadas de docs/13_MAPA_OPERACIONAL.md que ja
    sao possiveis com o que existe hoje: pulsos brutos (coloridos por
    atividade quando `cor_por_pulso` e informado - ver
    `rotulo_classificacao_pulso`/`cor_por_rotulo`), trajetoria
    simplificada, clusters de permanencia, marcos de inicio/fim
    (`marco_inicio`/`marco_fim` - pedido do responsavel pelo produto em
    2026-08-04) e (opcional) a malha ferrea da MRS como camada de
    referencia (`painel/malha_ferrea.py`).

    `marco_inicio`/`marco_fim` sao passados explicitamente por quem chama
    (em vez de inferidos de `pulsos` aqui dentro) para continuarem
    representando o inicio/fim REAL da jornada mesmo quando `pulsos` ja
    vem filtrado por atividade/periodo - o marco nao deveria sumir so
    porque o filtro atual nao inclui aquele pulso especifico.

    Falhas por sintoma/impacto e heatmap de HH ficam para quando houver
    mais volume de dados reais para validar a utilidade de cada camada
    adicional (ver ADR-0010).

    Pedido do responsavel pelo produto em 2026-08-04 (ADR-0049): so a
    trajetoria simplificada e opcional/togglable - malha ferrea, marcos
    de inicio/fim, pulsos brutos (ja selecionaveis por atividade/data/
    horario nos filtros da tela, nao precisam de outro toggle no mapa) e
    clusters de permanencia sao sempre desenhados direto no mapa, sem
    passar por `FeatureGroup`/`LayerControl` - mapa mais limpo, e o
    controle de camadas deixa de listar "escolhas" que na pratica nunca
    faziam sentido desligar. O tile base tambem nao aparece mais no
    controle (`TileLayer(..., control=False)`) - so existe um tile, nao e
    uma escolha real.
    """
    mapa = folium.Map(location=_centro(pulsos), zoom_start=14 if pulsos else 4, tiles=None)
    folium.TileLayer(tiles=_TILES_BASEMAP, control=False).add_to(mapa)

    if trilhos_ferrovia:
        for trilho in trilhos_ferrovia:
            folium.PolyLine(
                locations=trilho,
                color=_COR_MALHA_FERREA,
                weight=2,
                opacity=0.85,
                tooltip="Malha ferrea MRS",
            ).add_to(mapa)

    if marco_inicio is not None:
        folium.Marker(
            location=(marco_inicio.latitude, marco_inicio.longitude),
            icon=folium.Icon(color="green", icon="play"),
            tooltip="Inicio da jornada",
            popup=folium.Popup(
                f"Inicio da jornada<br>Horario: {html.escape(_horario_legivel(marco_inicio.timestamp_dispositivo))}",
                max_width=300,
            ),
        ).add_to(mapa)
    if marco_fim is not None:
        folium.Marker(
            location=(marco_fim.latitude, marco_fim.longitude),
            icon=folium.Icon(color="red", icon="stop"),
            tooltip="Fim da jornada",
            popup=folium.Popup(
                f"Fim da jornada<br>Horario: {html.escape(_horario_legivel(marco_fim.timestamp_dispositivo))}",
                max_width=300,
            ),
        ).add_to(mapa)

    if not pulsos:
        return mapa

    if mostrar_pulsos_brutos:
        for pulso in pulsos:
            suspeito = pulso.qualidade not in _QUALIDADES_CONFIAVEIS
            cor_categoria = cor_por_pulso.get(pulso.id) if cor_por_pulso else None
            cor_marcador = cor_categoria or _COR_PULSO_BRUTO
            cor_borda = _COR_BORDA_PULSO_BRUTO if cor_categoria is None else cor_marcador
            folium.CircleMarker(
                location=(pulso.latitude, pulso.longitude),
                radius=6 if suspeito else 4,
                color=_COR_QUALIDADE_SUSPEITA if suspeito else cor_borda,
                weight=3 if suspeito else 1,
                dash_array="4,3" if suspeito else None,
                fill=True,
                fill_color=cor_marcador,
                fill_opacity=0.9,
                popup=folium.Popup(_popup_pulso(pulso), max_width=300),
            ).add_to(mapa)

    # Trajetoria/clusters sao camadas de INFERENCIA (docs/13: "nunca prova
    # de presenca"), diferente do pulso bruto acima (registro operacional
    # que nunca some do mapa, so marcado). Pulso suspeito (precisao ruim,
    # salto impossivel, velocidade incompativel) fica de fora dessas duas
    # camadas derivadas - e exatamente o caso que motivou o ADR-0054
    # (pulso final de uma jornada real aparecendo longe do local certo,
    # puxando a trajetoria/linha reta ate ele).
    pulsos_confiaveis = [p for p in pulsos if p.qualidade in _QUALIDADES_CONFIAVEIS]

    trajetoria = simplificar_trajetoria(
        pulsos_confiaveis, distancia_minima_metros=distancia_simplificacao_metros
    )
    if len(trajetoria) > 1:
        camada_trajetoria = folium.FeatureGroup(name="Traçar trajetória", show=True)
        folium.PolyLine(
            locations=[(p.latitude, p.longitude) for p in trajetoria],
            color=_COR_TRAJETORIA,
            weight=3,
            opacity=0.8,
            dash_array="10,6,2,6",
        ).add_to(camada_trajetoria)
        camada_trajetoria.add_to(mapa)
        folium.LayerControl(collapsed=False).add_to(mapa)

    clusters = agrupar_permanencia(
        pulsos_confiaveis, raio_metros=raio_cluster_metros, tempo_minimo=tempo_minimo_cluster
    )
    if clusters:
        for cluster in clusters:
            folium.CircleMarker(
                location=(cluster.latitude_media, cluster.longitude_media),
                radius=8 + min(cluster.quantidade_pulsos, 20),
                color="purple",
                fill=True,
                fill_opacity=0.4,
                popup=folium.Popup(_popup_cluster(cluster), max_width=300),
            ).add_to(mapa)

    return mapa
