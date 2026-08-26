"""Testes de workforce_storage.serializacao para Patio (cadastro de patios,
ADR-0072).
"""

from workforce_core.patio import Patio
from workforce_storage.serializacao import patio_de_dict, patio_para_dict


def test_patio_round_trip():
    patio = Patio(
        codigo="IPN",
        nome="Pátio Prainha",
        coordenacao="Piaçaguera",
        latitude=-23.948095774842265,
        longitude=-46.30579661328678,
        ativo=True,
    )

    dados = patio_para_dict(patio)
    reconstruido = patio_de_dict(dados)

    assert reconstruido == patio


def test_patio_para_dict_inclui_inativo():
    patio = Patio(
        codigo="ICQ",
        nome="Pátio Casqueiro",
        coordenacao="Piaçaguera",
        latitude=-23.91531040683147,
        longitude=-46.41890410191962,
        ativo=False,
    )
    dados = patio_para_dict(patio)
    assert dados["ativo"] is False


def test_patio_de_dict_usa_defaults_para_campos_ausentes():
    # Compatibilidade retroativa: um dict sem "coordenacao"/"ativo" ainda
    # deve reconstruir um Patio valido (mesmo espirito de
    # entrada_catalogo_de_dict_usa_defaults_para_campos_ausentes).
    patio = patio_de_dict(
        {"codigo": "X", "nome": "Teste", "latitude": 1.0, "longitude": 2.0}
    )

    assert patio.coordenacao == ""
    assert patio.ativo is True


def test_patio_de_dict_converte_latitude_longitude_para_float():
    # JSON pode trazer numeros como int quando o valor cadastrado for
    # inteiro (ex.: latitude 0) - garante que o dominio sempre recebe float.
    patio = patio_de_dict(
        {"codigo": "X", "nome": "Teste", "coordenacao": "C", "latitude": 1, "longitude": 2}
    )

    assert patio.latitude == 1.0
    assert patio.longitude == 2.0
    assert isinstance(patio.latitude, float)
    assert isinstance(patio.longitude, float)
