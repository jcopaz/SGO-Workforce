"""Exportacao GeoJSON (Incremento 11).

docs/14_EXPORTACOES.md, secao "GeoJSON": "Pontos e trajetorias para QGIS/
ArcGIS. Aplicar permissao e minimizacao de dados pessoais."

Sem sistema de permissao/perfil ainda (nenhum incremento implementou
autenticacao), a unica forma responsavel de "aplicar minimizacao de dados
pessoais" hoje e por padrao: `colaborador_matricula` so entra nas
propriedades de cada feature se `incluir_identificacao_pessoal=True` for
passado explicitamente por quem chama - o padrao e nao incluir.

Trajetorias usam workforce_core.geo.simplificar_trajetoria antes de gerar
o LineString, seguindo a recomendacao de performance de
docs/13_MAPA_OPERACIONAL.md ("nao carregar pulsos brutos integralmente
sem necessidade").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from workforce_core.entities import PulsoGps
from workforce_core.geo import simplificar_trajetoria


def _propriedades_pulso(pulso: PulsoGps, *, incluir_identificacao_pessoal: bool) -> Dict[str, Any]:
    propriedades: Dict[str, Any] = {
        "jornada_id": str(pulso.jornada_id),
        "timestamp_dispositivo": pulso.timestamp_dispositivo.isoformat(),
        "precisao_metros": pulso.precisao_metros,
        "qualidade": pulso.qualidade.value,
    }
    if incluir_identificacao_pessoal:
        propriedades["colaborador_matricula"] = pulso.colaborador_matricula
    return propriedades


def feature_collection_pontos(
    pulsos: List[PulsoGps], *, incluir_identificacao_pessoal: bool = False
) -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [pulso.longitude, pulso.latitude]},
                "properties": _propriedades_pulso(
                    pulso, incluir_identificacao_pessoal=incluir_identificacao_pessoal
                ),
            }
            for pulso in pulsos
        ],
    }


def feature_collection_trajetorias(
    pulsos_por_jornada: Dict[Any, List[PulsoGps]],
    *,
    distancia_simplificacao_metros: float,
    incluir_identificacao_pessoal: bool = False,
) -> Dict[str, Any]:
    """Uma feature LineString por jornada, com a trajetoria ja simplificada.

    `distancia_simplificacao_metros` e sempre parametro explicito - sem
    valor padrao embutido, mesmo padrao de workforce_core.geo (ADR-0010).
    """
    features = []
    for jornada_id, pulsos in pulsos_por_jornada.items():
        trajetoria = simplificar_trajetoria(
            pulsos, distancia_minima_metros=distancia_simplificacao_metros
        )
        if len(trajetoria) < 2:
            continue
        propriedades: Dict[str, Any] = {
            "jornada_id": str(jornada_id),
            "quantidade_pulsos_original": len(pulsos),
            "quantidade_pontos_simplificados": len(trajetoria),
        }
        if incluir_identificacao_pessoal and trajetoria:
            propriedades["colaborador_matricula"] = trajetoria[0].colaborador_matricula
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[p.longitude, p.latitude] for p in trajetoria],
                },
                "properties": propriedades,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def exportar_geojson(
    caminho: Union[str, Path], colecao: Dict[str, Any]
) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(colecao, indent=2, ensure_ascii=False), encoding="utf-8")
    return caminho
