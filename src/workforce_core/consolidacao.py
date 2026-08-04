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
from .fuso_horario import para_horario_brasil


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
# Classificacao pontual (o que estava em andamento em um instante) - base
# para colorir/filtrar pulsos de GPS por atividade no mapa operacional
# (pedido do responsavel pelo produto em 2026-08-04, ver ADR-0047).
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificacaoInstante:
    tipo: str  # "ATIVIDADE" | "ATENDIMENTO_FALHA" | "PAUSA" | "EVENTO_SECUNDARIO" | "SEM_ATIVIDADE"
    motivo: Optional[str]  # codigo (pausa/evento secundario) - None para os demais tipos


def _contem_instante(inicio: Optional[datetime], fim: Optional[datetime], momento: datetime) -> bool:
    """Um intervalo sem `fim` (evento ainda em andamento no momento em que
    os dados foram lidos) e tratado como aberto - nunca deixa de "conter"
    um momento so por falta de fim registrado."""
    if inicio is None or momento < inicio:
        return False
    return fim is None or momento <= fim


def classificar_instante(jornada: Jornada, momento: datetime) -> ClassificacaoInstante:
    """Determina o que estava em andamento na jornada em `momento` (ex.:
    o `timestamp_dispositivo` de um pulso de GPS) - qual atividade, pausa
    ou evento secundario estava ativo.

    Pausa tem precedencia sobre a atividade que a contem (esta "dentro"
    dela); atividade e evento secundario sao mutuamente exclusivos por
    construcao (`MotorJornada`/`motorJornada.js`), entao a ordem de
    checagem entre eles nunca produz ambiguidade na pratica. Quando nada
    cobre o instante (jornada aberta sem nada especifico em andamento),
    devolve `SEM_ATIVIDADE`.
    """
    for atividade in jornada.atividades:
        if not _contem_instante(atividade.inicio, atividade.fim, momento):
            continue
        for pausa in atividade.pausas:
            if _contem_instante(pausa.inicio, pausa.fim, momento):
                return ClassificacaoInstante(tipo="PAUSA", motivo=pausa.motivo)
        tipo = "ATENDIMENTO_FALHA" if atividade.dados_falha is not None else "ATIVIDADE"
        return ClassificacaoInstante(tipo=tipo, motivo=None)

    for evento in jornada.eventos_secundarios:
        if _contem_instante(evento.inicio, evento.fim, momento):
            return ClassificacaoInstante(tipo="EVENTO_SECUNDARIO", motivo=evento.motivo)

    return ClassificacaoInstante(tipo="SEM_ATIVIDADE", motivo=None)


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
                    data=para_horario_brasil(atividade.inicio).date(),
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
                        data=para_horario_brasil(pausa.inicio).date(),
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
                    data=para_horario_brasil(evento.inicio).date(),
                    categoria=entrada.categoria if entrada is not None else None,
                    motivo=evento.motivo,
                    duracao=calculo.duracao_evento_secundario(evento),
                    tipo="EVENTO_SECUNDARIO",
                )
            )

    return linhas


# ----------------------------------------------------------------------
# Atendimentos de falha (ADR-0029) - uma linha por atendimento encerrado,
# base para a aba "Falhas" do painel (docs/12_DASHBOARDS_ECHARTS.md, "Top
# sintomas, causas, ..., HH consumido", nunca implementada ate aqui).
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class LinhaAtendimentoFalha:
    colaborador_matricula: str
    data: date
    inicio: datetime
    fim: datetime
    duracao: timedelta
    nota: Optional[str]
    ativo: Optional[str]
    sintoma: Optional[str]
    objeto: Optional[str]


def linhas_atendimento_falha(jornadas: List[Jornada]) -> List[LinhaAtendimentoFalha]:
    """Achata as jornadas em uma linha por atendimento de falha encerrado
    (Atividade com `dados_falha`, ver `DadosFalha`).

    `duracao` usa `calculo.duracao_atividade_bruta` (fim - inicio, tempo
    total decorrido) - deliberadamente diferente de `linhas_eventos_classificadas`,
    que usa a duracao liquida (descontando pausas) para fins de HH do
    colaborador. Aqui o interesse e "quanto tempo a falha ficou em
    aberto" (tempo de atendimento de ponta a ponta), nao HH liquido.

    Diferente de `linhas_eventos_classificadas`, NAO exige
    `jornada.estado == ENCERRADA` - um atendimento de falha ja concluido
    dentro de uma jornada ainda aberta (colaborador segue trabalhando)
    deve aparecer no painel de falhas imediatamente, nao só no fim do
    turno (decisao deliberada para uma visao operacional de falhas, ver
    ADR-0029).

    Inclui atendimentos com `dados_falha` incompleto (ex.: transferidos
    via `docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md`
    antes de preencher tudo) - campos ausentes ficam `None`, nunca
    descarta a linha; quem consome decide como exibir.
    """
    linhas: List[LinhaAtendimentoFalha] = []
    for jornada in jornadas:
        for atividade in jornada.atividades:
            if atividade.dados_falha is None or atividade.fim is None:
                continue
            dados = atividade.dados_falha
            linhas.append(
                LinhaAtendimentoFalha(
                    colaborador_matricula=jornada.colaborador_matricula,
                    data=para_horario_brasil(atividade.inicio).date(),
                    inicio=atividade.inicio,
                    fim=atividade.fim,
                    duracao=calculo.duracao_atividade_bruta(atividade),
                    nota=dados.nota,
                    ativo=dados.ativo,
                    sintoma=dados.sintoma,
                    objeto=dados.objeto,
                )
            )
    return linhas


