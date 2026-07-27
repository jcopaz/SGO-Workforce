"""Capacidade PCM (Incremento 12).

Formula conforme docs/15_CAPACIDADE_PCM.md - citada literalmente, nao
inventada:

    Capacidade bruta = pessoas previstas x horas de escala.
    Capacidade efetiva = capacidade bruta - ausencias - pausas nao
    computaveis - improdutividade - atividades produtivas nao aplicaveis
    ao plano.

docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 15.3 ("Antes do
Incremento 12") deixava pendente: fonte oficial de escala, fonte de
ausencias e ferias, buckets oficiais de perdas, horizonte de projecao,
sazonalidade e regras do simulador.

Em 2026-07-23 o responsavel pelo produto forneceu a planilha real de
calculo de PCM da MRS Logistica, com os 4 buckets de perda efetivamente
usados (HORAS_AUSENTES, HORAS_PRESENTES_IMPRODUTIVAS,
HORAS_PRESENTES_NAO_APONTADAS, HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS) e
o codigo a codigo de qual motivo do Relatorio 1 cai em qual bucket - ver
docs/42_ADR_0015_BUCKETS_REAIS_PCM.md. `BucketCapacidade` e
`mapeamento_categoria_bucket_relatorio_1_manutencao()` refletem essa
planilha real; ainda assim:

- pessoas_previstas, horas_escala e ausencias_externas (ferias/motivos
  legais) continuam SEMPRE parametros explicitos - nao ha fonte de escala
  nem de RH conectada;
- fora do mapeamento real, um mapeamento arbitrario ainda pode ser
  passado a agrupar_por_bucket()/simular_cenario() por quem chama;
- "Sempre mostrar premissas" (docs/15, secao "Simulacao") continua
  implementado literalmente: ResultadoCenario sempre carrega as
  PremissasCenario usadas, nunca esconde a entrada que gerou a saida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from .catalogo import Categoria
from .consolidacao import ResumoConsolidado


class BucketCapacidade(str, Enum):
    """Buckets de perda de capacidade, conforme a planilha real de PCM da
    MRS Logistica fornecida em 2026-07-23 - ver
    docs/42_ADR_0015_BUCKETS_REAIS_PCM.md. Substituem os buckets genericos
    de docs/15_CAPACIDADE_PCM.md usados ate este ADR.
    """

    HORAS_AUSENTES = "HORAS_AUSENTES"
    HORAS_PRESENTES_IMPRODUTIVAS = "HORAS_PRESENTES_IMPRODUTIVAS"
    HORAS_PRESENTES_NAO_APONTADAS = "HORAS_PRESENTES_NAO_APONTADAS"
    HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS = "HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS"


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
    registrado) sempre vira HORAS_PRESENTES_NAO_APONTADAS -
    correspondencia direta por definicao (e exatamente o que a planilha
    real da MRS chama de "Horas presentes nao apontadas"), nao um
    mapeamento inventado. Categorias sem correspondencia em
    `mapeamento_categoria_bucket` (incluindo o bucket `None` de "sem
    categoria conhecida") ficam agrupadas na chave `None` ("sem bucket
    conhecido") em vez de serem descartadas ou forcadas num bucket
    arbitrario.
    """
    buckets: Dict[Optional[BucketCapacidade], timedelta] = {}

    def _somar(bucket: Optional[BucketCapacidade], duracao: timedelta) -> None:
        buckets[bucket] = buckets.get(bucket, timedelta()) + duracao

    for categoria, duracao in resumo.por_categoria.items():
        bucket = mapeamento_categoria_bucket.get(categoria) if categoria is not None else None
        _somar(bucket, duracao)

    if resumo.tempo_nao_classificado_total:
        _somar(BucketCapacidade.HORAS_PRESENTES_NAO_APONTADAS, resumo.tempo_nao_classificado_total)

    return buckets


