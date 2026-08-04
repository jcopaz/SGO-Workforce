"""Leitura da malha ferrea da MRS a partir de um KML exportado do Google
Earth (`malha_mrs.kml`, raiz do repositorio), para sobrepor no mapa
operacional como camada de referencia visual (pedido do responsavel pelo
produto em 2026-08-04).

Parser deliberadamente minimo via defusedxml (blindado contra XXE/entity
expansion - nunca usar xml.etree.ElementTree puro para parsear XML/KML,
mesmo de origem "confiavel", ver
https://docs.python.org/3/library/xml.html#xml-vulnerabilities) em vez de
fastkml/geopandas - o KML de origem so usa
Document > Placemark > MultiGeometry > LineString > coordinates, e trazer
uma dependencia pesada (geopandas exige GDAL) so para isso nao se paga.
`parsear_kml` busca <coordinates> em qualquer profundidade (`Element.iter`),
entao continua funcionando mesmo que o KML seja reexportado com Placemarks
organizados em pastas ou sem o MultiGeometry envolvente.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import defusedxml.ElementTree as ET

_NAMESPACE_KML = "{http://www.opengis.net/kml/2.2}"

_DIRETORIO_MODULO = Path(__file__).resolve().parent
CAMINHO_MALHA_MRS_KML = _DIRETORIO_MODULO.parent / "malha_mrs.kml"


def parsear_kml(caminho: Path) -> List[List[Tuple[float, float]]]:
    """Devolve uma lista de trilhos, cada um uma lista de pontos
    (latitude, longitude) - um trilho por elemento <coordinates> do KML
    (coordenadas do KML sao longitude,latitude,altitude - invertidas aqui
    para o par (lat, lon) que folium espera).

    Nunca lanca: arquivo ausente ou KML mal formado devolve lista vazia -
    a malha ferrea e uma camada decorativa/de referencia, uma falha aqui
    nao pode derrubar o mapa operacional (mesmo principio de robustez das
    demais camadas, ver mapa.py).
    """
    if not caminho.exists():
        return []
    try:
        raiz = ET.parse(caminho).getroot()
    except ET.ParseError:
        return []

    trilhos: List[List[Tuple[float, float]]] = []
    for elemento in raiz.iter(f"{_NAMESPACE_KML}coordinates"):
        texto = (elemento.text or "").strip()
        if not texto:
            continue
        pontos: List[Tuple[float, float]] = []
        for tripla in texto.split():
            partes = tripla.split(",")
            if len(partes) < 2:
                continue
            try:
                longitude, latitude = float(partes[0]), float(partes[1])
            except ValueError:
                continue
            pontos.append((latitude, longitude))
        if len(pontos) > 1:
            trilhos.append(pontos)
    return trilhos


_trilhos_malha_mrs_em_cache: Optional[List[List[Tuple[float, float]]]] = None


def carregar_trilhos_malha_mrs() -> List[List[Tuple[float, float]]]:
    """Le malha_mrs.kml uma unica vez por processo (cache em memoria,
    mesmo padrao de graficos.py::_ler_js_echarts_local - o arquivo tem
    ~630KB e nunca muda em runtime, reler a cada rerun do Streamlit seria
    desperdicio)."""
    global _trilhos_malha_mrs_em_cache
    if _trilhos_malha_mrs_em_cache is None:
        _trilhos_malha_mrs_em_cache = parsear_kml(CAMINHO_MALHA_MRS_KML)
    return _trilhos_malha_mrs_em_cache
