"""Testes do Incremento 5: catalogo e eventos secundarios
(deslocamento, espera, apoio).

Regras aplicadas (docs/07_MOTOR_EVENTOS_E_HH.md + ADR-0005):
- deslocamento/espera/apoio sao mutuamente exclusivos com a atividade
  principal ("apenas um evento principal ativo");
- apenas um evento secundario ativo por vez;
- tipo e motivo sao obrigatorios;
- a duracao entra no tempo classificado da jornada;
- classificacao_hh de qualquer entrada de catalogo comeca como NAO_DEFINIDO.
"""

from datetime import datetime, timedelta

import pytest

from workforce_core import EstadoEventoSecundario, MotorJornada, TipoEventoSecundario, calculo
from workforce_core.catalogo import CatalogoMotivos, Categoria, ClassificacaoHH, EntradaCatalogo, catalogo_padrao
from workforce_core.exceptions import (
    AtividadeExigeNenhumEventoSecundarioAtivoError,
    EstadoInconsistenteError,
    EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError,
    EventoSecundarioJaAtivoError,
    EventoSecundarioMotivoObrigatorioError,
    EventoSecundarioNaoAtivoError,
    EventoSecundarioTipoObrigatorioError,
    JornadaComEventoSecundarioAbertoError,
    TimestampInvalidoError,
)
from workforce_storage import RepositorioJornadaArquivo


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def test_iniciar_e_encerrar_deslocamento():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    evento = motor.iniciar_evento_secundario(_dt(8, 10), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")
    assert evento.estado == EstadoEventoSecundario.ATIVA

    motor.encerrar_evento_secundario(_dt(8, 40))
    assert evento.estado == EstadoEventoSecundario.ENCERRADA
    assert calculo.duracao_evento_secundario(evento) == timedelta(minutes=30)


def test_iniciar_e_encerrar_espera_e_apoio():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    espera = motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.ESPERA, "ESPERA_TESTE")
    motor.encerrar_evento_secundario(_dt(8, 15))

    apoio = motor.iniciar_evento_secundario(_dt(8, 15), TipoEventoSecundario.APOIO, "APOIO_TESTE")
    motor.encerrar_evento_secundario(_dt(8, 45))

    assert calculo.duracao_evento_secundario(espera) == timedelta(minutes=15)
    assert calculo.duracao_evento_secundario(apoio) == timedelta(minutes=30)


def test_tipo_obrigatorio():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    with pytest.raises(EventoSecundarioTipoObrigatorioError):
        motor.iniciar_evento_secundario(_dt(8, 0), None, "DESLOCAMENTO_TESTE")


def test_motivo_obrigatorio():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    with pytest.raises(EventoSecundarioMotivoObrigatorioError):
        motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "")


def test_bloqueia_segundo_evento_secundario_simultaneo():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")

    with pytest.raises(EventoSecundarioJaAtivoError):
        motor.iniciar_evento_secundario(_dt(8, 5), TipoEventoSecundario.APOIO, "APOIO_TESTE")


def test_encerrar_evento_secundario_sem_nenhum_ativo():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    with pytest.raises(EventoSecundarioNaoAtivoError):
        motor.encerrar_evento_secundario(_dt(8, 10))


def test_mutuamente_exclusivo_com_atividade_principal_evento_apos_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    with pytest.raises(EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError):
        motor.iniciar_evento_secundario(_dt(8, 20), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")


def test_mutuamente_exclusivo_com_atividade_principal_atividade_apos_evento():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.ESPERA, "ESPERA_TESTE")

    with pytest.raises(AtividadeExigeNenhumEventoSecundarioAtivoError):
        motor.iniciar_atividade(_dt(8, 20))


def test_bloqueia_encerrar_jornada_com_evento_secundario_aberto():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.APOIO, "APOIO_TESTE")

    with pytest.raises(JornadaComEventoSecundarioAbertoError):
        motor.encerrar_jornada(_dt(9, 0))


def test_timestamp_invalido_no_evento_secundario():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 30), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")
    with pytest.raises(TimestampInvalidoError):
        motor.encerrar_evento_secundario(_dt(8, 0))


