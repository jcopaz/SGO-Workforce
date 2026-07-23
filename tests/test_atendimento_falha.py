"""Testes do Incremento 6: atendimento de falha.

Cobre a regra inegociavel de docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md
secao 3.5: um atendimento de falha nao pode ser encerrado sem nota, ativo,
sintoma, causa, acao, observacao tecnica e horario final.
"""

from datetime import datetime, timedelta

import pytest

from workforce_core import MotorJornada, calculo
from workforce_core.exceptions import (
    AtendimentoFalhaCamposObrigatoriosError,
    AtendimentoFalhaNaoAtivoError,
)


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def _motor_com_atendimento_ativo():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))
    return motor


def test_atendimento_falha_completo_encerra_normalmente():
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(
        nota="12345",
        ativo="AT-001",
        sintoma="33 - CIRCUITO DE VIA COM OCUP. INDEVIDA",
        causa="Falha de contato",
        acao="Substituicao de rele",
        observacao="Testado apos a troca, normalizado.",
    )
    atividade = motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    assert atividade.estado.value == "ENCERRADA"
    assert atividade.dados_falha.nota == "12345"
    assert calculo.duracao_atividade_bruta(atividade) == timedelta(minutes=50)


def test_bloqueia_encerramento_sem_nenhum_campo():
    motor = _motor_com_atendimento_ativo()
    with pytest.raises(AtendimentoFalhaCamposObrigatoriosError) as excinfo:
        motor.encerrar_atividade(_dt(9, 0))
    for campo in ("nota", "ativo", "sintoma", "causa", "acao", "observacao"):
        assert campo in str(excinfo.value)


def test_bloqueia_encerramento_com_campos_parciais():
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(nota="12345", ativo="AT-001", sintoma="Falha X")
    # causa, acao e observacao ainda faltam.
    with pytest.raises(AtendimentoFalhaCamposObrigatoriosError) as excinfo:
        motor.encerrar_atividade(_dt(9, 0))
    mensagem = str(excinfo.value)
    assert "causa" in mensagem
    assert "acao" in mensagem
    assert "observacao" in mensagem
    assert "nota" not in mensagem


def test_registro_progressivo_de_campos():
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S")
    motor.registrar_dados_falha(causa="C", acao="Ac", observacao="Obs")

    dados = motor.jornada.atividades[0].dados_falha
    assert (dados.nota, dados.ativo, dados.sintoma) == ("1", "A", "S")
    assert (dados.causa, dados.acao, dados.observacao) == ("C", "Ac", "Obs")

    # Nao deve fazer nada com um segundo registro passando None, so
    # sobrescrever o que for explicitamente informado.
    motor.registrar_dados_falha(nota="1-revisado")
    assert motor.jornada.atividades[0].dados_falha.ativo == "A"
    assert motor.jornada.atividades[0].dados_falha.nota == "1-revisado"


def test_registrar_dados_falha_sem_atendimento_ativo():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    with pytest.raises(AtendimentoFalhaNaoAtivoError):
        motor.registrar_dados_falha(nota="1")


def test_registrar_dados_falha_em_atividade_comum_nao_e_permitido():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))  # atividade comum, sem dados_falha
    with pytest.raises(AtendimentoFalhaNaoAtivoError):
        motor.registrar_dados_falha(nota="1")


def test_atividade_comum_encerra_sem_exigir_campos_de_falha():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    atividade = motor.encerrar_atividade(_dt(9, 0))
    assert atividade.dados_falha is None


def test_atendimento_falha_pode_ter_pausa_normalmente():
    motor = _motor_com_atendimento_ativo()
    motor.iniciar_pausa(_dt(8, 30), "PAUSA_TESTE")
    motor.finalizar_pausa(_dt(8, 40))
    motor.registrar_dados_falha(
        nota="1", ativo="A", sintoma="S", causa="C", acao="Ac", observacao="Obs"
    )
    atividade = motor.encerrar_atividade(_dt(9, 0))

    assert calculo.duracao_pausas_atividade(atividade) == timedelta(minutes=10)
    assert calculo.duracao_atividade_liquida(atividade) == timedelta(minutes=40)
