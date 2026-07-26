"""Testes do Incremento 8: consolidacao de HH e qualidade dos dados.

Cobre docs/20_TESTES_E_QUALIDADE.md secoes "Reconciliacao" (soma por
categoria, pulsos enviados x recebidos) e "Observabilidade" (jornadas
abertas anormais, taxa de GPS valido).
"""

from datetime import datetime, timedelta
from uuid import uuid4

from workforce_core import MotorJornada, PulsoGps, QualidadePulso, TipoEventoSecundario, consolidacao
from workforce_core.catalogo import Categoria, catalogo_padrao


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def _jornada_completa(matricula="12345"):
    motor = MotorJornada(matricula)
    motor.iniciar_jornada(_dt(8, 0))

    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE")
    motor.encerrar_evento_secundario(_dt(8, 30))

    motor.iniciar_atividade(_dt(8, 30))
    motor.iniciar_pausa(_dt(9, 0), "PAUSA_TESTE")
    motor.finalizar_pausa(_dt(9, 10))
    motor.encerrar_atividade(_dt(11, 30))

    motor.iniciar_atendimento_falha(_dt(11, 30))
    motor.registrar_dados_falha(
        nota="1", ativo="A", sintoma="S", causa="C", acao="Ac", observacao="Obs"
    )
    motor.encerrar_atividade(_dt(12, 0))

    motor.encerrar_jornada(_dt(12, 0))
    return motor.jornada


# ----------------------------------------------------------------------
# Soma por categoria
# ----------------------------------------------------------------------
def test_resumo_por_categoria_classifica_atividade_e_atendimento_falha():
    jornada = _jornada_completa()
    catalogo = catalogo_padrao()

    resumo = consolidacao.resumo_por_categoria(jornada, catalogo)

    assert resumo[Categoria.ATIVIDADE_PLANEJADA] == timedelta(hours=2, minutes=50)
    assert resumo[Categoria.ATENDIMENTO_FALHA] == timedelta(minutes=30)
    assert resumo[Categoria.DESLOCAMENTO_RODOVIARIO] == timedelta(minutes=30)


def test_resumo_por_categoria_pausa_sem_categoria_vai_para_none():
    jornada = _jornada_completa()
    catalogo = catalogo_padrao()

    resumo = consolidacao.resumo_por_categoria(jornada, catalogo)

    # PAUSA_TESTE tem categoria=None no catalogo padrao (ver ADR-0005).
    assert resumo[None] == timedelta(minutes=10)


def test_resumo_por_categoria_motivo_fora_do_catalogo_tambem_vai_para_none():
    from workforce_core.catalogo import CatalogoMotivos

    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    motor.iniciar_pausa(_dt(9, 0), "MOTIVO_INEXISTENTE_NO_CATALOGO")
    motor.finalizar_pausa(_dt(9, 5))
    motor.encerrar_atividade(_dt(10, 0))
    motor.encerrar_jornada(_dt(10, 0))

    resumo = consolidacao.resumo_por_categoria(motor.jornada, CatalogoMotivos())
    assert resumo[None] == timedelta(minutes=5)


def test_resumo_por_categoria_ignora_atividade_e_pausa_em_andamento():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    # atividade permanece aberta - nao deve ser somada.

    resumo = consolidacao.resumo_por_categoria(motor.jornada, catalogo_padrao())
    assert resumo == {}


# ----------------------------------------------------------------------
# Linhas de evento classificadas (base dos filtros do painel)
# ----------------------------------------------------------------------
def test_linhas_eventos_classificadas_uma_linha_por_evento_encerrado():
    jornada = _jornada_completa("12345")
    catalogo = catalogo_padrao()

    linhas = consolidacao.linhas_eventos_classificadas([jornada], catalogo)

    # 1 evento secundario + 1 atividade + 1 pausa + 1 atendimento de falha.
    assert len(linhas) == 4
    assert all(linha.colaborador_matricula == "12345" for linha in linhas)
    assert all(linha.data == _dt(8, 0).date() for linha in linhas)

    por_tipo = {linha.tipo: linha for linha in linhas if linha.tipo != "ATIVIDADE"}
    assert por_tipo["EVENTO_SECUNDARIO"].categoria == Categoria.DESLOCAMENTO_RODOVIARIO
    assert por_tipo["EVENTO_SECUNDARIO"].motivo == "DESLOCAMENTO_TESTE"
    assert por_tipo["EVENTO_SECUNDARIO"].duracao == timedelta(minutes=30)

    assert por_tipo["PAUSA"].categoria is None  # PAUSA_TESTE sem categoria no catalogo padrao
    assert por_tipo["PAUSA"].motivo == "PAUSA_TESTE"
    assert por_tipo["PAUSA"].duracao == timedelta(minutes=10)

    atividades = [linha for linha in linhas if linha.tipo == "ATIVIDADE"]
    categorias_atividade = {linha.categoria for linha in atividades}
    assert categorias_atividade == {Categoria.ATIVIDADE_PLANEJADA, Categoria.ATENDIMENTO_FALHA}
    assert all(linha.motivo is None for linha in atividades)


