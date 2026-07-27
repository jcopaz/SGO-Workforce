"""Testes do ADR-0025: associacao de OS (texto livre) a Atividade comum
(EE17/EE23) e o segundo desfecho de encerramento ("Atividade nao
concluida").

Decisoes de negocio ja tomadas com o responsavel pelo produto (ver
ADR-0023 "Fora de escopo" e ADR-0025): numero de OS em texto livre,
multiplas OS por atividade, exclusao individual das nao concluidas
(soft-delete, nunca remove da lista), dois desfechos de encerramento
("Concluir atividade" -> EE17/CONCLUIDA, "Atividade nao concluida" ->
EE23/NAO_CONCLUIDA), sem transferencia entre colaboradores.
"""

from datetime import datetime

import pytest

from workforce_core import MotorJornada
from workforce_core.catalogo import Categoria
from workforce_core.consolidacao import linhas_eventos_classificadas, resumo_por_categoria
from workforce_core.enums import ResultadoAtividade
from workforce_core.exceptions import (
    AtividadeNaoAtivaError,
    AtividadeNaoConcluidaExigeSemDadosFalhaError,
    OrdemServicoExigeAtividadeSemFalhaError,
    OrdemServicoNaoEncontradaError,
    OrdemServicoNumeroObrigatorioError,
)
from workforce_storage import RepositorioJornadaArquivo
from workforce_storage.serializacao import atividade_de_dict, atividade_para_dict


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def _catalogo_vazio():
    from workforce_core.catalogo import CatalogoMotivos

    return CatalogoMotivos()


# ----------------------------------------------------------------------
# adicionar_ordem_servico
# ----------------------------------------------------------------------
def test_adicionar_ordem_servico_associa_a_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    ordem = motor.adicionar_ordem_servico(_dt(8, 15), "12345678")

    assert ordem.numero == "12345678"
    assert ordem.excluida is False
    assert motor.jornada.atividades[0].ordens_servico == [ordem]


def test_adicionar_multiplas_ordens_de_servico():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    motor.adicionar_ordem_servico(_dt(8, 15), "111")
    motor.adicionar_ordem_servico(_dt(8, 20), "222")

    numeros = [o.numero for o in motor.jornada.atividades[0].ordens_servico]
    assert numeros == ["111", "222"]


def test_adicionar_ordem_servico_numero_obrigatorio():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(OrdemServicoNumeroObrigatorioError):
        motor.adicionar_ordem_servico(_dt(8, 15), "")


def test_adicionar_ordem_servico_sem_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(AtividadeNaoAtivaError):
        motor.adicionar_ordem_servico(_dt(8, 15), "111")


def test_adicionar_ordem_servico_em_atendimento_de_falha_nao_e_permitido():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))

    with pytest.raises(OrdemServicoExigeAtividadeSemFalhaError):
        motor.adicionar_ordem_servico(_dt(8, 15), "111")


# ----------------------------------------------------------------------
# excluir_ordem_servico (soft-delete)
# ----------------------------------------------------------------------
def test_excluir_ordem_servico_marca_excluida_sem_remover_da_lista():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    ordem = motor.adicionar_ordem_servico(_dt(8, 15), "111")

    motor.excluir_ordem_servico(ordem.id)

    atividade = motor.jornada.atividades[0]
    assert len(atividade.ordens_servico) == 1
    assert atividade.ordens_servico[0].excluida is True


def test_excluir_ordem_servico_e_idempotente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    ordem = motor.adicionar_ordem_servico(_dt(8, 15), "111")

    motor.excluir_ordem_servico(ordem.id)
    motor.excluir_ordem_servico(ordem.id)  # reenviar a mesma exclusao nao quebra

    assert motor.jornada.atividades[0].ordens_servico[0].excluida is True


def test_excluir_ordem_servico_inexistente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(OrdemServicoNaoEncontradaError):
        motor.excluir_ordem_servico("id-que-nao-existe")


def test_excluir_ordem_servico_sem_atividade_ativa():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    with pytest.raises(AtividadeNaoAtivaError):
        motor.excluir_ordem_servico("qualquer-id")


# ----------------------------------------------------------------------
# encerrar_atividade / encerrar_atividade_nao_concluida (resultado)
# ----------------------------------------------------------------------
def test_encerrar_atividade_grava_resultado_concluida():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.adicionar_ordem_servico(_dt(8, 15), "111")

    atividade = motor.encerrar_atividade(_dt(9, 0))

    assert atividade.resultado == ResultadoAtividade.CONCLUIDA
    assert atividade.ordens_servico[0].numero == "111"


