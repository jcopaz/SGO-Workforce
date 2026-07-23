"""Testes do Incremento 12: capacidade PCM.

Cobre a formula de docs/15_CAPACIDADE_PCM.md, a regra "sempre mostrar
premissas" da secao "Simulacao", e os buckets reais da planilha de PCM da
MRS Logistica fornecida em 2026-07-23 (ver
docs/42_ADR_0015_BUCKETS_REAIS_PCM.md).
"""

from datetime import datetime, timedelta

import pytest

from workforce_core import MotorJornada, TipoEventoSecundario
from workforce_core.catalogo import Categoria, catalogo_padrao, catalogo_relatorio_1_manutencao
from workforce_core.consolidacao import resumo_consolidado
from workforce_core.pcm import (
    BucketCapacidade,
    PremissasCenario,
    agrupar_por_bucket,
    capacidade_bruta,
    capacidade_efetiva,
    mapeamento_categoria_bucket_relatorio_1_manutencao,
    simular_cenario,
    simular_cenario_relatorio_1_manutencao,
)


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
    motor.encerrar_jornada(_dt(12, 0))  # 30min de lacuna nao classificada (11:30-12:00)
    return motor.jornada


def test_capacidade_bruta():
    assert capacidade_bruta(10, timedelta(hours=8)) == timedelta(hours=80)
    assert capacidade_bruta(0, timedelta(hours=8)) == timedelta()


def test_capacidade_bruta_rejeita_pessoas_negativas():
    with pytest.raises(ValueError):
        capacidade_bruta(-1, timedelta(hours=8))


def test_capacidade_efetiva_subtrai_tudo():
    bruta = timedelta(hours=80)
    efetiva = capacidade_efetiva(
        bruta,
        ausencias=timedelta(hours=8),
        pausas_nao_computaveis=timedelta(hours=4),
        improdutividade=timedelta(hours=2),
        atividades_nao_aplicaveis=timedelta(hours=1),
    )
    assert efetiva == timedelta(hours=65)


def test_capacidade_efetiva_nunca_fica_negativa():
    efetiva = capacidade_efetiva(
        timedelta(hours=10),
        ausencias=timedelta(hours=8),
        pausas_nao_computaveis=timedelta(hours=8),
        improdutividade=timedelta(hours=8),
        atividades_nao_aplicaveis=timedelta(hours=8),
    )
    assert efetiva == timedelta()


def test_agrupar_por_bucket_mapeia_categoria_e_nao_apontado():
    jornada = _jornada_completa()
    resumo = resumo_consolidado([jornada], catalogo_padrao())

    mapeamento = {
        Categoria.ATIVIDADE_PLANEJADA: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESLOCAMENTO_RODOVIARIO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
    }

    buckets = agrupar_por_bucket(resumo, mapeamento)

    assert buckets[BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS] == timedelta(
        hours=3, minutes=20
    )
    assert buckets[BucketCapacidade.HORAS_PRESENTES_NAO_APONTADAS] == timedelta(minutes=30)
    # PAUSA_TESTE (categoria=None no catalogo padrao) cai em "sem bucket conhecido".
    assert buckets[None] == timedelta(minutes=10)


def test_agrupar_por_bucket_sem_lacuna_nao_adiciona_chave():
    jornada = _jornada_completa()
    jornada.fim = jornada.atividades[0].fim  # remove a lacuna artificialmente para o teste
    resumo = resumo_consolidado([jornada], catalogo_padrao())

    buckets = agrupar_por_bucket(resumo, {})
    assert BucketCapacidade.HORAS_PRESENTES_NAO_APONTADAS not in buckets


def test_simular_cenario_sempre_devolve_premissas():
    jornada = _jornada_completa()
    resumo = resumo_consolidado([jornada], catalogo_padrao())
    premissas = PremissasCenario(
        pessoas_previstas=5,
        horas_escala=timedelta(hours=8),
        ausencias=timedelta(hours=1),
    )

    resultado = simular_cenario(premissas, resumo, {})

    assert resultado.premissas is premissas
    assert resultado.capacidade_bruta == timedelta(hours=40)
    assert resultado.capacidade_efetiva == timedelta(hours=39)
    assert BucketCapacidade.HORAS_PRESENTES_NAO_APONTADAS in resultado.por_bucket


