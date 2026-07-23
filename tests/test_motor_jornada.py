"""Testes do Incremento 1: Motor de Jornada + Atividade + Pausa + HH.

Cobre os casos obrigatorios da secao 9 de
docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md (9.1 a 9.13).
"""

from datetime import datetime, timedelta

import pytest

from workforce_core import MotorJornada, calculo
from workforce_core.entities import Atividade, Pausa
from workforce_core.exceptions import (
    AtividadeEncerramentoComPausaAbertaError,
    AtividadeJaAtivaError,
    JornadaComAtividadeAbertaError,
    JornadaComPausaAbertaError,
    JornadaJaAbertaError,
    JornadaNaoAbertaError,
    PausaExigeAtividadeAtivaError,
    PausaForaDoIntervaloError,
    PausaJaAtivaError,
    PausaMotivoObrigatorioError,
    TimestampInvalidoError,
)


def _dt(hora, minuto, dia=1, mes=1, ano=2026):
    return datetime(ano, mes, dia, hora, minuto)


# ----------------------------------------------------------------------
# 9.1 Fluxo nominal - caso minimo obrigatorio (secao 7.3)
# ----------------------------------------------------------------------
def test_9_1_fluxo_nominal():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(10, 0), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(10, 20))
    motor.encerrar_atividade(_dt(12, 0))
    motor.encerrar_jornada(_dt(12, 10))

    resumo = calculo.resumo_jornada(motor.jornada)

    assert calculo.duracao_jornada_bruta(motor.jornada) == timedelta(hours=4, minutes=10)
    assert resumo["atividades"][0]["bruta"] == timedelta(hours=3, minutes=50)
    assert resumo["atividades"][0]["pausas"] == timedelta(minutes=20)
    assert resumo["atividades"][0]["liquida"] == timedelta(hours=3, minutes=30)
    assert resumo["tempo_classificado"] == timedelta(hours=3, minutes=50)
    assert resumo["tempo_nao_classificado"] == timedelta(minutes=20)


# ----------------------------------------------------------------------
# 9.2 Jornada sem atividade
# ----------------------------------------------------------------------
def test_9_2_jornada_sem_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.encerrar_jornada(_dt(9, 0))

    assert calculo.tempo_classificado_jornada(motor.jornada) == timedelta()
    assert calculo.tempo_nao_classificado(motor.jornada) == timedelta(hours=1)


# ----------------------------------------------------------------------
# 9.3 Atividade sem pausa
# ----------------------------------------------------------------------
def test_9_3_atividade_sem_pausa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.encerrar_atividade(_dt(9, 10))
    motor.encerrar_jornada(_dt(9, 20))

    atividade = motor.jornada.atividades[0]
    assert calculo.duracao_atividade_liquida(atividade) == calculo.duracao_atividade_bruta(atividade)


# ----------------------------------------------------------------------
# 9.4 Atividade com uma pausa
# ----------------------------------------------------------------------
def test_9_4_atividade_com_uma_pausa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(9, 15))
    motor.encerrar_atividade(_dt(10, 0))
    motor.encerrar_jornada(_dt(10, 0))

    atividade = motor.jornada.atividades[0]
    assert calculo.duracao_atividade_bruta(atividade) == timedelta(hours=2)
    assert calculo.duracao_pausas_atividade(atividade) == timedelta(minutes=15)
    assert calculo.duracao_atividade_liquida(atividade) == timedelta(hours=1, minutes=45)


# ----------------------------------------------------------------------
# 9.5 Atividade com varias pausas sequenciais
# ----------------------------------------------------------------------
def test_9_5_atividade_com_varias_pausas():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))

    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(9, 10))

    motor.iniciar_pausa(_dt(10, 0), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(10, 5))

    motor.encerrar_atividade(_dt(11, 0))
    motor.encerrar_jornada(_dt(11, 0))

    atividade = motor.jornada.atividades[0]
    assert calculo.duracao_pausas_atividade(atividade) == timedelta(minutes=15)
    assert calculo.duracao_atividade_liquida(atividade) == timedelta(hours=2, minutes=45)


# ----------------------------------------------------------------------
# 9.6 Tentativa de segunda atividade
# ----------------------------------------------------------------------
def test_9_6_bloqueia_segunda_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(AtividadeJaAtivaError):
        motor.iniciar_atividade(_dt(8, 20))


# ----------------------------------------------------------------------
# 9.7 Tentativa de segunda pausa
# ----------------------------------------------------------------------
def test_9_7_bloqueia_segunda_pausa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    with pytest.raises(PausaJaAtivaError):
        motor.iniciar_pausa(_dt(9, 5), motivo="PAUSA_TESTE")


# ----------------------------------------------------------------------
# 9.8 Encerramento da atividade durante pausa
# ----------------------------------------------------------------------
def test_9_8_bloqueia_encerrar_atividade_com_pausa_aberta():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    with pytest.raises(AtividadeEncerramentoComPausaAbertaError):
        motor.encerrar_atividade(_dt(9, 30))


