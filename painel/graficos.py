"""Construcao dos graficos ECharts do painel (Incremento 9, expandido no
ADR-0031 - dashboard completo de produtividade/execucao e detalhamento de
falhas).

Usa pyecharts (gera a option JSON do Apache ECharts em Python) em vez do
pacote streamlit-echarts original do Requirements.txt, que esta
incompativel com a versao do Streamlit disponivel neste ambiente - troca
documentada em docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md, a decisao
arquitetural posterior que a regra de ouro do CLAUDE.md permite.

O grafico e renderizado para HTML autocontido, com o JS do ECharts
embutido inline (ver painel/assets/echarts.min.js) em vez de referenciar o
CDN publico do pyecharts - o painel gerencial nao deveria depender de
acesso externo so para desenhar um grafico.

Rotulos (Categoria, codigo de motivo) vem de `dados.rotulo_categoria`/
`dados.rotulo_motivo` - fonte unica compartilhada com os filtros das
telas (ver ADR-0031), nunca `categoria.value`/codigo cru direto num
grafico.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pyecharts import options as opts
from pyecharts.charts import Bar, Gauge, Line, Pie, Sankey, Scatter, Sunburst

from workforce_core.catalogo import Categoria
from workforce_core.consolidacao import LinhaAtendimentoFalha, LinhaEvento

from dados import rotulo_categoria, rotulo_motivo

_DIRETORIO_MODULO = Path(__file__).resolve().parent
CAMINHO_ECHARTS_JS_LOCAL = _DIRETORIO_MODULO / "assets" / "echarts.min.js"
_MARCADOR_SCRIPT_CDN = (
    '<script type="text/javascript" '
    'src="https://assets.pyecharts.org/assets/v6/echarts.min.js"></script>'
)


def _horas(duracao: timedelta) -> float:
    return round(duracao.total_seconds() / 3600, 2)


def _altura_lista_px(quantidade_itens: int) -> int:
    """Altura em pixels proporcional ao numero de barras de um grafico
    horizontal (ranking) - listas maiores precisam de mais espaco vertical
    para nenhuma barra ficar espremida. Usada tanto no `InitOpts` do
    grafico quanto na altura do iframe do Streamlit
    (`components.html(..., height=...)`) que o exibe - as duas precisam
    bater, senao o conteudo excedente fica cortado (bug real relatado em
    2026-07-31: graficos com listas longas precisam de altura dinamica,
    nao um valor fixo pensado para poucos itens)."""
    return max(320, 40 * quantidade_itens + 100)


# ----------------------------------------------------------------------
# Layout compartilhado (ADR-0031): titulo e legenda com posicoes fixas
# que nunca se sobrepoem, mesmo com muitas categorias de nome longo - bug
# real relatado em 2026-07-31 (titulo e legenda desenhados um em cima do
# outro em varios graficos). Toda funcao de grafico com titulo/legenda
# usa um destes dois helpers em vez de deixar o pyecharts no padrao.
# ----------------------------------------------------------------------
def _titulo_opts(titulo: str) -> opts.TitleOpts:
    return opts.TitleOpts(title=titulo, pos_left="center", pos_top="0%")


def _legenda_lateral_opts() -> opts.LegendOpts:
    """Legenda vertical na lateral esquerda, comecando bem abaixo do
    titulo - para pizza/donut com muitas fatias."""
    return opts.LegendOpts(
        type_="scroll",
        orient="vertical",
        pos_left="1%",
        pos_top="16%",
        pos_bottom="2%",
        item_width=14,
        item_height=10,
        textstyle_opts=opts.TextStyleOpts(font_size=11),
    )


def _legenda_superior_opts() -> opts.LegendOpts:
    """Legenda horizontal, empurrada para baixo do titulo - para
    graficos de barra/linha com varias series (uma por categoria)."""
    return opts.LegendOpts(type_="scroll", pos_top="9%", textstyle_opts=opts.TextStyleOpts(font_size=11))


# ----------------------------------------------------------------------
# Visao geral - HH por categoria/colaborador/tempo (Incremento 9,
# corrigido e ampliado no ADR-0031)
# ----------------------------------------------------------------------
def grafico_hh_por_categoria(por_categoria: Dict[Optional[Categoria], timedelta]) -> Bar:
    itens = sorted(por_categoria.items(), key=lambda kv: kv[1], reverse=True)
    rotulos = [rotulo_categoria(c) for c, _ in itens]
    valores = [_horas(d) for _, d in itens]

    return (
        Bar(init_opts=opts.InitOpts(width="100%", height="460px"))
        .add_xaxis(rotulos)
        .add_yaxis("HH (horas)", valores)
        .set_global_opts(
            title_opts=_titulo_opts("HH por categoria"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=35, font_size=11)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_distribuicao_pizza(por_categoria: Dict[Optional[Categoria], timedelta]) -> Pie:
    dados = [(rotulo_categoria(c), _horas(d)) for c, d in por_categoria.items()]
    return (
        Pie(init_opts=opts.InitOpts(width="100%", height="480px"))
        .add("HH", dados, radius="60%", center=["63%", "58%"])
        .set_global_opts(title_opts=_titulo_opts("Distribuição de HH"), legend_opts=_legenda_lateral_opts())
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%", font_size=11))
    )


def grafico_evolucao_diaria(linhas: List[LinhaEvento]) -> Line:
    """Serie temporal de HH por dia - "tendencia" recomendada em
    docs/12_DASHBOARDS_ECHARTS.md, aba Distribuicao de HH."""
    totais_por_dia: Dict[date, timedelta] = {}
    for linha in linhas:
        totais_por_dia[linha.data] = totais_por_dia.get(linha.data, timedelta()) + linha.duracao

    dias_ordenados = sorted(totais_por_dia)
    rotulos = [dia.strftime("%d/%m/%Y") for dia in dias_ordenados]
    valores = [_horas(totais_por_dia[dia]) for dia in dias_ordenados]

    return (
        Line(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add_xaxis(rotulos)
        .add_yaxis("HH (horas)", valores, is_smooth=True)
        .set_global_opts(
            title_opts=_titulo_opts("Evolução diária de HH"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30, font_size=11)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_hh_por_colaborador(linhas: List[LinhaEvento]) -> Bar:
    """Barras empilhadas por colaborador x categoria - permite comparar
    colaboradores, nao so o total geral."""
    colaboradores = sorted({linha.colaborador_matricula for linha in linhas})
    categorias_presentes = sorted({linha.categoria for linha in linhas}, key=rotulo_categoria)
    rotulos_categoria = [rotulo_categoria(c) for c in categorias_presentes]

    totais: Dict[str, Dict[str, timedelta]] = {rotulo: {} for rotulo in rotulos_categoria}
    for linha in linhas:
        rotulo = rotulo_categoria(linha.categoria)
        totais[rotulo][linha.colaborador_matricula] = (
            totais[rotulo].get(linha.colaborador_matricula, timedelta()) + linha.duracao
        )

    grafico = Bar(init_opts=opts.InitOpts(width="100%", height="460px")).add_xaxis(colaboradores)
    for rotulo in rotulos_categoria:
        valores = [_horas(totais[rotulo].get(colaborador, timedelta())) for colaborador in colaboradores]
        grafico.add_yaxis(rotulo, valores, stack="total")
    grafico.set_global_opts(
        title_opts=_titulo_opts("HH por colaborador"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=_legenda_superior_opts(),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20, font_size=11)),
    )
    return grafico


def grafico_hh_por_motivo(linhas: List[LinhaEvento]) -> Tuple[Bar, int]:
    """Ranking horizontal de HH por motivo/justificativa (pausas e
    deslocamento/espera/apoio - atividades nao tem motivo, ver
    LinhaEvento), com rotulo descritivo ("EE07 - Reunião ou ADM") em vez
    do codigo cru. Substitui o treemap do Incremento 9 (ADR-0031): boxes
    pequenas cortavam o rotulo em "EE" ilegivel, e um treemap nao tem
    onde caber um rotulo longo - barra horizontal acomoda texto longo sem
    esse problema, mesmo padrao ja usado em grafico_ranking_duracao_falhas.

    Retorna (grafico, altura_px) - altura cresce com o numero de motivos
    distintos, quem chama deve usar o mesmo valor no iframe que exibe o
    grafico (ver _altura_lista_px)."""
    totais: Dict[str, timedelta] = {}
    for linha in linhas:
        if linha.motivo is None:
            continue
        totais[linha.motivo] = totais.get(linha.motivo, timedelta()) + linha.duracao

    itens = sorted(totais.items(), key=lambda item: item[1], reverse=True)
    itens = list(reversed(itens))  # maior fica no topo depois do reversal_axis
    rotulos = [rotulo_motivo(motivo) for motivo, _ in itens]
    valores = [_horas(duracao) for _, duracao in itens]
    altura_px = _altura_lista_px(len(itens))

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height=f"{altura_px}px"))
        .add_xaxis(rotulos)
        .add_yaxis("HH (horas)", valores, color="#0f4c81")
        .reversal_axis()
        .set_global_opts(
            title_opts=_titulo_opts("HH por motivo/justificativa"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=11)),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right"))
    )
    return grafico, altura_px


def grafico_utilizacao_por_colaborador(utilizacao_por_colaborador: Dict[str, Optional[float]]) -> Bar:
    """Utilizacao HH (ADR-0027) individual, ordenada do maior para o
    menor - "quem esta convertendo mais periodo de trabalho em manutencao
    rentavel", em vez de so o agregado do periodo inteiro."""
    itens = sorted(
        ((colaborador, fracao) for colaborador, fracao in utilizacao_por_colaborador.items() if fracao is not None),
        key=lambda item: item[1],
        reverse=True,
    )
    colaboradores = [colaborador for colaborador, _ in itens]
    percentuais = [round(fracao * 100, 1) for _, fracao in itens]

    return (
        Bar(init_opts=opts.InitOpts(width="100%", height="460px"))
        .add_xaxis(colaboradores)
        .add_yaxis("Utilização HH (%)", percentuais, color="#0f4c81")
        .set_global_opts(
            title_opts=_titulo_opts("Utilização HH por colaborador (rentável / total)"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20, font_size=11)),
            yaxis_opts=opts.AxisOpts(name="%", max_=100),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_scatter_duracao_frequencia(dados_por_motivo: Dict[str, Tuple[int, timedelta]]) -> Scatter:
    """Duração média x frequência por motivo (docs/12_DASHBOARDS_ECHARTS.md,
    "scatter para duração x frequência") - identifica motivos que são ao
    mesmo tempo frequentes e demorados (prioritários para investigar),
    sem misturar com os raros/curtos. Cada motivo vira sua própria série
    de 1 ponto (em vez de um único eixo categórico) para o tooltip padrão
    do ECharts mostrar o nome do motivo sem precisar de JS customizado.
    `dados_por_motivo` vem de `contagem_e_duracao_media_por_motivo`
    (painel/dados.py): motivo -> (frequência, duração média)."""
    grafico = Scatter(init_opts=opts.InitOpts(width="100%", height="480px"))
    grafico.add_xaxis([])
    for motivo, (frequencia, duracao_media) in dados_por_motivo.items():
        grafico.add_yaxis(
            rotulo_motivo(motivo),
            [[frequencia, _horas(duracao_media)]],
            symbol_size=18,
            label_opts=opts.LabelOpts(is_show=False),
        )
    grafico.set_global_opts(
        title_opts=_titulo_opts("Duração média x frequência por motivo"),
        xaxis_opts=opts.AxisOpts(name="Frequência (nº de ocorrências)", type_="value"),
        yaxis_opts=opts.AxisOpts(name="Duração média (horas)", type_="value"),
        tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{a}<br/>Freq.: {c}"),
        legend_opts=_legenda_lateral_opts(),
    )
    return grafico


def grafico_sankey_colaborador_categoria(linhas: List[LinhaEvento]) -> Sankey:
    """Fluxo de HH de colaborador para categoria (docs/12_DASHBOARDS_ECHARTS.md,
    "sankey da jornada") - versão "quem gastou tempo em quê", mais
    tratável que um sankey de sequência temporal de estados (que exigiria
    reconstruir a ordem cronológica dos eventos dentro de cada jornada,
    fora de escopo deste incremento)."""
    fluxo: Dict[Tuple[str, str], timedelta] = {}
    for linha in linhas:
        chave = (linha.colaborador_matricula, rotulo_categoria(linha.categoria))
        fluxo[chave] = fluxo.get(chave, timedelta()) + linha.duracao

    colaboradores = sorted({colaborador for colaborador, _categoria in fluxo})
    categorias = sorted({categoria for _colaborador, categoria in fluxo})
    nodes = [{"name": nome} for nome in [*colaboradores, *categorias]]
    links = [
        {"source": colaborador, "target": categoria, "value": _horas(duracao)}
        for (colaborador, categoria), duracao in fluxo.items()
        if duracao > timedelta()
    ]

    grafico = Sankey(init_opts=opts.InitOpts(width="100%", height="520px"))
    grafico.add(
        "HH",
        nodes,
        links,
        linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
        label_opts=opts.LabelOpts(font_size=11),
    )
    grafico.set_global_opts(title_opts=_titulo_opts("Fluxo de HH: colaborador → categoria"))
    return grafico


# ----------------------------------------------------------------------
# Falhas - tempo de atendimento e detalhamento (ADR-0029, ampliado no
# ADR-0031)
# ----------------------------------------------------------------------
def grafico_ranking_duracao_falhas(linhas: List[LinhaAtendimentoFalha], top_n: int = 15) -> Tuple[Bar, int]:
    """Ranking horizontal das N falhas de maior duração (ADR-0029),
    inspirado na visão de referência do responsável do produto - barra
    ordenada por duração decrescente, rótulo = sintoma + ativo. Duração em
    horas (`_horas`, mesmo arredondamento dos outros gráficos do painel).
    Limitado a `top_n` para não sobrecarregar o gráfico com centenas de
    barras - a tabela completa (fora deste gráfico) cobre o restante.

    Retorna (grafico, altura_px) - ver grafico_hh_por_motivo."""
    ordenadas = sorted(linhas, key=lambda linha: linha.duracao, reverse=True)[:top_n]
    # Barra horizontal (reversal_axis): a maior duração fica no topo, por
    # isso a lista é revertida antes de virar eixo Y do pyecharts.
    ordenadas = list(reversed(ordenadas))
    rotulos = [
        f"{linha.sintoma or 'Sem sintoma'} · {linha.ativo or 'Sem ativo'}" for linha in ordenadas
    ]
    valores = [_horas(linha.duracao) for linha in ordenadas]
    altura_px = _altura_lista_px(len(ordenadas))

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height=f"{altura_px}px"))
        .add_xaxis(rotulos)
        .add_yaxis("Duração (horas)", valores, color="#f5c400")
        .reversal_axis()
        .set_global_opts(
            title_opts=_titulo_opts(f"Top {len(ordenadas)} atendimentos por duração"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=11)),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right"))
    )
    return grafico, altura_px


