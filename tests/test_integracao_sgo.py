"""Testes do Incremento 13: contrato de integracao futura com o SGO.

Nao testa integracao real (nao existe) - testa que a FORMA do contrato
(chaves, Protocol, identidade de ReferenciaOS) esta correta conforme
docs/16_INTEGRACAO_FUTURA_SGO.md e docs/27 secao 10.
"""

from datetime import datetime

from workforce_core import DadosFalha, MotorJornada
from workforce_core.integracao_sgo import (
    Ativo,
    ContratoSGO,
    ContratoSGOEmMemoria,
    Coordenacao,
    Especialidade,
    OsProgramada,
    Patio,
    ReferenciaOS,
    UsuarioAutorizado,
)
from workforce_storage.serializacao import dados_falha_de_dict, dados_falha_para_dict


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


# ----------------------------------------------------------------------
# ReferenciaOS: identidade nunca e so o numero
# ----------------------------------------------------------------------
def test_referencia_os_mesmo_numero_ciclos_diferentes_nao_sao_iguais():
    os_ciclo_1 = ReferenciaOS(numero="12345", ciclo_ou_plano="2026-C1")
    os_ciclo_2 = ReferenciaOS(numero="12345", ciclo_ou_plano="2026-C2")

    assert os_ciclo_1 != os_ciclo_2
    assert hash(os_ciclo_1) != hash(os_ciclo_2)


def test_referencia_os_mesma_os_data_importacao_diferente_sao_iguais():
    referencia_1 = ReferenciaOS(numero="12345", ciclo_ou_plano="2026-C1", data_importacao=_dt(8, 0))
    referencia_2 = ReferenciaOS(numero="12345", ciclo_ou_plano="2026-C1", data_importacao=_dt(9, 0))

    assert referencia_1 == referencia_2
    assert hash(referencia_1) == hash(referencia_2)


def test_referencia_os_usavel_como_chave_de_dict():
    referencia = ReferenciaOS(numero="1", ciclo_ou_plano="C1")
    mapa = {referencia: "valor"}
    assert mapa[ReferenciaOS(numero="1", ciclo_ou_plano="C1")] == "valor"


# ----------------------------------------------------------------------
# DadosFalha.os_referencia (campo recomendado, Incremento 6 + 13)
# ----------------------------------------------------------------------
def test_atendimento_falha_pode_referenciar_os_opcionalmente():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 10))
    motor.registrar_dados_falha(
        nota="1", ativo="A", sintoma="S", causa="C", acao="Ac", observacao="Obs"
    )
    atividade = motor.jornada.atividades[0]
    atividade.dados_falha.os_referencia = ReferenciaOS(numero="999", ciclo_ou_plano="2026-C3")
    atividade_encerrada = motor.encerrar_atividade(_dt(9, 0))

    assert atividade_encerrada.dados_falha.os_referencia.numero == "999"


def test_dados_falha_sem_os_referencia_continua_funcionando():
    dados = DadosFalha(nota="1", ativo="A", sintoma="S", causa="C", acao="Ac", observacao="Obs")
    assert dados.os_referencia is None


def test_round_trip_serializacao_com_os_referencia():
    dados = DadosFalha(
        nota="1",
        ativo="A",
        sintoma="S",
        causa="C",
        acao="Ac",
        observacao="Obs",
        os_referencia=ReferenciaOS(numero="42", ciclo_ou_plano="2026-C1", data_importacao=_dt(8, 0)),
    )

    recarregado = dados_falha_de_dict(dados_falha_para_dict(dados))

    assert recarregado.os_referencia == ReferenciaOS(numero="42", ciclo_ou_plano="2026-C1")


def test_round_trip_serializacao_sem_os_referencia_e_retrocompativel():
    # Simula um arquivo v3 (antes do Incremento 13), sem a chave os_referencia.
    dados_v3 = {
        "nota": "1",
        "ativo": "A",
        "sintoma": "S",
        "causa": "C",
        "acao": "Ac",
        "observacao": "Obs",
    }
    recarregado = dados_falha_de_dict(dados_v3)
    assert recarregado.os_referencia is None


# ----------------------------------------------------------------------
# Contrato falso (nunca uma integracao real)
# ----------------------------------------------------------------------
def test_contrato_sgo_em_memoria_atende_o_protocol():
    contrato = ContratoSGOEmMemoria()
    assert isinstance(contrato, ContratoSGO)


def test_contrato_sgo_em_memoria_carrega_e_lista():
    contrato = ContratoSGOEmMemoria(versao_contrato="1.2.3")
    contrato.carregar_usuarios([UsuarioAutorizado(matricula="1", nome="Fulano", coordenacao_codigo="C1")])
    contrato.carregar_coordenacoes([Coordenacao(codigo="C1", descricao="Coordenacao 1")])
    contrato.carregar_especialidades([Especialidade(codigo="E1", descricao="Especialidade 1")])
    contrato.carregar_patios([Patio(codigo="P1", descricao="Patio 1")])
    contrato.carregar_ativos([Ativo(identificador="AT-1", descricao="Ativo 1", patio_codigo="P1")])
    contrato.carregar_os_programadas(
        [
            OsProgramada(
                referencia=ReferenciaOS(numero="1", ciclo_ou_plano="2026-C1"),
                descricao="OS de teste",
                ativo_identificador="AT-1",
            )
        ]
    )

    assert contrato.metadados_snapshot().versao_contrato == "1.2.3"
    assert len(contrato.listar_usuarios_autorizados()) == 1
    assert len(contrato.listar_coordenacoes()) == 1
    assert len(contrato.listar_especialidades()) == 1
    assert len(contrato.listar_patios()) == 1
    assert len(contrato.listar_ativos()) == 1
    assert contrato.listar_os_programadas()[0].referencia.numero == "1"


def test_contrato_sgo_em_memoria_vazio_nao_quebra():
    contrato = ContratoSGOEmMemoria()
    assert contrato.listar_usuarios_autorizados() == []
    assert contrato.listar_os_programadas() == []