def test_fluxo_com_evento_secundario_entra_no_tempo_classificado():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")
    motor.encerrar_evento_secundario(_dt(8, 30))

    motor.iniciar_atividade(_dt(8, 30))
    motor.encerrar_atividade(_dt(10, 30))

    motor.encerrar_jornada(_dt(10, 30))

    resumo = calculo.resumo_jornada(motor.jornada)
    assert resumo["jornada_bruta"] == timedelta(hours=2, minutes=30)
    assert resumo["tempo_classificado"] == timedelta(hours=2, minutes=30)
    assert resumo["tempo_nao_classificado"] == timedelta()
    assert len(resumo["eventos_secundarios"]) == 1
    assert resumo["eventos_secundarios"][0]["tipo"] == TipoEventoSecundario.DESLOCAMENTO
    assert resumo["eventos_secundarios"][0]["duracao"] == timedelta(minutes=30)


def test_recuperacao_de_estado_com_evento_secundario_ativo(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.ESPERA, "ESPERA_TESTE")

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    motor_recuperado = repo.carregar_motor(motor.jornada.id)
    motor_recuperado.encerrar_evento_secundario(_dt(8, 20))
    motor_recuperado.iniciar_atividade(_dt(8, 20))
    motor_recuperado.encerrar_atividade(_dt(9, 0))
    motor_recuperado.encerrar_jornada(_dt(9, 0))

    assert motor_recuperado.jornada.eventos_secundarios[0].fim == _dt(8, 20)


def test_estado_inconsistente_evento_e_atividade_ativos_juntos():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    # Adultera diretamente a entidade para simular corrupcao/adulteracao,
    # ja que o motor nunca permite chegar a este estado por transicoes normais.
    from workforce_core.entities import EventoSecundario

    motor.jornada.eventos_secundarios.append(
        EventoSecundario(
            tipo=TipoEventoSecundario.APOIO,
            motivo="APOIO_TESTE",
            inicio=_dt(8, 0),
            estado=EstadoEventoSecundario.ATIVA,
        )
    )

    with pytest.raises(EstadoInconsistenteError):
        MotorJornada.a_partir_de(motor.jornada)


# ----------------------------------------------------------------------
# Catalogo
# ----------------------------------------------------------------------
def test_catalogo_registrar_e_obter():
    catalogo = CatalogoMotivos()
    catalogo.registrar(
        EntradaCatalogo(codigo="X", descricao="Exemplo", categoria=Categoria.APOIO_OPERACIONAL)
    )
    entrada = catalogo.obter("X")
    assert entrada is not None
    assert entrada.categoria == Categoria.APOIO_OPERACIONAL
    assert entrada.classificacao_hh == ClassificacaoHH.NAO_DEFINIDO


def test_catalogo_obter_inexistente_retorna_none():
    catalogo = CatalogoMotivos()
    assert catalogo.obter("NAO_EXISTE") is None


def test_round_trip_persistencia_com_evento_secundario_encerrado(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")
    motor.encerrar_evento_secundario(_dt(8, 30))
    motor.iniciar_atividade(_dt(8, 30))
    motor.encerrar_atividade(_dt(10, 0))
    motor.encerrar_jornada(_dt(10, 0))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)
    recarregada = repo.carregar(motor.jornada.id)

    assert len(recarregada.eventos_secundarios) == 1
    evento = recarregada.eventos_secundarios[0]
    assert evento.tipo == TipoEventoSecundario.DESLOCAMENTO
    assert evento.motivo == "DESLOCAMENTO_TESTE"
    assert calculo.duracao_evento_secundario(evento) == timedelta(minutes=30)


def test_catalogo_padrao_contem_motivos_de_teste_nao_definidos():
    catalogo = catalogo_padrao()
    codigos = {e.codigo for e in catalogo.todos()}
    assert {"PAUSA_TESTE", "DESLOCAMENTO_TESTE", "ESPERA_TESTE", "APOIO_TESTE"} <= codigos
    for entrada in catalogo.todos():
        assert entrada.classificacao_hh == ClassificacaoHH.NAO_DEFINIDO
