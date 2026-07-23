"""Capacidade PCM (Incremento 12).

Formula e buckets conforme docs/15_CAPACIDADE_PCM.md - citados
literalmente, nao inventados:

    Capacidade bruta = pessoas previstas x horas de escala.
    Capacidade efetiva = capacidade bruta - ausencias - pausas nao
    computaveis - improdutividade - atividades produtivas nao aplicaveis
    ao plano.

docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 15.3 ("Antes do
Incremento 12") deixa pendente: fonte oficial de escala, fonte de
ausencias e ferias, buckets oficiais de perdas (ou seja, qual motivo/
categoria real cai em qual bucket), horizonte de projecao, sazonalidade e
regras do simulador. Por isso:

- pessoas_previstas, horas_escala, ausencias, pausas_nao_computaveis,
  improdutividade e atividades_nao_aplicaveis sao SEMPRE parametros
  explicitos - nenhuma fonte de dado real (escala, RH, ferias) e assumida;
- o mapeamento de Categoria para BucketCapacidade e SEMPRE fornecido por
  quem chama - nao ha "buckets oficiais" embutidos aqui;
- "Sempre mostrar premissas" (docs/15, secao "Simulacao") e implementado
  literalmente: ResultadoCenario sempre carrega as PremissasCenario
  usadas, nunca esconde a entrada que gerou a saida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from .catalogo import Categoria
from .consolidacao import ResumoConsolidado


class BucketCapacidade(str, Enum):
    """Buckets de docs/15_CAPACIDADE_PCM.md, secao "Buckets"."""

    AUSENTE = "AUSENTE"
    PRESENTE_PRODUTIVO_APLICAVEL = "PRESENTE_PRODUTIVO_APLICAVEL"
    PRESENTE_PRODUTIVO_NAO_APLICAVEL = "PRESENTE_PRODUTIVO_NAO_APLICAVEL"
    DESLOCAMENTO = "DESLOCAMENTO"
    ESPERA_OPERACIONAL = "ESPERA_OPERACIONAL"
    PAUSA_LEGAL_REFEICAO = "PAUSA_LEGAL_REFEICAO"
    TREINAMENTO_DDS_REUNIAO = "TREINAMENTO_DDS_REUNIAO"
    FALHA_CORRETIVA = "FALHA_CORRETIVA"
    LACUNA_NAO_APONTADO = "LACUNA_NAO_APONTADO"


def capacidade_bruta(pessoas_previstas: int, horas_escala: timedelta) -> timedelta:
    """Capacidade bruta = pessoas previstas x horas de escala (docs/15)."""
    if pessoas_previstas < 0:
        raise ValueError("pessoas_previstas nao pode ser negativo.")
    return horas_escala * pessoas_previstas


def capacidade_efetiva(
    bruta: timedelta,
    *,
    ausencias: timedelta,
    pausas_nao_computaveis: timedelta,
    improdutividade: timedelta,
    atividades_nao_aplicaveis: timedelta,
) -> timedelta:
    """Capacidade efetiva = bruta - ausencias - pausas nao computaveis -
    improdutividade - atividades produtivas nao aplicaveis ao plano
    (docs/15). Nunca fica negativa: uma capacidade efetiva negativa nao
    tem significado operacional, entao o piso e zero.
    """
    efetiva = bruta - ausencias - pausas_nao_computaveis - improdutividade - atividades_nao_aplicaveis
    return max(efetiva, timedelta())


def agrupar_por_bucket(
    resumo: ResumoConsolidado,
    mapeamento_categoria_bucket: Dict[Categoria, BucketCapacidade],
) -> Dict[Optional[BucketCapacidade], timedelta]:
    """Agrupa o HH por categoria (Incremento 8) em buckets de capacidade.

    O tempo nao classificado da jornada (gaps sem nenhum evento
    registrado) sempre vira LACUNA_NAO_APONTADO - correspondencia direta
    por definicao, nao um mapeamento inventado. Categorias sem
    correspondencia em `mapeamento_categoria_bucket` (incluindo o bucket
    `None` de "sem categoria conhecida") ficam agrupadas na chave `None`
    ("sem bucket conhecido") em vez de serem descartadas ou forcadas num
    bucket arbitrario.
    """
    buckets: Dict[Optional[BucketCapacidade], timedelta] = {}

    def _somar(bucket: Optional[BucketCapacidade], duracao: timedelta) -> None:
        buckets[bucket] = buckets.get(bucket, timedelta()) + duracao

    for categoria, duracao in resumo.por_categoria.items():
        bucket = mapeamento_categoria_bucket.get(categoria) if categoria is not None else None
        _somar(bucket, duracao)

    if resumo.tempo_nao_classificado_total:
        _somar(BucketCapacidade.LACUNA_NAO_APONTADO, resumo.tempo_nao_classificado_total)

    return buckets


@dataclass
class PremissasCenario:
    """Toda premissa usada no calculo - "sempre mostrar premissas" (docs/15)."""

    pessoas_previstas: int
    horas_escala: timedelta
    ausencias: timedelta = field(default_factory=timedelta)
    pausas_nao_computaveis: timedelta = field(default_factory=timedelta)
    improdutividade: timedelta = field(default_factory=timedelta)
    atividades_nao_aplicaveis: timedelta = field(default_factory=timedelta)
    periodo_inicio: Optional[datetime] = None
    periodo_fim: Optional[datetime] = None


@dataclass
class ResultadoCenario:
    premissas: PremissasCenario
    capacidade_bruta: timedelta
    capacidade_efetiva: timedelta
    por_bucket: Dict[Optional[BucketCapacidade], timedelta]


def simular_cenario(
    premissas: PremissasCenario,
    resumo: ResumoConsolidado,
    mapeamento_categoria_bucket: Dict[Categoria, BucketCapacidade],
) -> ResultadoCenario:
    """Roda um cenario de capacidade, sempre devolvendo as premissas usadas.

    Nao decide sozinho fonte de escala, ausencias ou buckets oficiais -
    tudo isso continua sendo decisao/entrada de quem chama (docs/27 secao
    15.3). O motor so garante que a formula de docs/15 seja aplicada de
    forma consistente e nunca esconda a premissa por tras do resultado.
    """
    bruta = capacidade_bruta(premissas.pessoas_previstas, premissas.horas_escala)
    efetiva = capacidade_efetiva(
        bruta,
        ausencias=premissas.ausencias,
        pausas_nao_computaveis=premissas.pausas_nao_computaveis,
        improdutividade=premissas.improdutividade,
        atividades_nao_aplicaveis=premissas.atividades_nao_aplicaveis,
    )
    por_bucket = agrupar_por_bucket(resumo, mapeamento_categoria_bucket)

    return ResultadoCenario(
        premissas=premissas,
        capacidade_bruta=bruta,
        capacidade_efetiva=efetiva,
        por_bucket=por_bucket,
    )
