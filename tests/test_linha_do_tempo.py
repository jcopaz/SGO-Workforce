"""Testes do grafico "linha do tempo da jornada" (ADR-0051, pedido do
responsavel pelo produto em 2026-08-04): visualizacao dia x hora dos
apontamentos sequenciais, no mapa operacional (uma jornada) e na Visao
Geral (um colaborador, varios dias do mes).

`workforce_core.consolidacao.linha_do_tempo` (a decomposicao da jornada
em intervalos) e testada em tests/test_consolidacao.py - aqui so o
recorte por dia calendario (`dados.fatiar_linha_do_tempo_por_dia`) e o
grafico (`graficos.grafico_linha_do_tempo`).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from dados import SegmentoLinhaDoTempo, fatiar_linha_do_tempo_por_dia
from graficos import grafico_linha_do_tempo, legenda_linha_do_tempo
from mapa import cor_por_rotulo
from workforce_core.consolidacao import IntervaloClassificado


def test_fatiar_linha_do_tempo_por_dia_intervalo_simples_dentro_de_um_dia():
    intervalo = IntervaloClassificado(
        inicio=datetime(2026, 8, 1, 8, 0),
        fim=datetime(2026, 8, 1, 9, 30),
        tipo="ATIVIDADE",
        motivo=None,
    )

    por_dia = fatiar_linha_do_tempo_por_dia([intervalo])

    assert list(por_dia.keys()) == [date(2026, 8, 1)]
    segmentos = por_dia[date(2026, 8, 1)]
    assert len(segmentos) == 1
    assert segmentos[0].minuto_inicio == 8 * 60
    assert segmentos[0].minuto_fim == 9 * 60 + 30
    assert segmentos[0].tipo == "ATIVIDADE"


def test_fatiar_linha_do_tempo_por_dia_converte_utc_para_horario_de_brasilia():
    # 23h de Brasilia em 01/08 e 02h UTC do dia seguinte.
    intervalo = IntervaloClassificado(
        inicio=datetime(2026, 8, 2, 2, 0, tzinfo=timezone.utc),
        fim=datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc),
        tipo="EVENTO_SECUNDARIO",
        motivo="EE12",
    )

    por_dia = fatiar_linha_do_tempo_por_dia([intervalo])

    assert list(por_dia.keys()) == [date(2026, 8, 1)]
    segmento = por_dia[date(2026, 8, 1)][0]
    assert segmento.minuto_inicio == 23 * 60
    assert segmento.minuto_fim == 24 * 60


def test_fatiar_linha_do_tempo_por_dia_intervalo_atravessando_meia_noite_vira_dois_segmentos():
    intervalo = IntervaloClassificado(
        inicio=datetime(2026, 8, 1, 22, 0),
        fim=datetime(2026, 8, 2, 1, 30),
        tipo="PAUSA",
        motivo="EE02",
    )

    por_dia = fatiar_linha_do_tempo_por_dia([intervalo])

    assert sorted(por_dia.keys()) == [date(2026, 8, 1), date(2026, 8, 2)]

    segmento_dia1 = por_dia[date(2026, 8, 1)][0]
    assert segmento_dia1.minuto_inicio == 22 * 60
    assert segmento_dia1.minuto_fim == 1440

    segmento_dia2 = por_dia[date(2026, 8, 2)][0]
    assert segmento_dia2.minuto_inicio == 0
    assert segmento_dia2.minuto_fim == 90


def test_fatiar_linha_do_tempo_por_dia_intervalo_de_varios_dias_seguidos():
    intervalo = IntervaloClassificado(
        inicio=datetime(2026, 8, 1, 23, 0),
        fim=datetime(2026, 8, 3, 1, 0),
        tipo="SEM_ATIVIDADE",
        motivo=None,
    )

    por_dia = fatiar_linha_do_tempo_por_dia([intervalo])

    assert sorted(por_dia.keys()) == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    assert por_dia[date(2026, 8, 1)][0].minuto_inicio == 23 * 60
    assert por_dia[date(2026, 8, 1)][0].minuto_fim == 1440
    assert por_dia[date(2026, 8, 2)][0].minuto_inicio == 0
    assert por_dia[date(2026, 8, 2)][0].minuto_fim == 1440
    assert por_dia[date(2026, 8, 3)][0].minuto_inicio == 0
    assert por_dia[date(2026, 8, 3)][0].minuto_fim == 60


def test_fatiar_linha_do_tempo_por_dia_multiplos_intervalos_mesmo_dia_mantem_ordem():
    intervalos = [
        IntervaloClassificado(datetime(2026, 8, 1, 8, 0), datetime(2026, 8, 1, 9, 0), "ATIVIDADE", None),
        IntervaloClassificado(datetime(2026, 8, 1, 9, 0), datetime(2026, 8, 1, 9, 15), "PAUSA", "EE02"),
        IntervaloClassificado(datetime(2026, 8, 1, 9, 15), datetime(2026, 8, 1, 10, 0), "ATIVIDADE", None),
    ]

    por_dia = fatiar_linha_do_tempo_por_dia(intervalos)

    tipos = [s.tipo for s in por_dia[date(2026, 8, 1)]]
    assert tipos == ["ATIVIDADE", "PAUSA", "ATIVIDADE"]


def test_fatiar_linha_do_tempo_por_dia_lista_vazia_devolve_dict_vazio():
    assert fatiar_linha_do_tempo_por_dia([]) == {}


# ----------------------------------------------------------------------
# grafico_linha_do_tempo (ADR-0051) - barra empilhada com series
# genericas por posicao (nao por codigo, ver docstring da funcao).
# ----------------------------------------------------------------------
def _segmento(dia, hora_inicio, minuto_inicio, hora_fim, minuto_fim, tipo, motivo=None):
    return SegmentoLinhaDoTempo(
        data=dia,
        minuto_inicio=hora_inicio * 60 + minuto_inicio,
        minuto_fim=hora_fim * 60 + minuto_fim,
        tipo=tipo,
        motivo=motivo,
    )


def test_grafico_linha_do_tempo_sem_dados_nao_quebra():
    grafico = grafico_linha_do_tempo({})
    opcoes = json.loads(grafico.dump_options())
    assert opcoes["xAxis"][0]["data"] == []


def test_grafico_linha_do_tempo_eixo_y_em_horas_0_a_24():
    dia = date(2026, 8, 1)
    por_dia = {dia: [_segmento(dia, 7, 0, 8, 0, "ATIVIDADE")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    eixo_y = opcoes["yAxis"][0]
    assert eixo_y["min"] == 0
    assert eixo_y["max"] == 24
    assert eixo_y["interval"] == 1
    assert eixo_y["axisLabel"]["formatter"] == "{value}:00"


def test_grafico_linha_do_tempo_um_segmento_posicao_e_cor_corretas():
    dia = date(2026, 8, 1)
    por_dia = {dia: [_segmento(dia, 7, 0, 8, 30, "EVENTO_SECUNDARIO", "EE12")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    # series[0] e sempre a base invisivel (tempo antes do 1o apontamento);
    # series[1] e o primeiro (e unico, aqui) apontamento real do dia.
    assert opcoes["series"][0]["data"][0]["value"] == 7.0  # 07:00 = 7h de base invisivel
    item = opcoes["series"][1]["data"][0]
    assert item["value"] == 1.5  # 07:00-08:30 = 90min = 1.5h
    assert "EE12" in item["name"]
    assert "07:00" in item["name"] and "08:30" in item["name"]
    assert "90 min" in item["name"]
    assert item["itemStyle"]["color"] == cor_por_rotulo("EE12 - Deslocamento rodoviário")


def test_grafico_linha_do_tempo_dias_com_quantidades_diferentes_de_segmentos():
    dia1 = date(2026, 8, 1)
    dia2 = date(2026, 8, 2)
    por_dia = {
        dia1: [_segmento(dia1, 8, 0, 9, 0, "ATIVIDADE")],
        dia2: [
            _segmento(dia2, 8, 0, 9, 0, "ATIVIDADE"),
            _segmento(dia2, 9, 0, 9, 15, "PAUSA", "EE02"),
        ],
    }

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    # 1 serie base + 2 series de posicao (dia2 tem 2 segmentos, o maximo).
    assert len(opcoes["series"]) == 3
    # dia1 (indice 0) so tem 1 segmento - a 2a posicao deve ser invisivel/zero pra ele.
    segunda_posicao_dia1 = opcoes["series"][2]["data"][0]
    assert segunda_posicao_dia1["value"] == 0
    # pyecharts omite a chave "name" quando o valor e string vazia -
    # ausencia de nome tem o mesmo efeito de nome vazio pro tooltip.
    assert segunda_posicao_dia1.get("name", "") == ""
    # dia2 (indice 1) usa as duas posicoes normalmente.
    segunda_posicao_dia2 = opcoes["series"][2]["data"][1]
    assert segunda_posicao_dia2["value"] > 0
    assert "EE02" in segunda_posicao_dia2["name"]


def test_grafico_linha_do_tempo_legenda_oculta():
    dia = date(2026, 8, 1)
    por_dia = {dia: [_segmento(dia, 8, 0, 9, 0, "ATIVIDADE")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    assert opcoes["legend"][0]["show"] is False


# ----------------------------------------------------------------------
# Codigo dentro do segmento + dataZoom por scroll (pedido do responsavel
# do produto em 2026-08-07).
# ----------------------------------------------------------------------
def test_grafico_linha_do_tempo_mostra_codigo_dentro_do_segmento_longo():
    dia = date(2026, 8, 1)
    # 90 min - acima do limiar de 30min pro rotulo nao ficar espremido.
    por_dia = {dia: [_segmento(dia, 7, 0, 8, 30, "EVENTO_SECUNDARIO", "EE12")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    item = opcoes["series"][1]["data"][0]
    assert item["label"]["show"] is True
    assert item["label"]["formatter"] == "EE12"


def test_grafico_linha_do_tempo_esconde_codigo_em_segmento_curto():
    dia = date(2026, 8, 1)
    # 10 min - abaixo do limiar, nao deveria ganhar rotulo dentro da barra.
    por_dia = {dia: [_segmento(dia, 7, 0, 7, 10, "EVENTO_SECUNDARIO", "EE12")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    item = opcoes["series"][1]["data"][0]
    assert "label" not in item


def test_grafico_linha_do_tempo_codigo_atividade_e_atendimento_falha():
    # ATIVIDADE/ATENDIMENTO_FALHA nao tem "motivo" (so PAUSA/EVENTO_SECUNDARIO
    # tem) - o codigo vem fixo (EE17/EE21, ja documentados em app.js).
    dia = date(2026, 8, 1)
    por_dia = {
        dia: [
            _segmento(dia, 7, 0, 8, 0, "ATIVIDADE"),
            _segmento(dia, 8, 0, 9, 0, "ATENDIMENTO_FALHA"),
        ]
    }

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    assert opcoes["series"][1]["data"][0]["label"]["formatter"] == "EE17"
    assert opcoes["series"][2]["data"][0]["label"]["formatter"] == "EE21"


def test_grafico_linha_do_tempo_sem_atividade_nunca_ganha_codigo():
    dia = date(2026, 8, 1)
    por_dia = {dia: [_segmento(dia, 7, 0, 9, 0, "SEM_ATIVIDADE")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    assert "label" not in opcoes["series"][1]["data"][0]


def test_grafico_linha_do_tempo_tem_datazoom_vertical_por_scroll():
    dia = date(2026, 8, 1)
    por_dia = {dia: [_segmento(dia, 8, 0, 9, 0, "ATIVIDADE")]}

    grafico = grafico_linha_do_tempo(por_dia)
    opcoes = json.loads(grafico.dump_options())

    datazoom = opcoes["dataZoom"][0]
    assert datazoom["type"] == "inside"
    assert datazoom["orient"] == "vertical"


# ----------------------------------------------------------------------
# legenda_linha_do_tempo - legenda HTML montada a parte (o grafico acima
# nao usa a legenda nativa do ECharts, series sinteticas por posicao).
# ----------------------------------------------------------------------
def test_legenda_linha_do_tempo_rotulos_distintos_ordenados():
    dia1 = date(2026, 8, 1)
    dia2 = date(2026, 8, 2)
    por_dia = {
        dia1: [
            _segmento(dia1, 7, 0, 8, 0, "ATIVIDADE"),
            _segmento(dia1, 8, 0, 8, 15, "PAUSA", "EE02"),
        ],
        dia2: [
            _segmento(dia2, 7, 0, 8, 0, "ATIVIDADE"),  # repetido de proposito - so 1 entrada
            _segmento(dia2, 8, 0, 8, 30, "EVENTO_SECUNDARIO", "EE12"),
        ],
    }

    legenda = legenda_linha_do_tempo(por_dia)

    rotulos = [rotulo for rotulo, _cor in legenda]
    assert rotulos == sorted(set(rotulos))  # sem duplicata, ordenado
    assert "Atividade" in rotulos
    assert any("EE02" in r for r in rotulos)
    assert any("EE12" in r for r in rotulos)
    for rotulo, cor in legenda:
        assert cor == cor_por_rotulo(rotulo)


def test_legenda_linha_do_tempo_vazia_sem_segmentos():
    assert legenda_linha_do_tempo({}) == []
