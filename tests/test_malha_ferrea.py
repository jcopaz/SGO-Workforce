"""Testes de painel/malha_ferrea.py (leitura da malha ferrea da MRS a
partir de KML, sobreposta no mapa operacional a pedido do responsavel
pelo produto em 2026-08-04).

parsear_kml e pura (sem cache, sem depender do arquivo real do
repositorio) - testada com fixtures pequenas escritas em tmp_path.
carregar_trilhos_malha_mrs e testada contra o arquivo real
(malha_mrs.kml, raiz do repositorio) so pra confirmar que o parser da
conta do formato de verdade, sem repetir os casos de borda ja cobertos
por parsear_kml.
"""

from __future__ import annotations

from pathlib import Path

from malha_ferrea import CAMINHO_MALHA_MRS_KML, carregar_trilhos_malha_mrs, parsear_kml

_KML_VALIDO = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Placemark>
<name>trecho 1</name>
<MultiGeometry>
<LineString>
<coordinates>
-44.0,-20.0,0 -44.1,-20.1,0 -44.2,-20.2,0
</coordinates>
</LineString>
<LineString>
<coordinates>
-43.0,-21.0,0 -43.1,-21.1,0
</coordinates>
</LineString>
</MultiGeometry>
</Placemark>
</Document>
</kml>
"""


def test_parsear_kml_devolve_um_trilho_por_linestring(tmp_path):
    caminho = tmp_path / "malha.kml"
    caminho.write_text(_KML_VALIDO, encoding="utf-8")

    trilhos = parsear_kml(caminho)

    assert len(trilhos) == 2
    assert trilhos[0] == [(-20.0, -44.0), (-20.1, -44.1), (-20.2, -44.2)]
    assert trilhos[1] == [(-21.0, -43.0), (-21.1, -43.1)]


def test_parsear_kml_inverte_lon_lat_do_kml_para_lat_lon(tmp_path):
    caminho = tmp_path / "malha.kml"
    caminho.write_text(_KML_VALIDO, encoding="utf-8")

    trilhos = parsear_kml(caminho)
    primeiro_ponto = trilhos[0][0]

    # KML grava longitude,latitude,altitude - o par devolvido e (lat, lon).
    assert primeiro_ponto[0] == -20.0  # latitude
    assert primeiro_ponto[1] == -44.0  # longitude


def test_parsear_kml_arquivo_ausente_devolve_lista_vazia(tmp_path):
    trilhos = parsear_kml(tmp_path / "nao-existe.kml")
    assert trilhos == []


def test_parsear_kml_xml_malformado_nunca_lanca(tmp_path):
    caminho = tmp_path / "quebrado.kml"
    caminho.write_text("<kml><Document><Placemark>", encoding="utf-8")

    trilhos = parsear_kml(caminho)
    assert trilhos == []


def test_parsear_kml_ignora_coordinates_com_um_unico_ponto(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><Placemark><LineString>
<coordinates>-44.0,-20.0,0</coordinates>
</LineString></Placemark></Document></kml>
"""
    caminho = tmp_path / "ponto-unico.kml"
    caminho.write_text(kml, encoding="utf-8")

    assert parsear_kml(caminho) == []


def test_carregar_trilhos_malha_mrs_le_o_arquivo_real_do_repositorio():
    trilhos = carregar_trilhos_malha_mrs()

    assert CAMINHO_MALHA_MRS_KML.exists()
    assert len(trilhos) > 0
    assert all(len(trilho) > 1 for trilho in trilhos)
    # Coordenadas plausiveis para a area de atuacao da MRS (Sudeste/Brasil).
    for trilho in trilhos:
        for latitude, longitude in trilho:
            assert -34 < latitude < 6
            assert -74 < longitude < -34


def test_carregar_trilhos_malha_mrs_e_cacheado_por_processo():
    primeira_chamada = carregar_trilhos_malha_mrs()
    segunda_chamada = carregar_trilhos_malha_mrs()

    assert primeira_chamada is segunda_chamada
