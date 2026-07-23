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
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from . import calculo
from .catalogo import Categoria, CatalogoMotivos
from .entities import Jornada, PulsoGps
from .enums import EstadoJornada, QualidadePulso


# ----------------------------------------------------------------------
# Soma por categoria (uma jornada)
# ----------------------------------------------------------------------
def resumo_por_categoria(
    jornada: Jornada, catalogo: CatalogoMotivos
) -> Dict[Optional[Categoria], timedelta]:
    """Agrega a duracao classificada da jornada por Categoria.

    Atividades sao classificadas como ATENDIMENTO_FALHA quando tem
    dados_falha, ou ATIVIDADE_PLANEJADA quando nao tem (as duas categorias
    de docs/07_MOTOR_EVENTOS_E_HH.md que correspondem ao conceito de
    "atividade"). Pausas e eventos secundarios sao classificados pela
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
        categoria_atividade = (
            Categoria.ATENDIMENTO_FALHA if atividade.dados_falha is not None else Categoria.ATIVIDADE_PLANEJADA
        )
        _somar(categoria_atividade, calculo.duracao_atividade_liquida(atividade))

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
# Consolidacao multi-jornada
# ----------------------------------------------------------------------
@dataclass
class ResumoConsolidado:
    quantidade_jornadas: int = 0
    jornada_bruta_total: timedelta = field(default_factory=timedelta)
    tempo_classificado_total: timedelta = field(default_factory=timedelta)
    tempo_nao_classificado_total: timedelta = field(default_factory=timedelta)
    por_categoria: Dict[Optional[Categoria], timedelta] = field(default_factory=dict)


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