def grafico_donut_contagem(titulo: str, contagem: Dict[str, int]) -> Pie:
    """Donut genérico rótulo->contagem (ADR-0029) - usado para a
    distribuição de atendimentos de falha por sintoma/objeto. Diferente
    de grafico_distribuicao_pizza (que soma duração por Categoria), este
    soma contagem de ocorrências por um rótulo de texto livre."""
    dados = sorted(contagem.items(), key=lambda item: item[1], reverse=True)
    return (
        Pie(init_opts=opts.InitOpts(width="100%", height="480px"))
        .add("Ocorrências", dados, radius=["38%", "62%"], center=["63%", "58%"])
        .set_global_opts(title_opts=_titulo_opts(titulo), legend_opts=_legenda_lateral_opts())
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}", font_size=11))
    )


def grafico_gauge_percentual(titulo: str, fracao: float) -> Gauge:
    """Gauge 0-100% - tipo de grafico recomendado em
    docs/12_DASHBOARDS_ECHARTS.md para capacidade/utilizacao (ADR-0027,
    indicador de Utilizacao HH). `fracao` e um valor 0..1 (ex.: saida de
    workforce_core.consolidacao.utilizacao_hh) - a conversao para
    percentual e so de exibicao, feita aqui, nunca antes.

    Sem titulo interno nem rotulo de nome (ADR-0031: o texto duplicava
    literalmente o titulo do card KPI do Streamlit logo acima, as duas
    strings idênticas se sobrepondo na tela) - só o mostrador com o
    percentual. O `titulo` continua descrevendo o indicador para quem
    chama (Streamlit exibe isso fora do gráfico)."""
    percentual = round(fracao * 100, 1)
    return (
        Gauge(init_opts=opts.InitOpts(width="100%", height="320px"))
        .add(
            "",
            [("", percentual)],
            min_=0,
            max_=100,
            title_label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(title_opts=opts.TitleOpts(is_show=False))
    )


def grafico_evolucao_diaria_falhas(linhas: List[LinhaAtendimentoFalha]) -> Line:
    """Serie temporal de duração total de atendimentos de falha por dia -
    mesmo padrão de grafico_evolucao_diaria, aplicado a falhas."""
    totais_por_dia: Dict[date, timedelta] = {}
    for linha in linhas:
        totais_por_dia[linha.data] = totais_por_dia.get(linha.data, timedelta()) + linha.duracao

    dias_ordenados = sorted(totais_por_dia)
    rotulos = [dia.strftime("%d/%m/%Y") for dia in dias_ordenados]
    valores = [_horas(totais_por_dia[dia]) for dia in dias_ordenados]

    return (
        Line(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add_xaxis(rotulos)
        .add_yaxis("Duração (horas)", valores, is_smooth=True, color="#f5c400")
        .set_global_opts(
            title_opts=_titulo_opts("Evolução diária de atendimentos de falha"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30, font_size=11)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_hh_falhas_por_colaborador(linhas: List[LinhaAtendimentoFalha]) -> Bar:
    """Duração total de atendimento de falha por colaborador - "quem
    atende mais falhas e por quanto tempo", ordenado do maior para o
    menor."""
    totais: Dict[str, timedelta] = {}
    for linha in linhas:
        totais[linha.colaborador_matricula] = totais.get(linha.colaborador_matricula, timedelta()) + linha.duracao

    itens = sorted(totais.items(), key=lambda item: item[1], reverse=True)
    colaboradores = [colaborador for colaborador, _ in itens]
    valores = [_horas(duracao) for _, duracao in itens]

    return (
        Bar(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add_xaxis(colaboradores)
        .add_yaxis("Duração (horas)", valores, color="#f5c400")
        .set_global_opts(
            title_opts=_titulo_opts("HH de atendimento de falha por colaborador"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20, font_size=11)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_duracao_media_por_sintoma(duracao_media: Dict[str, timedelta]) -> Tuple[Bar, int]:
    """Duração média de atendimento por sintoma - "quais sintomas
    tipicamente demoram mais para resolver", distinto do ranking de
    piores ocorrências individuais (que mostra só o pior caso).

    Retorna (grafico, altura_px) - ver grafico_hh_por_motivo."""
    itens = sorted(duracao_media.items(), key=lambda item: item[1], reverse=True)
    itens = list(reversed(itens))
    rotulos = [sintoma for sintoma, _ in itens]
    valores = [_horas(duracao) for _, duracao in itens]
    altura_px = _altura_lista_px(len(itens))

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height=f"{altura_px}px"))
        .add_xaxis(rotulos)
        .add_yaxis("Duração média (horas)", valores, color="#b3261e")
        .reversal_axis()
        .set_global_opts(
            title_opts=_titulo_opts("Duração média por sintoma"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=11)),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right"))
    )
    return grafico, altura_px


def grafico_reincidencia_ativos(reincidentes: Dict[str, int]) -> Tuple[Bar, int]:
    """Ativos com mais de um atendimento de falha no período (ver
    workforce_core.consolidacao.ativos_reincidentes) - "quais
    equipamentos falham repetidamente", ordenado do mais reincidente
    para o menos.

    Retorna (grafico, altura_px) - ver grafico_hh_por_motivo."""
    itens = sorted(reincidentes.items(), key=lambda item: item[1], reverse=True)
    itens = list(reversed(itens))
    ativos = [ativo for ativo, _ in itens]
    quantidades = [quantidade for _, quantidade in itens]
    altura_px = _altura_lista_px(len(itens))

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height=f"{altura_px}px"))
        .add_xaxis(ativos)
        .add_yaxis("Atendimentos", quantidades, color="#b3261e")
        .reversal_axis()
        .set_global_opts(
            title_opts=_titulo_opts("Ativos reincidentes (mais de 1 atendimento)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=11)),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right"))
    )
    return grafico, altura_px


def grafico_sunburst_ativo_sintoma(agrupado: Dict[str, Dict[str, timedelta]]) -> Sunburst:
    """Hierarquia ativo > sintoma por duração (docs/12_DASHBOARDS_ECHARTS.md
    recomenda sunburst "sistema > ativo > sintoma" - o nível "sistema" não
    é capturado em `DadosFalha` hoje, então este sunburst cobre só os dois
    níveis com dado real: ativo e sintoma. Ver ADR-0031."""
    dados = [
        {
            "name": ativo,
            "children": [
                {"name": sintoma, "value": _horas(duracao)} for sintoma, duracao in por_sintoma.items()
            ],
        }
        for ativo, por_sintoma in agrupado.items()
    ]

    return (
        Sunburst(init_opts=opts.InitOpts(width="100%", height="520px"))
        .add(
            "Falhas",
            dados,
            radius=[0, "90%"],
            label_opts=opts.LabelOpts(font_size=11),
        )
        .set_global_opts(title_opts=_titulo_opts("Falhas por ativo e sintoma"))
    )


_js_echarts_em_cache: Optional[str] = None


def _ler_js_echarts_local() -> str:
    """Le echarts.min.js uma unica vez por processo (cache em memoria).

    ADR-0031: com o dashboard ampliado, uma unica tela pode renderizar
    uma dezena de graficos - reler um arquivo de 1MB+ do disco a cada
    grafico (o que este modulo fazia desde o Incremento 9) virou um
    gargalo real e mensuravel (uma bateria de testes que deveria durar
    segundos passou de vinte minutos por causa disso, mesmo sintoma que
    afetaria o Streamlit real a cada rerun). O conteudo do arquivo nunca
    muda durante a vida do processo, entao cache-lo em memoria e seguro."""
    global _js_echarts_em_cache
    if _js_echarts_em_cache is None:
        _js_echarts_em_cache = CAMINHO_ECHARTS_JS_LOCAL.read_text(encoding="utf-8")
    return _js_echarts_em_cache


def renderizar_embutido(grafico) -> str:
    """Renderiza um grafico pyecharts para HTML autocontido, sem depender de CDN.

    Falha explicitamente se o JS local nao estiver presente, em vez de
    deixar passar silenciosamente a tag <script src="cdn..."> sem
    integrity/crossorigin que o pyecharts gera por padrao (fail closed,
    CLAUDE.md regra de ouro 9).
    """
    if not CAMINHO_ECHARTS_JS_LOCAL.exists():
        raise FileNotFoundError(
            f"echarts.min.js nao encontrado em {CAMINHO_ECHARTS_JS_LOCAL}. "
            "Baixe o arquivo localmente antes de renderizar - o painel nao "
            "deve depender de um <script> de CDN sem integrity/crossorigin."
        )
    html = grafico.render_embed()
    if _MARCADOR_SCRIPT_CDN not in html:
        raise RuntimeError(
            "A tag <script> de CDN esperada nao foi encontrada no HTML gerado "
            "pelo pyecharts (o template pode ter mudado em uma atualizacao de "
            "versao). Recusando renderizar para nao deixar passar uma "
            "dependencia de CDN sem integrity/crossorigin sem querer."
        )
    js_conteudo = _ler_js_echarts_local()
    return html.replace(_MARCADOR_SCRIPT_CDN, f"<script>{js_conteudo}</script>")