def mapeamento_categoria_bucket_relatorio_1_manutencao() -> Dict[Categoria, BucketCapacidade]:
    """Mapeamento categoria -> bucket de perda, conforme a planilha real de
    calculo de PCM da MRS Logistica fornecida pelo responsavel pelo
    produto em 2026-07-23. Ver docs/42_ADR_0015_BUCKETS_REAIS_PCM.md para
    a tabela original e a justificativa completa.

    `Categoria.ATIVIDADE_PLANEJADA` (EE17, manutencao programada),
    `Categoria.ATENDIMENTO_FALHA` (EE21, atendimento de falha) e
    `Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA` (EE23, manutencao
    programada nao concluida, ver ADR-0023) deliberadamente NAO aparecem
    aqui: na planilha real, essas horas so contam como perda ("produtiva
    nao rentavel") quando NAO estao vinculadas a uma OS planejada valida -
    uma distincao que o sistema ainda nao verifica automaticamente (nao ha
    checagem de "OS valida/planejada" hoje, so o campo opcional
    `DadosFalha.os_referencia` do Incremento 13). Ate essa checagem
    existir, esses tres codigos ficam fora de qualquer bucket de perda por
    padrao aqui - tratados como capacidade efetiva/rentavel, o mesmo valor
    (0,00%) que a planilha real mostrava para eles no bucket "nao
    rentavel" no exemplo fornecido. (Numeracao de codigos atualizada pelo
    ADR-0023 em 2026-07-27 - o antigo EE22 "manutencao nao planejada"
    virou EE21 "Atendimento de Falha".)

    `FERIAS` e `MOTIVOS_LEGAIS` (bucket HORAS_AUSENTES na planilha real)
    tambem nao aparecem: nao correspondem a nenhum codigo do Relatorio 1,
    vem de uma fonte de RH/escala que o sistema ainda nao tem (mesma
    pendencia de sempre, docs/27 secao 15.3).
    """
    return {
        Categoria.REFEICAO: BucketCapacidade.HORAS_AUSENTES,
        Categoria.AGUARDANDO_CCO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.AGUARDANDO_SEQUENCIA_SERVICO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.AGUARDANDO_MATERIAL: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.PREPARACAO_JORNADA: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.RESTRICAO_INFRAESTRUTURA: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.REUNIAO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.SERVICO_INTERNO_COORDENACAO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.TRABALHO_NAO_DISTRIBUIDO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.TREM_PARADO_FRENTE_SERVICO: BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS,
        Categoria.CARREGAR_VEICULO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESCARREGAR_VEICULO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESLOCAMENTO_A_PE: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESLOCAMENTO_FERROVIARIO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESLOCAMENTO_RODOVIARIO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.DESMONTAR_ATIVIDADE: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.PREPARAR_ATIVIDADE: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.SMS: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.APOIO_OPERACIONAL: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.TREINAMENTO: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
        Categoria.CONSULTA_DOCUMENTACAO_TECNICA: BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS,
    }


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


def simular_cenario_relatorio_1_manutencao(
    pessoas_previstas: int,
    horas_escala: timedelta,
    resumo: ResumoConsolidado,
    *,
    ausencias_externas: timedelta = timedelta(),
    periodo_inicio: Optional[datetime] = None,
    periodo_fim: Optional[datetime] = None,
) -> ResultadoCenario:
    """Roda o cenario de capacidade usando o mapeamento REAL de buckets da
    MRS (mapeamento_categoria_bucket_relatorio_1_manutencao()), derivando
    automaticamente pausas_nao_computaveis, improdutividade e atividades
    nao aplicaveis a partir do apontamento real - em vez de exigir que
    quem chama estime cada termo manualmente, como `simular_cenario()`
    generico ainda faz.

    `ausencias_externas` continua sendo o unico termo verdadeiramente
    manual: ferias e motivos legais nao tem fonte de dados no sistema
    ainda (docs/27 secao 15.3, docs/42_ADR_0015_BUCKETS_REAIS_PCM.md). O
    tempo de refeicao (EE02) ja apontado entra automaticamente no total de
    ausencias a partir do apontamento real, sem precisar ser informado a
    parte.
    """
    mapeamento = mapeamento_categoria_bucket_relatorio_1_manutencao()
    por_bucket = agrupar_por_bucket(resumo, mapeamento)

    horas_ausentes_apontadas = por_bucket.get(BucketCapacidade.HORAS_AUSENTES, timedelta())
    improdutividade = por_bucket.get(BucketCapacidade.HORAS_PRESENTES_IMPRODUTIVAS, timedelta())
    nao_apontadas = por_bucket.get(BucketCapacidade.HORAS_PRESENTES_NAO_APONTADAS, timedelta())
    nao_rentaveis = por_bucket.get(
        BucketCapacidade.HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS, timedelta()
    )

    premissas = PremissasCenario(
        pessoas_previstas=pessoas_previstas,
        horas_escala=horas_escala,
        ausencias=ausencias_externas + horas_ausentes_apontadas,
        pausas_nao_computaveis=nao_apontadas,
        improdutividade=improdutividade,
        atividades_nao_aplicaveis=nao_rentaveis,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
    )

    bruta = capacidade_bruta(pessoas_previstas, horas_escala)
    efetiva = capacidade_efetiva(
        bruta,
        ausencias=premissas.ausencias,
        pausas_nao_computaveis=premissas.pausas_nao_computaveis,
        improdutividade=premissas.improdutividade,
        atividades_nao_aplicaveis=premissas.atividades_nao_aplicaveis,
    )

    return ResultadoCenario(
        premissas=premissas,
        capacidade_bruta=bruta,
        capacidade_efetiva=efetiva,
        por_bucket=por_bucket,
    )
