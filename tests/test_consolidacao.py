"""Testes do Incremento 8: consolidacao de HH e qualidade dos dados.

Cobre docs/20_TESTES_E_QUALIDADE.md secoes "Reconciliacao" (soma por
categoria, pulsos enviados x recebidos) e "Observabilidade" (jornadas
abertas anormais, taxa de GPS valido).
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from workforce_core import MotorJornada, PulsoGps, QualidadePulso, TipoEventoSecundario, consolidacao
from workforce_core.catalogo import Categoria, ClassificacaoHH, catalogo_padrao, catalogo_relatorio_1_manutencao


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
        nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs"
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
# Atendimentos de falha (ADR-0029)
# ----------------------------------------------------------------------
def test_linhas_atendimento_falha_uma_linha_por_atendimento_encerrado():
    jornada = _jornada_completa("12345")

    linhas = consolidacao.linhas_atendimento_falha([jornada])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.colaborador_matricula == "12345"
    assert linha.data == _dt(11, 30).date()
    assert linha.duracao == timedelta(minutes=30)  # 11:30 -> 12:00, bruta
    assert linha.nota == "1"
    assert linha.ativo == "A"
    assert linha.sintoma == "S"
    assert linha.objeto == "O"


def test_linhas_atendimento_falha_ignora_atividade_comum():
    motor = MotorJornada("1")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 0))
    motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 0))

    assert consolidacao.linhas_atendimento_falha([motor.jornada]) == []


def test_linhas_atendimento_falha_ignora_atendimento_em_andamento():
    motor = MotorJornada("1")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 0))
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs")
    # atendimento nao encerrado (sem atividade.fim).

    assert consolidacao.linhas_atendimento_falha([motor.jornada]) == []


def test_linhas_atendimento_falha_inclui_jornada_ainda_aberta():
    # Diferente de linhas_eventos_classificadas: um atendimento de falha
    # ja concluido deve aparecer mesmo que o colaborador continue
    # trabalhando (jornada nao encerrada) - decisao deliberada do ADR-0029.
    motor = MotorJornada("1")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atendimento_falha(_dt(8, 0))
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs")
    motor.encerrar_atividade(_dt(9, 0))
    # jornada permanece aberta.

    linhas = consolidacao.linhas_atendimento_falha([motor.jornada])
    assert len(linhas) == 1
    assert linhas[0].duracao == timedelta(hours=1)


def test_resumo_atendimentos_falha_calcula_media_e_maior():
    linhas = [
        consolidacao.LinhaAtendimentoFalha(
            colaborador_matricula="1",
            data=_dt(8, 0).date(),
            inicio=_dt(8, 0),
            fim=_dt(9, 0),
            duracao=timedelta(hours=1),
            nota="1",
            ativo="A",
            sintoma="Sintoma A",
            objeto="O",
        ),
        consolidacao.LinhaAtendimentoFalha(
            colaborador_matricula="2",
            data=_dt(8, 0).date(),
            inicio=_dt(8, 0),
            fim=_dt(11, 0),
            duracao=timedelta(hours=3),
            nota="2",
            ativo="B",
            sintoma="Sintoma B",
            objeto="O",
        ),
    ]

    resumo = consolidacao.resumo_atendimentos_falha(linhas)

    assert resumo.quantidade == 2
    assert resumo.duracao_total == timedelta(hours=4)
    assert resumo.duracao_media == timedelta(hours=2)
    assert resumo.maior_duracao == timedelta(hours=3)


def test_resumo_atendimentos_falha_lista_vazia_nunca_quebra():
    resumo = consolidacao.resumo_atendimentos_falha([])
    assert resumo.quantidade == 0
    assert resumo.duracao_total == timedelta()
    assert resumo.duracao_media is None
    assert resumo.maior_duracao is None


def test_contagem_por_sintoma_agrupa_e_trata_ausente():
    linhas = [
        consolidacao.LinhaAtendimentoFalha("1", _dt(8, 0).date(), _dt(8, 0), _dt(9, 0), timedelta(hours=1), "1", "A", "Sintoma A", "O"),
        consolidacao.LinhaAtendimentoFalha("1", _dt(8, 0).date(), _dt(8, 0), _dt(9, 0), timedelta(hours=1), "2", "A", "Sintoma A", "O"),
        consolidacao.LinhaAtendimentoFalha("1", _dt(8, 0).date(), _dt(8, 0), _dt(9, 0), timedelta(hours=1), "3", "B", None, "O"),
    ]

    contagem = consolidacao.contagem_por_sintoma(linhas)

    assert contagem == {"Sintoma A": 2, "Sem sintoma informado": 1}


def test_contagem_por_ativo_agrupa_e_trata_ausente():
    linhas = [
        consolidacao.LinhaAtendimentoFalha("1", _dt(8, 0).date(), _dt(8, 0), _dt(9, 0), timedelta(hours=1), "1", "ATIVO-1", "S", "O"),
        consolidacao.LinhaAtendimentoFalha("1", _dt(8, 0).date(), _dt(8, 0), _dt(9, 0), timedelta(hours=1), "2", None, "S", "O"),
    ]

    contagem = consolidacao.contagem_por_ativo(linhas)

    assert contagem == {"ATIVO-1": 1, "Sem ativo informado": 1}


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


def test_resumo_consolidado_soma_por_classificacao_hh_varias_jornadas():
    # catalogo_padrao() nao tem entrada com categoria=ATENDIMENTO_FALHA/
    # ATIVIDADE_PLANEJADA, entao as atividades caem em NAO_DEFINIDO - so o
    # deslocamento (DESLOCAMENTO_TESTE) tem classificacao_hh (NAO_DEFINIDO
    # tambem, por ser catalogo de teste) - o que importa aqui e que o
    # agregado bate com a soma das duas jornadas.
    j1 = _jornada_completa("1")
    j2 = _jornada_completa("2")
    catalogo = catalogo_padrao()

    resumo = consolidacao.resumo_consolidado([j1, j2], catalogo)

    assert resumo.por_classificacao_hh[ClassificacaoHH.NAO_DEFINIDO] == resumo.jornada_bruta_total


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
# Indicadores de HH (Utilizacao e Performance) - ADR-0027
# ----------------------------------------------------------------------
def _jornada_relatorio_1(matricula="12345"):
    """Mesma linha do tempo de _jornada_completa, mas com codigos reais do
    Relatorio 1 (EE01-EE23) em vez de motivos *_TESTE, para exercitar
    resumo_por_classificacao_hh com classificacao_hh de verdade (validada
    no ADR-0023) em vez de NAO_DEFINIDO."""
    motor = MotorJornada(matricula)
    motor.iniciar_jornada(_dt(8, 0))

    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "EE12")
    motor.encerrar_evento_secundario(_dt(8, 30))

    motor.iniciar_atividade(_dt(8, 30))
    motor.iniciar_pausa(_dt(9, 0), "EE02")  # Refeicao 1 hora -> NAO_COMPUTAVEL
    motor.finalizar_pausa(_dt(9, 10))
    motor.encerrar_atividade(_dt(11, 30))  # vira EE17 (Manutencao Programada) -> PRODUTIVA

    motor.iniciar_atendimento_falha(_dt(11, 30))
    motor.registrar_dados_falha(nota="1", ativo="A", sintoma="S", objeto="O", observacao="Obs")
    motor.encerrar_atividade(_dt(12, 0))  # EE21 (Atendimento de Falha) -> PRODUTIVA

    motor.encerrar_jornada(_dt(12, 0))
    return motor.jornada


def test_resumo_por_classificacao_hh_usa_classificacao_real_do_catalogo():
    jornada = _jornada_relatorio_1()
    catalogo = catalogo_relatorio_1_manutencao()

    resumo = consolidacao.resumo_por_classificacao_hh(jornada, catalogo)

    # EE17 (2h50, atividade liquida apos descontar a pausa) + EE21 (30min)
    # = 3h20 produtiva (rentavel - ADR-0028 moveu EE12 para
    # PRODUTIVA_NAO_RENTAVEL, EE17/EE21 continuam PRODUTIVA).
    assert resumo[ClassificacaoHH.PRODUTIVA] == timedelta(hours=3, minutes=20)
    # EE12 (30min de deslocamento) -> produtiva nao rentavel.
    assert resumo[ClassificacaoHH.PRODUTIVA_NAO_RENTAVEL] == timedelta(minutes=30)
    # EE02 (10min de pausa) -> nao computavel.
    assert resumo[ClassificacaoHH.NAO_COMPUTAVEL] == timedelta(minutes=10)
    # reconcilia com a jornada bruta inteira (4h, sem nenhuma lacuna nesta linha do tempo).
    assert sum(resumo.values(), timedelta()) == timedelta(hours=4)


def test_resumo_consolidado_por_classificacao_hh_com_catalogo_real():
    jornada = _jornada_relatorio_1()
    resumo = consolidacao.resumo_consolidado([jornada], catalogo_relatorio_1_manutencao())

    assert resumo.por_classificacao_hh[ClassificacaoHH.PRODUTIVA] == timedelta(hours=3, minutes=20)
    assert resumo.por_classificacao_hh[ClassificacaoHH.PRODUTIVA_NAO_RENTAVEL] == timedelta(minutes=30)
    assert resumo.por_classificacao_hh[ClassificacaoHH.NAO_COMPUTAVEL] == timedelta(minutes=10)


def test_utilizacao_hh_formula():
    # Utilizacao HH = Horas Produtivas / Horas Totais.
    assert consolidacao.utilizacao_hh(timedelta(hours=6), timedelta(hours=8)) == 0.75


def test_utilizacao_hh_com_jornada_relatorio_1():
    jornada = _jornada_relatorio_1()
    resumo = consolidacao.resumo_consolidado([jornada], catalogo_relatorio_1_manutencao())
    horas_produtivas = resumo.por_classificacao_hh.get(ClassificacaoHH.PRODUTIVA, timedelta())

    fracao = consolidacao.utilizacao_hh(horas_produtivas, resumo.jornada_bruta_total)

    # 3h20 produtivas (rentaveis) / 4h totais - o deslocamento (EE12) agora
    # e PRODUTIVA_NAO_RENTAVEL e nao entra mais neste numerador (ADR-0028).
    assert fracao == pytest.approx(timedelta(hours=3, minutes=20) / timedelta(hours=4))


def test_utilizacao_hh_zero_horas_totais_retorna_none_sem_dividir_por_zero():
    assert consolidacao.utilizacao_hh(timedelta(hours=2), timedelta()) is None


def test_performance_formula():
    # Performance = Tempo Planejado / Tempo Real.
    assert consolidacao.performance(timedelta(hours=4), timedelta(hours=5)) == 0.8


def test_performance_zero_tempo_real_retorna_none_sem_dividir_por_zero():
    assert consolidacao.performance(timedelta(hours=1), timedelta()) is None


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
