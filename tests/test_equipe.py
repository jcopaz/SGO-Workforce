"""Testes da aba Equipe (2026-08-07, pedido do responsavel pelo produto):
associacao de membros de equipe (matricula, texto livre) a uma Atividade.

Mesmo espirito de tests/test_ordem_servico.py (ADR-0025): lista anexada a
Atividade, exclusao individual soft-delete (nunca remove da lista). Unica
diferenca de regra de negocio: Equipe TAMBEM e permitida em atendimento de
falha (quem estava presente independe do tipo de atividade) - OS nao e.
Nao afeta calculo de HH nem o dono da Jornada (regra de ouro 4).
"""

from datetime import datetime

import pytest

from workforce_core import MotorJornada
from workforce_core.exceptions import (
    AtividadeNaoAtivaError,
    MembroEquipeMatriculaObrigatoriaError,
    MembroEquipeNaoEncontradoError,
)
from workforce_storage import RepositorioJornadaArquivo
from workforce_storage.serializacao import atividade_de_dict, atividade_para_dict


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


# ----------------------------------------------------------------------
# adicionar_membro_equipe
# ----------------------------------------------------------------------
def test_adicionar_membro_equipe_associa_a_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    membro = motor.adicionar_membro_equipe(_dt(8, 15), "54321")

    assert membro.matricula == "54321"
    assert membro.excluida is False
    assert motor.jornada.atividades[0].equipe == [membro]


def test_adicionar_multiplos_membros_de_equipe():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    motor.adicionar_membro_equipe(_dt(8, 15), "54321")
    motor.adicionar_membro_equipe(_dt(8, 20), "67890")

    matriculas = [m.matricula for m in motor.jornada.atividades[0].equipe]
    assert matriculas == ["54321", "67890"]


def test_adicionar_membro_equipe_matricula_obrigatoria():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(MembroEquipeMatriculaObrigatoriaError):
        motor.adicionar_membro_equipe(_dt(8, 15), "")


def test_adicionar_membro_equipe_sem_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(AtividadeNaoAtivaError):
        motor.adicionar_membro_equipe(_dt(8, 15), "54321")


def test_adicionar_membro_equipe_e_permitido_em_atendimento_de_falha():
    # Diferente de OrdemServico (OrdemServicoExigeAtividadeSemFalhaError):
    # quem estava presente na equipe independe do tipo de atividade.
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))

    membro = motor.adicionar_membro_equipe(_dt(8, 15), "54321")

    assert membro.matricula == "54321"


# ----------------------------------------------------------------------
# excluir_membro_equipe (soft-delete)
# ----------------------------------------------------------------------
def test_excluir_membro_equipe_marca_excluida_sem_remover_da_lista():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    membro = motor.adicionar_membro_equipe(_dt(8, 15), "54321")

    motor.excluir_membro_equipe(membro.id)

    atividade = motor.jornada.atividades[0]
    assert len(atividade.equipe) == 1
    assert atividade.equipe[0].excluida is True


def test_excluir_membro_equipe_e_idempotente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    membro = motor.adicionar_membro_equipe(_dt(8, 15), "54321")

    motor.excluir_membro_equipe(membro.id)
    motor.excluir_membro_equipe(membro.id)  # reenviar a mesma exclusao nao quebra

    assert motor.jornada.atividades[0].equipe[0].excluida is True


def test_excluir_membro_equipe_inexistente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(MembroEquipeNaoEncontradoError):
        motor.excluir_membro_equipe("id-que-nao-existe")


def test_excluir_membro_equipe_sem_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(AtividadeNaoAtivaError):
        motor.excluir_membro_equipe("qualquer-id")


# ----------------------------------------------------------------------
# Serializacao (round-trip) e persistencia
# ----------------------------------------------------------------------
def test_atividade_para_dict_de_dict_round_trip_com_equipe():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    membro1 = motor.adicionar_membro_equipe(_dt(8, 15), "54321")
    motor.adicionar_membro_equipe(_dt(8, 20), "67890")
    motor.excluir_membro_equipe(membro1.id)
    atividade = motor.encerrar_atividade(_dt(9, 0))

    dados = atividade_para_dict(atividade)
    reconstruida = atividade_de_dict(dados)

    assert reconstruida == atividade
    assert [m.matricula for m in reconstruida.equipe] == ["54321", "67890"]
    assert reconstruida.equipe[0].excluida is True
    assert reconstruida.equipe[1].excluida is False


def test_atividade_de_dict_compatibilidade_retroativa_sem_equipe():
    # Jornada gravada antes da aba Equipe (FORMATO_VERSAO 5) nao tem essa
    # chave - atividade_de_dict precisa reconstruir sem quebrar (mesmo
    # principio de ordens_servico/resultado no ADR-0025).
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    atividade = motor.encerrar_atividade(_dt(9, 0))

    dados = atividade_para_dict(atividade)
    del dados["equipe"]

    reconstruida = atividade_de_dict(dados)
    assert reconstruida.equipe == []


def test_persistencia_round_trip_com_membro_equipe(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.adicionar_membro_equipe(_dt(8, 15), "54321")
    motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)
    recarregada = repo.carregar(motor.jornada.id)

    atividade = recarregada.atividades[0]
    assert atividade.equipe[0].matricula == "54321"