# ----------------------------------------------------------------------
# 9.9 Encerramento da jornada durante pausa
# ----------------------------------------------------------------------
def test_9_9_bloqueia_encerrar_jornada_com_pausa_aberta():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    with pytest.raises(JornadaComPausaAbertaError):
        motor.encerrar_jornada(_dt(9, 30))


def test_9_9b_bloqueia_encerrar_jornada_com_atividade_aberta():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(JornadaComAtividadeAbertaError):
        motor.encerrar_jornada(_dt(9, 30))


# ----------------------------------------------------------------------
# 9.10 Timestamp invalido
# ----------------------------------------------------------------------
def test_9_10_bloqueia_fim_anterior_ao_inicio_na_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(TimestampInvalidoError):
        motor.encerrar_atividade(_dt(8, 0))


def test_9_10_bloqueia_fim_anterior_ao_inicio_na_pausa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    with pytest.raises(TimestampInvalidoError):
        motor.finalizar_pausa(_dt(8, 50))


def test_9_10_bloqueia_fim_anterior_ao_inicio_na_jornada():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(TimestampInvalidoError):
        motor.encerrar_jornada(_dt(7, 0))


# ----------------------------------------------------------------------
# 9.11 Pausa fora do intervalo da atividade
# ----------------------------------------------------------------------
def test_9_11_bloqueia_pausa_iniciada_antes_da_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(TimestampInvalidoError):
        motor.iniciar_pausa(_dt(8, 0), motivo="PAUSA_TESTE")


def test_9_11_bloqueia_pausa_encerrada_depois_da_atividade():
    # Construcao direta das entidades para validar a regra no motor de
    # calculo, pois o motor de transicoes nao permite finalizar uma pausa
    # apos o encerramento da atividade que a contem (a atividade so encerra
    # sem pausa ativa).
    atividade = Atividade(inicio=_dt(8, 0), fim=_dt(9, 0))
    pausa = Pausa(
        atividade_id=atividade.id,
        motivo="PAUSA_TESTE",
        inicio=_dt(8, 30),
        fim=_dt(9, 30),
    )
    atividade.pausas.append(pausa)

    with pytest.raises(PausaForaDoIntervaloError):
        calculo.duracao_pausas_atividade(atividade)


# ----------------------------------------------------------------------
# 9.12 Evento atravessando meia-noite
# ----------------------------------------------------------------------
def test_9_12_evento_atravessando_meia_noite():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(22, 0, dia=1))
    motor.iniciar_atividade(_dt(22, 30, dia=1))
    motor.iniciar_pausa(_dt(23, 30, dia=1), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(0, 0, dia=2))
    motor.encerrar_atividade(_dt(2, 0, dia=2))
    motor.encerrar_jornada(_dt(2, 30, dia=2))

    resumo = calculo.resumo_jornada(motor.jornada)

    assert calculo.duracao_jornada_bruta(motor.jornada) == timedelta(hours=4, minutes=30)
    assert resumo["atividades"][0]["bruta"] == timedelta(hours=3, minutes=30)
    assert resumo["atividades"][0]["pausas"] == timedelta(minutes=30)
    assert resumo["atividades"][0]["liquida"] == timedelta(hours=3)


# ----------------------------------------------------------------------
# 9.13 Duplicidade de comando
# ----------------------------------------------------------------------
def test_9_13_duplicidade_iniciar_jornada_nao_corrompe_estado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(JornadaJaAbertaError):
        motor.iniciar_jornada(_dt(8, 5))

    assert motor.jornada.inicio == _dt(8, 0)


def test_9_13_duplicidade_encerrar_jornada_nao_corrompe_estado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.encerrar_jornada(_dt(9, 0))

    with pytest.raises(JornadaNaoAbertaError):
        motor.encerrar_jornada(_dt(10, 0))

    assert motor.jornada.fim == _dt(9, 0)


def test_9_13_duplicidade_iniciar_pausa_nao_corrompe_estado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    with pytest.raises(PausaJaAtivaError):
        motor.iniciar_pausa(_dt(9, 1), motivo="PAUSA_TESTE")

    atividade = motor.jornada.atividades[0]
    assert len(atividade.pausas) == 1
    assert atividade.pausas[0].inicio == _dt(9, 0)


# ----------------------------------------------------------------------
# Regras estruturais adicionais da secao 8 (nao numeradas na secao 9,
# mas fechadas para o Incremento 1)
# ----------------------------------------------------------------------
def test_atividade_exige_jornada_aberta():
    motor = MotorJornada("12345")

    with pytest.raises(JornadaNaoAbertaError):
        motor.iniciar_atividade(_dt(8, 0))


def test_pausa_exige_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(PausaExigeAtividadeAtivaError):
        motor.iniciar_pausa(_dt(8, 30), motivo="PAUSA_TESTE")


def test_pausa_exige_motivo_obrigatorio():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(PausaMotivoObrigatorioError):
        motor.iniciar_pausa(_dt(9, 0), motivo="")
