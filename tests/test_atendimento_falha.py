"""Testes do Incremento 6: atendimento de falha.

Regra atual (revista no ADR-0021 a pedido do responsavel pelo produto,
2026-07-27): um atendimento de falha nao pode ser encerrado sem nota,
ativo, sintoma, objeto (componente causador) e observacao ("Observacoes/
Causa" na interface de campo) e horario final. `causa`/`acao` (regra
original de docs/27 secao 3.5) continuam aceitos por
compatibilidade com registros antigos, mas nao sao mais exigidos.
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
        objeto="FUSÍVEL",
        observacao="Testado apos a troca, normalizado.",
    )
    atividade = motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    assert atividade.estado.value == "ENCERRADA"
    assert atividade.dados_falha.nota == "12345"
    assert atividade.dados_falha.objeto == "FUSÍVEL"
    assert calculo.duracao_atividade_bruta(atividade) == timedelta(minutes=50)


def test_bloqueia_encerramento_sem_nenhum_campo():
    motor = _motor_com_atendimento_ativo()
    with pytest.raises(AtendimentoFalhaCamposObrigatoriosError) as excinfo:
        motor.encerrar_atividade(_dt(9, 0))
    for campo in ("nota", "ativo", "sintoma", "objeto", "observacao"):
        assert campo in str(excinfo.value)


def test_bloqueia_encerramento_com_campos_parciais():
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(nota="12345", ativo="AT-001", sintoma="Falha X")
    # objeto e observacao ainda faltam.
    with pytest.raises(AtendimentoFalhaCamposObrigatoriosError) as excinfo:
        motor.encerrar_atividade(_dt(9, 0))
    mensagem = str(excinfo.value)
    assert "objeto" in mensagem
    assert "observacao" in mensagem
    assert "nota" not in mensagem


def test_causa_e_acao_sao_opcionais_apos_adr_0021():
    # causa/acao continuam existindo no dataclass (compatibilidade), mas
    # nao bloqueiam mais o encerramento - so nota/ativo/sintoma/objeto/
    # observacao sao exigidos.
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(
        nota="12345", ativo="AT-001", sintoma="Falha X", objeto="Componente Y", observacao="Obs"
    )
    atividade = motor.encerrar_atividade(_dt(9, 0))
    assert atividade.dados_falha.causa is None
    assert atividade.dados_falha.acao is None


def test_registro_progressivo_de_campos():
    motor = _motor_com_atendimento_ativo()
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S", objeto="O")
    motor.registrar_dados_falha(observacao="Obs")

    dados = motor.jornada.atividades[0].dados_falha
    assert (dados.nota, dados.ativo, dados.sintoma, dados.objeto) == ("1", "A", "S", "O")
    assert dados.observacao == "Obs"

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
        nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs"
    )
    atividade = motor.encerrar_atividade(_dt(9, 0))

    assert calculo.duracao_pausas_atividade(atividade) == timedelta(minutes=10)
    assert calculo.duracao_atividade_liquida(atividade) == timedelta(minutes=40)