# ----------------------------------------------------------------------
# Mapeamento e simulacao com os buckets reais da MRS (ADR-0015)
# ----------------------------------------------------------------------
def _jornada_relatorio_1(matricula="12345"):
    """Jornada usando os codigos reais do Relatorio 1: deslocamento (EE12),
    atividade planejada (EE17), pausa para refeicao (EE02), e uma lacuna
    nao classificada no final.
    """
    motor = MotorJornada(matricula)
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_evento_secundario(_dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "EE12")
    motor.encerrar_evento_secundario(_dt(8, 30))
    motor.iniciar_atividade(_dt(8, 30))
    motor.iniciar_pausa(_dt(9, 0), "EE02")
    motor.finalizar_pausa(_dt(9, 10))
    motor.encerrar_atividade(_dt(11, 30))
    motor.encerrar_jornada(_dt(12, 0))  # 30min de lacuna
    return motor.jornada


def test_mapeamento_real_nao_inclui_atividade_planejada_nem_atendimento_falha():
    mapeamento = mapeamento_categoria_bucket_relatorio_1_manutencao()
    assert Categoria.ATIVIDADE_PLANEJADA not in mapeamento
    assert Categoria.ATENDIMENTO_FALHA not in mapeamento


def test_mapeamento_real_refeicao_e_ausente():
    mapeamento = mapeamento_categoria_bucket_relatorio_1_manutencao()
    assert mapeamento[Categoria.REFEICAO] == BucketCapacidade.HORAS_AUSENTES


def test_mapeamento_real_deslocamento_e_produtivo_nao_rentavel():
    mapeamento = mapeamento_categoria_bucket_relatorio_1_manutencao()
    assert (
        mapeamento[Categoria.DESLOCAMENTO_RODOVIARIO]
        == BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS
    )


def test_simular_cenario_relatorio_1_deriva_termos_automaticamente():
    jornada = _jornada_relatorio_1()
    resumo = resumo_consolidado([jornada], catalogo_relatorio_1_manutencao())

    resultado = simular_cenario_relatorio_1_manutencao(
        pessoas_previstas=1,
        horas_escala=timedelta(hours=8),
        resumo=resumo,
    )

    # Refeicao (EE02, 10min) contabilizada automaticamente como ausencia.
    assert resultado.premissas.ausencias == timedelta(minutes=10)
    # Lacuna (30min) automaticamente como "pausas_nao_computaveis".
    assert resultado.premissas.pausas_nao_computaveis == timedelta(minutes=30)
    # Deslocamento (EE12, 30min) automaticamente como "nao aplicavel ao plano".
    assert resultado.premissas.atividades_nao_aplicaveis == timedelta(minutes=30)
    # Nenhum codigo IMPRODUTIVO nesta jornada de exemplo.
    assert resultado.premissas.improdutividade == timedelta()

    assert resultado.capacidade_bruta == timedelta(hours=8)
    esperado = timedelta(hours=8) - timedelta(minutes=10) - timedelta(minutes=30) - timedelta(minutes=30)
    assert resultado.capacidade_efetiva == esperado


def test_simular_cenario_relatorio_1_soma_ausencias_externas():
    jornada = _jornada_relatorio_1()
    resumo = resumo_consolidado([jornada], catalogo_relatorio_1_manutencao())

    resultado = simular_cenario_relatorio_1_manutencao(
        pessoas_previstas=1,
        horas_escala=timedelta(hours=8),
        resumo=resumo,
        ausencias_externas=timedelta(hours=1),  # ex.: ferias/motivos legais
    )

    assert resultado.premissas.ausencias == timedelta(hours=1, minutes=10)