def test_encerrar_atividade_nao_concluida_grava_resultado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    ordem1 = motor.adicionar_ordem_servico(_dt(8, 15), "111")
    motor.adicionar_ordem_servico(_dt(8, 20), "222")
    motor.excluir_ordem_servico(ordem1.id)  # "conclusao parcial de OS" (ADR-0023)

    atividade = motor.encerrar_atividade_nao_concluida(_dt(9, 0))

    assert atividade.resultado == ResultadoAtividade.NAO_CONCLUIDA
    assert len(atividade.ordens_servico) == 2  # nenhuma foi removida da lista
    assert atividade.ordens_servico[0].excluida is True
    assert atividade.ordens_servico[1].excluida is False


def test_encerrar_atividade_nao_concluida_em_atendimento_de_falha_nao_e_permitido():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))

    with pytest.raises(AtividadeNaoConcluidaExigeSemDadosFalhaError):
        motor.encerrar_atividade_nao_concluida(_dt(9, 0))


def test_atividade_encerrada_sem_resultado_explicito_e_none():
    # Espelha o comportamento anterior ao ADR-0025 (jornadas ja
    # sincronizadas): resultado so existe explicitamente a partir daqui,
    # mas o campo em si aceita None sem quebrar encerrar_atividade.
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    atividade = motor.encerrar_atividade(_dt(9, 0))
    assert atividade.resultado == ResultadoAtividade.CONCLUIDA


# ----------------------------------------------------------------------
# Consolidacao: EE23 (ATIVIDADE_PLANEJADA_NAO_CONCLUIDA) via resultado
# ----------------------------------------------------------------------
def test_consolidacao_classifica_atividade_nao_concluida():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.encerrar_atividade_nao_concluida(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    resumo = resumo_por_categoria(motor.jornada, _catalogo_vazio())
    assert Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA in resumo
    assert Categoria.ATIVIDADE_PLANEJADA not in resumo

    linhas = linhas_eventos_classificadas([motor.jornada], _catalogo_vazio())
    linha_atividade = [l for l in linhas if l.tipo == "ATIVIDADE"][0]
    assert linha_atividade.categoria == Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA


def test_consolidacao_classifica_atividade_concluida_normalmente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    resumo = resumo_por_categoria(motor.jornada, _catalogo_vazio())
    assert Categoria.ATIVIDADE_PLANEJADA in resumo
    assert Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA not in resumo


def test_consolidacao_dados_falha_tem_precedencia_sobre_resultado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs")
    motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    resumo = resumo_por_categoria(motor.jornada, _catalogo_vazio())
    assert Categoria.ATENDIMENTO_FALHA in resumo
    assert Categoria.ATIVIDADE_PLANEJADA not in resumo


# ----------------------------------------------------------------------
# Serializacao (round-trip) e persistencia
# ----------------------------------------------------------------------
def test_atividade_para_dict_de_dict_round_trip_com_ordens_servico():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    ordem1 = motor.adicionar_ordem_servico(_dt(8, 15), "111")
    motor.adicionar_ordem_servico(_dt(8, 20), "222")
    motor.excluir_ordem_servico(ordem1.id)
    atividade = motor.encerrar_atividade_nao_concluida(_dt(9, 0))

    dados = atividade_para_dict(atividade)
    reconstruida = atividade_de_dict(dados)

    assert reconstruida == atividade
    assert reconstruida.resultado == ResultadoAtividade.NAO_CONCLUIDA
    assert [o.numero for o in reconstruida.ordens_servico] == ["111", "222"]
    assert reconstruida.ordens_servico[0].excluida is True


def test_atividade_de_dict_compatibilidade_retroativa_sem_ordens_servico_nem_resultado():
    # Jornada gravada antes do ADR-0025 (FORMATO_VERSAO 4) nao tem essas
    # chaves - atividade_de_dict precisa reconstruir sem quebrar.
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    atividade = motor.encerrar_atividade(_dt(9, 0))

    dados = atividade_para_dict(atividade)
    del dados["ordens_servico"]
    del dados["resultado"]

    reconstruida = atividade_de_dict(dados)
    assert reconstruida.ordens_servico == []
    assert reconstruida.resultado is None


def test_persistencia_round_trip_com_ordem_servico(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.adicionar_ordem_servico(_dt(8, 15), "111")
    motor.encerrar_atividade_nao_concluida(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)
    recarregada = repo.carregar(motor.jornada.id)

    atividade = recarregada.atividades[0]
    assert atividade.resultado == ResultadoAtividade.NAO_CONCLUIDA
    assert atividade.ordens_servico[0].numero == "111"