@dataclass
class ResumoAtendimentosFalha:
    quantidade: int = 0
    duracao_total: timedelta = field(default_factory=timedelta)
    duracao_media: Optional[timedelta] = None
    maior_duracao: Optional[timedelta] = None


def resumo_atendimentos_falha(linhas: List[LinhaAtendimentoFalha]) -> ResumoAtendimentosFalha:
    """KPIs agregados de uma lista de LinhaAtendimentoFalha - quantidade,
    duracao total, media e maior duracao. `duracao_media`/`maior_duracao`
    ficam `None` (nunca ZeroDivisionError/erro em lista vazia) quando nao
    ha nenhuma linha."""
    if not linhas:
        return ResumoAtendimentosFalha()
    duracoes = [linha.duracao for linha in linhas]
    total = sum(duracoes, timedelta())
    return ResumoAtendimentosFalha(
        quantidade=len(linhas),
        duracao_total=total,
        duracao_media=total / len(linhas),
        maior_duracao=max(duracoes),
    )


def contagem_por_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    """Conta atendimentos por sintoma - sintoma ausente/None entra no
    rotulo "Sem sintoma informado" (nunca descartado)."""
    totais: Dict[str, int] = {}
    for linha in linhas:
        chave = linha.sintoma or "Sem sintoma informado"
        totais[chave] = totais.get(chave, 0) + 1
    return totais


def contagem_por_ativo(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    """Conta atendimentos por ativo - ativo ausente/None entra no rotulo
    "Sem ativo informado" (nunca descartado)."""
    totais: Dict[str, int] = {}
    for linha in linhas:
        chave = linha.ativo or "Sem ativo informado"
        totais[chave] = totais.get(chave, 0) + 1
    return totais


def contagem_por_objeto(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    """Conta atendimentos por objeto (componente causador, catalogo RASF)
    - objeto ausente/None entra no rotulo "Sem objeto informado" (nunca
    descartado). Mesmo padrao de contagem_por_sintoma/contagem_por_ativo."""
    totais: Dict[str, int] = {}
    for linha in linhas:
        chave = linha.objeto or "Sem objeto informado"
        totais[chave] = totais.get(chave, 0) + 1
    return totais


def duracao_media_por_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, timedelta]:
    """Duracao media (nao total) de atendimento por sintoma - "quais
    sintomas tipicamente demoram mais para resolver", distinto do ranking
    de piores ocorrencias individuais (que mostra so o pior caso, nao a
    tendencia). Sintoma ausente/None entra no rotulo "Sem sintoma
    informado"."""
    total_por_sintoma: Dict[str, timedelta] = {}
    contagem: Dict[str, int] = {}
    for linha in linhas:
        chave = linha.sintoma or "Sem sintoma informado"
        total_por_sintoma[chave] = total_por_sintoma.get(chave, timedelta()) + linha.duracao
        contagem[chave] = contagem.get(chave, 0) + 1
    return {chave: total / contagem[chave] for chave, total in total_por_sintoma.items()}


def ativos_reincidentes(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    """Ativos com mais de um atendimento de falha no periodo - reincidencia
    e definida como "aconteceu mais de uma vez" (piso 2, nao um limiar de
    negocio inventado). Ativo ausente/None nunca conta como reincidente
    (nao da pra saber se e o mesmo ativo sem identificacao)."""
    contagem = contagem_por_ativo([linha for linha in linhas if linha.ativo])
    return {ativo: quantidade for ativo, quantidade in contagem.items() if quantidade > 1}


def agrupar_ativo_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, Dict[str, timedelta]]:
    """Duracao total por (ativo, sintoma) - base do detalhamento
    hierarquico ativo > sintoma no painel. Ausentes entram nos mesmos
    rotulos "Sem ativo/sintoma informado" de contagem_por_ativo/sintoma."""
    agrupado: Dict[str, Dict[str, timedelta]] = {}
    for linha in linhas:
        chave_ativo = linha.ativo or "Sem ativo informado"
        chave_sintoma = linha.sintoma or "Sem sintoma informado"
        por_sintoma = agrupado.setdefault(chave_ativo, {})
        por_sintoma[chave_sintoma] = por_sintoma.get(chave_sintoma, timedelta()) + linha.duracao
    return agrupado


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


def resumo_consolidado_por_colaborador(
    jornadas: List[Jornada], catalogo: CatalogoMotivos
) -> Dict[str, ResumoConsolidado]:
    """Mesma consolidacao de resumo_consolidado, mas uma entrada por
    colaborador_matricula - base do indicador de Utilizacao HH individual
    (por colaborador) no painel, em vez de so o agregado do periodo
    inteiro. Colaboradores sem nenhuma jornada encerrada nao aparecem no
    resultado (mesmo criterio de resumo_consolidado)."""
    jornadas_por_colaborador: Dict[str, List[Jornada]] = {}
    for jornada in jornadas:
        jornadas_por_colaborador.setdefault(jornada.colaborador_matricula, []).append(jornada)

    resultado: Dict[str, ResumoConsolidado] = {}
    for colaborador, jornadas_do_colaborador in jornadas_por_colaborador.items():
        resumo = resumo_consolidado(jornadas_do_colaborador, catalogo)
        if resumo.quantidade_jornadas > 0:
            resultado[colaborador] = resumo
    return resultado


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
