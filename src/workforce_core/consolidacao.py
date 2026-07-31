"""Consolidacao de HH e qualidade dos dados (Incremento 8).

Reune capacidades citadas em docs/20_TESTES_E_QUALIDADE.md, secoes
"Reconciliacao" (soma por jornada, soma por categoria, pulsos enviados x
recebidos) e "Observabilidade" (jornadas abertas anormais, taxa de GPS
valido). Nao inventa nenhum limiar de negocio: tudo que a doc nao define
numericamente (o que conta como "muito tempo aberta", por exemplo) e
recebido como parametro explicito de quem chama.

"Soma por OS", "dashboard x exportacao" e "eventos x HH de equipe" (as
demais linhas de "Reconciliacao") dependem de conceitos que ainda nao
existem no sistema (OS, equipe, dashboards, exportacoes) e ficam para os
incrementos correspondentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from . import calculo
from .catalogo import Categoria, CatalogoMotivos, ClassificacaoHH
from .entities import Atividade, Jornada, PulsoGps
from .enums import EstadoJornada, QualidadePulso, ResultadoAtividade


def _categoria_atividade(atividade: Atividade) -> Categoria:
    """Classifica uma Atividade encerrada em ATENDIMENTO_FALHA, ATIVIDADE_PLANEJADA
    ou ATIVIDADE_PLANEJADA_NAO_CONCLUIDA (EE21/EE17/EE23).

    dados_falha tem precedencia sobre `resultado`: um atendimento de falha
    so encerra via encerrar_atividade/transferir_atendimento_falha, nunca
    via encerrar_atividade_nao_concluida (ADR-0025), entao sempre e
    ATENDIMENTO_FALHA independente do `resultado` gravado.

    `resultado is None` (qualquer Atividade encerrada antes do ADR-0025,
    quando o campo nao existia) e tratado como CONCLUIDA - mesmo
    comportamento implicito que ja existia, sem reclassificar dados ja
    sincronizados.
    """
    if atividade.dados_falha is not None:
        return Categoria.ATENDIMENTO_FALHA
    if atividade.resultado == ResultadoAtividade.NAO_CONCLUIDA:
        return Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA
    return Categoria.ATIVIDADE_PLANEJADA


# ----------------------------------------------------------------------
# Soma por categoria (uma jornada)
# ----------------------------------------------------------------------
def resumo_por_categoria(
    jornada: Jornada, catalogo: CatalogoMotivos
) -> Dict[Optional[Categoria], timedelta]:
    """Agrega a duracao classificada da jornada por Categoria.

    Atividades sao classificadas por `_categoria_atividade`: ATENDIMENTO_FALHA
    quando tem dados_falha, ATIVIDADE_PLANEJADA_NAO_CONCLUIDA quando o
    resultado e NAO_CONCLUIDA (ADR-0025), ou ATIVIDADE_PLANEJADA caso
    contrario. Pausas e eventos secundarios sao classificados pela
    categoria associada ao seu motivo no catalogo informado; quando o
    motivo nao esta no catalogo ou nao tem categoria definida, a duracao
    entra no bucket `None` ("sem categoria conhecida").
    """
    totais: Dict[Optional[Categoria], timedelta] = {}

    def _somar(categoria: Optional[Categoria], duracao: timedelta) -> None:
        totais[categoria] = totais.get(categoria, timedelta()) + duracao

    for atividade in jornada.atividades:
        if atividade.fim is None:
            continue
        _somar(_categoria_atividade(atividade), calculo.duracao_atividade_liquida(atividade))

        for pausa in atividade.pausas:
            if pausa.fim is None:
                continue
            entrada = catalogo.obter(pausa.motivo)
            categoria_pausa = entrada.categoria if entrada is not None else None
            _somar(categoria_pausa, calculo.duracao_pausa(pausa))

    for evento in jornada.eventos_secundarios:
        if evento.fim is None:
            continue
        entrada = catalogo.obter(evento.motivo)
        categoria_evento = entrada.categoria if entrada is not None else None
        _somar(categoria_evento, calculo.duracao_evento_secundario(evento))

    return totais


# ----------------------------------------------------------------------
# Soma por classificacao de HH (uma jornada) - base para o indicador de
# Utilizacao HH (ver secao "Indicadores de HH" no fim deste modulo).
# ----------------------------------------------------------------------
def resumo_por_classificacao_hh(
    jornada: Jornada, catalogo: CatalogoMotivos
) -> Dict[ClassificacaoHH, timedelta]:
    """Agrega a duracao classificada da jornada por ClassificacaoHH
    (PRODUTIVA/IMPRODUTIVA/NAO_COMPUTAVEL/NAO_DEFINIDO).

    Pausas e eventos secundarios usam `classificacao_hh` da entrada do
    catalogo associada ao seu motivo, igual a `resumo_por_categoria`.
    Atividades nao tem `motivo` (sao tipadas por `Categoria` via
    `_categoria_atividade`, nao por codigo de catalogo) - por isso usam a
    `classificacao_hh` da entrada do catalogo cuja `categoria` bate com a
    Categoria derivada, unica correspondencia automatica permitida
    (mesma fonte de verdade do catalogo, nada reclassificado por fora
    dele). Quando o motivo/categoria nao esta no catalogo, a duracao
    entra no bucket `ClassificacaoHH.NAO_DEFINIDO` - nunca descartada.
    """
    totais: Dict[ClassificacaoHH, timedelta] = {}

    def _somar(classificacao: ClassificacaoHH, duracao: timedelta) -> None:
        totais[classificacao] = totais.get(classificacao, timedelta()) + duracao

    categoria_para_classificacao = {
        entrada.categoria: entrada.classificacao_hh
        for entrada in catalogo.todos()
        if entrada.categoria is not None
    }

    for atividade in jornada.atividades:
        if atividade.fim is None:
            continue
        categoria = _categoria_atividade(atividade)
        classificacao = categoria_para_classificacao.get(categoria, ClassificacaoHH.NAO_DEFINIDO)
        _somar(classificacao, calculo.duracao_atividade_liquida(atividade))

        for pausa in atividade.pausas:
            if pausa.fim is None:
                continue
            entrada = catalogo.obter(pausa.motivo)
            classificacao_pausa = entrada.classificacao_hh if entrada is not None else ClassificacaoHH.NAO_DEFINIDO
            _somar(classificacao_pausa, calculo.duracao_pausa(pausa))

    for evento in jornada.eventos_secundarios:
        if evento.fim is None:
            continue
        entrada = catalogo.obter(evento.motivo)
        classificacao_evento = entrada.classificacao_hh if entrada is not None else ClassificacaoHH.NAO_DEFINIDO
        _somar(classificacao_evento, calculo.duracao_evento_secundario(evento))

    return totais


# ----------------------------------------------------------------------
# Linhas de evento classificadas (uma linha por atividade/pausa/evento
# secundario encerrado) - base para filtros e graficos de detalhamento
# no painel (por colaborador, por dia, por categoria, por motivo). Mesma
# classificacao de resumo_por_categoria, so que sem agregar - cada evento
# vira uma linha, para quem consome poder filtrar antes de somar.
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class LinhaEvento:
    colaborador_matricula: str
    data: date
    categoria: Optional[Categoria]
    motivo: Optional[str]
    duracao: timedelta
    tipo: str  # "ATIVIDADE" | "PAUSA" | "EVENTO_SECUNDARIO"


def linhas_eventos_classificadas(
    jornadas: List[Jornada], catalogo: CatalogoMotivos
) -> List[LinhaEvento]:
    """Achata as jornadas encerradas em uma linha por atividade, pausa e
    evento secundario ja encerrado, cada uma com colaborador, data,
    categoria e motivo - para os filtros do painel (colaborador, periodo,
    categoria, motivo/justificativa) operarem sobre eventos individuais,
    nao só sobre a jornada inteira.
    """
    linhas: List[LinhaEvento] = []
    for jornada in jornadas:
        if jornada.estado != EstadoJornada.ENCERRADA:
            continue
        for atividade in jornada.atividades:
            if atividade.fim is None:
                continue
            linhas.append(
                LinhaEvento(
                    colaborador_matricula=jornada.colaborador_matricula,
                    data=atividade.inicio.date(),
                    categoria=_categoria_atividade(atividade),
                    motivo=None,
                    duracao=calculo.duracao_atividade_liquida(atividade),
                    tipo="ATIVIDADE",
                )
            )
            for pausa in atividade.pausas:
                if pausa.fim is None:
                    continue
                entrada = catalogo.obter(pausa.motivo)
                linhas.append(
                    LinhaEvento(
                        colaborador_matricula=jornada.colaborador_matricula,
                        data=pausa.inicio.date(),
                        categoria=entrada.categoria if entrada is not None else None,
                        motivo=pausa.motivo,
                        duracao=calculo.duracao_pausa(pausa),
                        tipo="PAUSA",
                    )
                )

        for evento in jornada.eventos_secundarios:
            if evento.fim is None:
                continue
            entrada = catalogo.obter(evento.motivo)
            linhas.append(
                LinhaEvento(
                    colaborador_matricula=jornada.colaborador_matricula,
                    data=evento.inicio.date(),
                    categoria=entrada.categoria if entrada is not None else None,
                    motivo=evento.motivo,
                    duracao=calculo.duracao_evento_secundario(evento),
                    tipo="EVENTO_SECUNDARIO",
                )
            )

    return linhas


# ----------------------------------------------------------------------
# Consolidacao multi-jornada
# ----------------------------------------------------------------------
@dataclass
class ResumoConsolidado:
    quantidade_jornadas: int = 0
    jornada_bruta_total: timedelta = field(default_factory=timedelta)
    tempo_classificado_total: timedelta = field(default_factory=timedelta)
    tempo_nao_classificado_total: timedelta = field(default_factory=timedelta)
    por_categoria: Dict[Optional[Categoria], timedelta] = field(default_factory=dict)
    por_classificacao_hh: Dict[ClassificacaoHH, timedelta] = field(default_factory=dict)


def resumo_consolidado(jornadas: List[Jornada], catalogo: CatalogoMotivos) -> ResumoConsolidado:
    """Consolida HH de varias jornadas encerradas (ex.: uma equipe, um periodo).

    Jornadas nao encerradas (sem `fim`) sao ignoradas aqui - nao ha
    duracao bruta valida para uma jornada em andamento. Use
    `jornadas_abertas_ha_muito_tempo` para monitorar essas separadamente.
    """
    resumo = ResumoConsolidado()
    for jornada in jornadas:
        if jornada.estado != EstadoJornada.ENCERRADA:
            continue
        resumo.quantidade_jornadas += 1
        resumo.jornada_bruta_total += calculo.duracao_jornada_bruta(jornada)
        resumo.tempo_classificado_total += calculo.tempo_classificado_jornada(jornada)
        resumo.tempo_nao_classificado_total += calculo.tempo_nao_classificado(jornada)

        for categoria, duracao in resumo_por_categoria(jornada, catalogo).items():
            resumo.por_categoria[categoria] = resumo.por_categoria.get(categoria, timedelta()) + duracao

        for classificacao, duracao in resumo_por_classificacao_hh(jornada, catalogo).items():
            resumo.por_classificacao_hh[classificacao] = (
                resumo.por_classificacao_hh.get(classificacao, timedelta()) + duracao
            )

    return resumo


# ----------------------------------------------------------------------
# Qualidade dos dados
# ----------------------------------------------------------------------
def jornadas_abertas_ha_muito_tempo(
    jornadas: List[Jornada], *, agora: datetime, limite: timedelta
) -> List[Jornada]:
    """Jornadas ABERTA cujo tempo decorrido desde o inicio ultrapassa `limite`.

    Nao ha limite padrao - "anormal" e uma decisao de negocio pendente
    (nao existe hoje um valor validado de "jornada aberta demais").
    """
    return [
        jornada
        for jornada in jornadas
        if jornada.estado == EstadoJornada.ABERTA
        and jornada.inicio is not None
        and (agora - jornada.inicio) > limite
    ]


def taxa_qualidade_pulsos(pulsos: List[PulsoGps]) -> Optional[float]:
    """Proporcao de pulsos avaliados que estao QualidadePulso.OK.

    Pulsos NAO_AVALIADO ficam fora do denominador (ainda nao foram
    classificados, entao nao contam nem a favor nem contra a taxa).
    Retorna None se nao houver nenhum pulso avaliado.
    """
    avaliados = [p for p in pulsos if p.qualidade != QualidadePulso.NAO_AVALIADO]
    if not avaliados:
        return None
    ok = sum(1 for p in avaliados if p.qualidade == QualidadePulso.OK)
    return ok / len(avaliados)


def pulsos_pendentes_de_sincronizacao(total_local: int, total_sincronizado: int) -> int:
    """Diferenca entre pulsos gravados localmente e confirmados pelo servidor.

    Reconciliacao "pulsos enviados x recebidos" de
    docs/20_TESTES_E_QUALIDADE.md. `total_sincronizado` normalmente vem de
    CursorSincronizacaoPulsos.total_sincronizado.
    """
    return max(total_local - total_sincronizado, 0)


# ----------------------------------------------------------------------
# Indicadores de HH (Utilizacao e Performance) - formulas fornecidas pelo
# responsavel pelo produto em 2026-07-30, ver
# docs/54_ADR_0027_INDICADORES_UTILIZACAO_HH_E_PERFORMANCE.md. Funcoes
# puras (sem nenhuma fonte de dado embutida, mesmo principio de
# taxa_qualidade_pulsos): quem chama decide o numerador/denominador e
# nunca ha divisao por zero silenciosa.
# ----------------------------------------------------------------------
def utilizacao_hh(horas_produtivas: timedelta, horas_totais: timedelta) -> Optional[float]:
    """Utilizacao HH = Horas Produtivas / Horas Totais.

    Mede quanto do periodo de trabalho do colaborador foi convertido em
    manutencao executavel. `horas_produtivas` normalmente vem de
    `ResumoConsolidado.por_classificacao_hh[ClassificacaoHH.PRODUTIVA]`
    (ver `resumo_por_classificacao_hh`); `horas_totais` normalmente e
    `ResumoConsolidado.jornada_bruta_total` - nunca calculado aqui, sempre
    recebido explicito de quem chama. Retorna `None` quando
    `horas_totais` e zero (nada para dividir), nunca `ZeroDivisionError`.
    """
    if horas_totais.total_seconds() == 0:
        return None
    return horas_produtivas.total_seconds() / horas_totais.total_seconds()


def performance(tempo_planejado: timedelta, tempo_real: timedelta) -> Optional[float]:
    """Performance = Tempo Planejado / Tempo Real.

    Mede quao aderente o colaborador esteve ao tempo planejado de
    execucao da(s) atividade(s). O sistema ainda NAO modela "tempo
    planejado" em nenhuma entidade (nem OS nem Atividade tem uma duracao
    estimada) - decisao pendente, ver
    docs/23_DECISOES_PENDENTES.md. Esta funcao existe pronta para quando
    essa fonte existir (ex.: tempo planejado por OS vindo do SGO no
    futuro, Fase 5) - ate la, nenhuma tela deste sistema deve inventar um
    tempo planejado so para preencher o indicador. Retorna `None` quando
    `tempo_real` e zero, nunca `ZeroDivisionError`.
    """
    if tempo_real.total_seconds() == 0:
        return None
    return tempo_planejado.total_seconds() / tempo_real.total_seconds()