def test_linhas_eventos_classificadas_ignora_jornada_nao_encerrada():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    # jornada permanece aberta.

    linhas = consolidacao.linhas_eventos_classificadas([motor.jornada], catalogo_padrao())
    assert linhas == []


def test_linhas_eventos_classificadas_varias_jornadas_mantem_colaborador_por_linha():
    j1 = _jornada_completa("1")
    j2 = _jornada_completa("2")

    linhas = consolidacao.linhas_eventos_classificadas([j1, j2], catalogo_padrao())

    colaboradores = {linha.colaborador_matricula for linha in linhas}
    assert colaboradores == {"1", "2"}
    assert len(linhas) == 8  # 4 linhas por jornada


# ----------------------------------------------------------------------
# Consolidacao multi-jornada
# ----------------------------------------------------------------------
def test_resumo_consolidado_soma_varias_jornadas():
    j1 = _jornada_completa("1")
    j2 = _jornada_completa("2")
    catalogo = catalogo_padrao()

    resumo = consolidacao.resumo_consolidado([j1, j2], catalogo)

    assert resumo.quantidade_jornadas == 2
    assert resumo.jornada_bruta_total == timedelta(hours=8)
    assert resumo.por_categoria[Categoria.ATENDIMENTO_FALHA] == timedelta(hours=1)
    # tempo classificado + nao classificado deve reconciliar com a bruta.
    assert (
        resumo.tempo_classificado_total + resumo.tempo_nao_classificado_total
        == resumo.jornada_bruta_total
    )


def test_resumo_consolidado_ignora_jornadas_nao_encerradas():
    motor_aberta = MotorJornada("3")
    motor_aberta.iniciar_jornada(_dt(8, 0))

    resumo = consolidacao.resumo_consolidado([motor_aberta.jornada], catalogo_padrao())

    assert resumo.quantidade_jornadas == 0
    assert resumo.jornada_bruta_total == timedelta()


def test_resumo_consolidado_lista_vazia():
    resumo = consolidacao.resumo_consolidado([], catalogo_padrao())
    assert resumo.quantidade_jornadas == 0
    assert resumo.por_categoria == {}


# ----------------------------------------------------------------------
# Qualidade dos dados
# ----------------------------------------------------------------------
def test_jornadas_abertas_ha_muito_tempo():
    motor_normal = MotorJornada("1")
    motor_normal.iniciar_jornada(_dt(8, 0))

    motor_antiga = MotorJornada("2")
    motor_antiga.iniciar_jornada(_dt(0, 0))

    agora = datetime(2026, 1, 1, 20, 0)
    resultado = consolidacao.jornadas_abertas_ha_muito_tempo(
        [motor_normal.jornada, motor_antiga.jornada], agora=agora, limite=timedelta(hours=12)
    )

    assert resultado == [motor_antiga.jornada]


def test_jornadas_abertas_ha_muito_tempo_ignora_encerradas():
    motor = MotorJornada("1")
    motor.iniciar_jornada(_dt(0, 0))
    motor.encerrar_jornada(_dt(1, 0))

    resultado = consolidacao.jornadas_abertas_ha_muito_tempo(
        [motor.jornada], agora=datetime(2026, 1, 2, 0, 0), limite=timedelta(hours=1)
    )
    assert resultado == []


def _pulso(qualidade):
    return PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="1",
        latitude=0.0,
        longitude=0.0,
        precisao_metros=10,
        timestamp_dispositivo=_dt(8, 0),
        qualidade=qualidade,
    )


def test_taxa_qualidade_pulsos():
    pulsos = [
        _pulso(QualidadePulso.OK),
        _pulso(QualidadePulso.OK),
        _pulso(QualidadePulso.OK),
        _pulso(QualidadePulso.SALTO_IMPOSSIVEL),
    ]
    assert consolidacao.taxa_qualidade_pulsos(pulsos) == 0.75


def test_taxa_qualidade_pulsos_ignora_nao_avaliados():
    pulsos = [_pulso(QualidadePulso.OK), _pulso(QualidadePulso.NAO_AVALIADO)]
    assert consolidacao.taxa_qualidade_pulsos(pulsos) == 1.0


def test_taxa_qualidade_pulsos_sem_nenhum_avaliado_retorna_none():
    pulsos = [_pulso(QualidadePulso.NAO_AVALIADO)]
    assert consolidacao.taxa_qualidade_pulsos(pulsos) is None


def test_taxa_qualidade_pulsos_lista_vazia_retorna_none():
    assert consolidacao.taxa_qualidade_pulsos([]) is None


def test_pulsos_pendentes_de_sincronizacao():
    assert consolidacao.pulsos_pendentes_de_sincronizacao(10, 7) == 3
    assert consolidacao.pulsos_pendentes_de_sincronizacao(5, 5) == 0
    assert consolidacao.pulsos_pendentes_de_sincronizacao(5, 8) == 0  # nunca negativo
