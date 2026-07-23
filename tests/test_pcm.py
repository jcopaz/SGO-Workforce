"""Testes do Incremento 12: capacidade PCM.

Cobre a formula e os buckets de docs/15_CAPACIDADE_PCM.md, e a regra
"sempre mostrar premissas" da secao "Simulacao".
"""

from datetime import datetime, timedelta

import pytest

from workforce_core import MotorJornada, TipoEventoSecundario
from workforce_core.catalogo import Categoria, catalogo_padrao
from workforce_core.consolidacao import resumo_consolidado
from workforce_core.pcm import (
    BucketCapacidade,
    PremissasCenario,
    agrupar_por_bucket,
    capacidade_bruta,
    capacidade_efetiva,
    simular_cenario,
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


def test_agrupar_por_bucket_mapeia_categoria_e_lacuna():
    jornada = _jornada_completa()
    resumo = resumo_consolidado([jornada], catalogo_padrao())

    mapeamento = {
        Categoria.ATIVIDADE_PLANEJADA: BucketCapacidade.PRESENTE_PRODUTIVO_APLICAVEL,
        Categoria.DESLOCAMENTO_RODOVIARIO: BucketCapacidade.DESLOCAMENTO,
    }

    buckets = agrupar_por_bucket(resumo, mapeamento)

    assert buckets[BucketCapacidade.PRESENTE_PRODUTIVO_APLICAVEL] == timedelta(hours=2, minutes=50)
    assert buckets[BucketCapacidade.DESLOCAMENTO] == timedelta(minutes=30)
    assert buckets[BucketCapacidade.LACUNA_NAO_APONTADO] == timedelta(minutes=30)
    # PAUSA_TESTE (categoria=None no catalogo padrao) cai em "sem bucket conhecido".
    assert buckets[None] == timedelta(minutes=10)


def test_agrupar_por_bucket_sem_lacuna_nao_adiciona_chave():
    jornada = _jornada_completa()
    jornada.fim = jornada.atividades[0].fim  # remove a lacuna artificialmente para o teste
    resumo = resumo_consolidado([jornada], catalogo_padrao())

    buckets = agrupar_por_bucket(resumo, {})
    assert BucketCapacidade.LACUNA_NAO_APONTADO not in buckets


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
    assert BucketCapacidade.LACUNA_NAO_APONTADO in resultado.por_bucket
