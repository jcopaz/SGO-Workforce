"""Motor de calculo de HH do Incremento 1.

Formulas conforme docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 7.4/7.5:

    Atividade bruta   = fim da atividade - inicio da atividade
    Pausa              = fim da pausa - inicio da pausa
    Atividade liquida = atividade bruta - soma das pausas descontaveis vinculadas
    Tempo classificado = soma(atividade liquida) + soma(pausas)
    Tempo nao classificado = jornada bruta - tempo classificado

No Incremento 1 toda pausa e integralmente descontavel (decisao provisoria,
secao 5). Classificacao de pausas produtivas/improdutivas fica para o
Incremento 5.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from .entities import Atividade, EventoSecundario, Jornada, Pausa
from .exceptions import PausaForaDoIntervaloError, TimestampInvalidoError


def duracao_pausa(pausa: Pausa) -> timedelta:
    if pausa.inicio is None or pausa.fim is None:
        raise TimestampInvalidoError(
            "Pausa sem inicio e fim definidos nao pode ser calculada."
        )
    if pausa.fim < pausa.inicio:
        raise TimestampInvalidoError("Pausa com fim anterior ao inicio.")
    return pausa.fim - pausa.inicio


def duracao_atividade_bruta(atividade: Atividade) -> timedelta:
    if atividade.inicio is None or atividade.fim is None:
        raise TimestampInvalidoError(
            "Atividade sem inicio e fim definidos nao pode ser calculada."
        )
    if atividade.fim < atividade.inicio:
        raise TimestampInvalidoError("Atividade com fim anterior ao inicio.")
    return atividade.fim - atividade.inicio


def _validar_pausa_contida(pausa: Pausa, atividade: Atividade) -> None:
    if pausa.inicio < atividade.inicio:
        raise PausaForaDoIntervaloError(
            "Pausa iniciada antes do inicio da atividade a qual pertence."
        )
    if atividade.fim is not None and pausa.fim is not None and pausa.fim > atividade.fim:
        raise PausaForaDoIntervaloError(
            "Pausa encerrada depois do fim da atividade a qual pertence."
        )


def duracao_pausas_atividade(atividade: Atividade) -> timedelta:
    total = timedelta()
    for pausa in atividade.pausas:
        _validar_pausa_contida(pausa, atividade)
        total += duracao_pausa(pausa)
    return total


def duracao_atividade_liquida(atividade: Atividade) -> timedelta:
    return duracao_atividade_bruta(atividade) - duracao_pausas_atividade(atividade)


def duracao_evento_secundario(evento: EventoSecundario) -> timedelta:
    if evento.inicio is None or evento.fim is None:
        raise TimestampInvalidoError(
            "Evento secundario sem inicio e fim definidos nao pode ser calculado."
        )
    if evento.fim < evento.inicio:
        raise TimestampInvalidoError("Evento secundario com fim anterior ao inicio.")
    return evento.fim - evento.inicio


def duracao_eventos_secundarios(jornada: Jornada) -> timedelta:
    total = timedelta()
    for evento in jornada.eventos_secundarios:
        total += duracao_evento_secundario(evento)
    return total


def duracao_jornada_bruta(jornada: Jornada) -> timedelta:
    if jornada.inicio is None or jornada.fim is None:
        raise TimestampInvalidoError(
            "Jornada sem inicio e fim definidos nao pode ser calculada."
        )
    if jornada.fim < jornada.inicio:
        raise TimestampInvalidoError("Jornada com fim anterior ao inicio.")
    return jornada.fim - jornada.inicio


def tempo_classificado_jornada(jornada: Jornada) -> timedelta:
    total = timedelta()
    for atividade in jornada.atividades:
        total += duracao_atividade_liquida(atividade)
        total += duracao_pausas_atividade(atividade)
    total += duracao_eventos_secundarios(jornada)
    return total


def tempo_nao_classificado(jornada: Jornada) -> timedelta:
    return duracao_jornada_bruta(jornada) - tempo_classificado_jornada(jornada)


def resumo_atividade(atividade: Atividade) -> Dict[str, object]:
    return {
        "id": atividade.id,
        "bruta": duracao_atividade_bruta(atividade),
        "pausas": duracao_pausas_atividade(atividade),
        "liquida": duracao_atividade_liquida(atividade),
    }


def resumo_evento_secundario(evento: EventoSecundario) -> Dict[str, object]:
    return {
        "id": evento.id,
        "tipo": evento.tipo,
        "motivo": evento.motivo,
        "duracao": duracao_evento_secundario(evento),
    }


def resumo_jornada(jornada: Jornada) -> Dict[str, object]:
    atividades: List[Dict[str, object]] = [
        resumo_atividade(atividade) for atividade in jornada.atividades
    ]
    eventos_secundarios: List[Dict[str, object]] = [
        resumo_evento_secundario(evento) for evento in jornada.eventos_secundarios
    ]
    return {
        "jornada_bruta": duracao_jornada_bruta(jornada),
        "tempo_classificado": tempo_classificado_jornada(jornada),
        "tempo_nao_classificado": tempo_nao_classificado(jornada),
        "atividades": atividades,
        "eventos_secundarios": eventos_secundarios,
    }
