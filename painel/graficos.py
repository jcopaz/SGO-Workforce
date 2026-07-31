"""Construcao dos graficos ECharts do painel (Incremento 9).

Usa pyecharts (gera a option JSON do Apache ECharts em Python) em vez do
pacote streamlit-echarts original do Requirements.txt, que esta
incompativel com a versao do Streamlit disponivel neste ambiente - troca
documentada em docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md, a decisao
arquitetural posterior que a regra de ouro do CLAUDE.md permite.

O grafico e renderizado para HTML autocontido, com o JS do ECharts
embutido inline (ver painel/assets/echarts.min.js) em vez de referenciar o
CDN publico do pyecharts - o painel gerencial nao deveria depender de
acesso externo so para desenhar um grafico.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from pyecharts import options as opts
from pyecharts.charts import Bar, Gauge, Line, Pie, TreeMap

from workforce_core.catalogo import Categoria
from workforce_core.consolidacao import LinhaEvento

_DIRETORIO_MODULO = Path(__file__).resolve().parent
CAMINHO_ECHARTS_JS_LOCAL = _DIRETORIO_MODULO / "assets" / "echarts.min.js"
_MARCADOR_SCRIPT_CDN = (
    '<script type="text/javascript" '
    'src="https://assets.pyecharts.org/assets/v6/echarts.min.js"></script>'
)


def _rotulo_categoria(categoria: Optional[Categoria]) -> str:
    return categoria.value if categoria is not None else "SEM_CATEGORIA"


def _horas(duracao: timedelta) -> float:
    return round(duracao.total_seconds() / 3600, 2)


def grafico_hh_por_categoria(por_categoria: Dict[Optional[Categoria], timedelta]) -> Bar:
    itens = sorted(por_categoria.items(), key=lambda kv: kv[1], reverse=True)
    rotulos = [_rotulo_categoria(c) for c, _ in itens]
    valores = [_horas(d) for _, d in itens]

    return (
        Bar(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add_xaxis(rotulos)
        .add_yaxis("HH (horas)", valores)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="HH por categoria"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_distribuicao_pizza(por_categoria: Dict[Optional[Categoria], timedelta]) -> Pie:
    dados = [(_rotulo_categoria(c), _horas(d)) for c, d in por_categoria.items()]
    return (
        Pie(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add("HH", dados)
        .set_global_opts(title_opts=opts.TitleOpts(title="Distribuicao de HH"))
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
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
            title_opts=opts.TitleOpts(title="Evolucao diaria de HH"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )


def grafico_hh_por_colaborador(linhas: List[LinhaEvento]) -> Bar:
    """Barras empilhadas por colaborador x categoria - permite comparar
    colaboradores, nao so o total geral."""
    colaboradores = sorted({linha.colaborador_matricula for linha in linhas})
    categorias = sorted({_rotulo_categoria(linha.categoria) for linha in linhas})

    totais: Dict[str, Dict[str, timedelta]] = {categoria: {} for categoria in categorias}
    for linha in linhas:
        rotulo = _rotulo_categoria(linha.categoria)
        totais[rotulo][linha.colaborador_matricula] = (
            totais[rotulo].get(linha.colaborador_matricula, timedelta()) + linha.duracao
        )

    grafico = Bar(init_opts=opts.InitOpts(width="100%", height="420px")).add_xaxis(colaboradores)
    for categoria in categorias:
        valores = [_horas(totais[categoria].get(colaborador, timedelta())) for colaborador in colaboradores]
        grafico.add_yaxis(categoria, valores, stack="total")
    grafico.set_global_opts(
        title_opts=opts.TitleOpts(title="HH por colaborador"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(type_="scroll"),
    )
    return grafico


def grafico_motivos_treemap(linhas: List[LinhaEvento]) -> TreeMap:
    """Treemap de HH por motivo/justificativa (pausas e deslocamento/espera/
    apoio - atividades nao tem motivo, ver LinhaEvento)."""
    totais: Dict[str, timedelta] = {}
    for linha in linhas:
        if linha.motivo is None:
            continue
        totais[linha.motivo] = totais.get(linha.motivo, timedelta()) + linha.duracao

    dados = [
        {"name": motivo, "value": _horas(duracao)}
        for motivo, duracao in sorted(totais.items(), key=lambda item: item[1], reverse=True)
    ]

    return (
        TreeMap(init_opts=opts.InitOpts(width="100%", height="420px"))
        .add("HH por motivo", dados)
        .set_global_opts(title_opts=opts.TitleOpts(title="HH por motivo/justificativa"))
    )


def grafico_gauge_percentual(titulo: str, fracao: float) -> Gauge:
    """Gauge 0-100% - tipo de grafico recomendado em
    docs/12_DASHBOARDS_ECHARTS.md para capacidade/utilizacao (ADR-0027,
    indicador de Utilizacao HH). `fracao` e um valor 0..1 (ex.: saida de
    workforce_core.consolidacao.utilizacao_hh) - a conversao para
    percentual e so de exibicao, feita aqui, nunca antes."""
    percentual = round(fracao * 100, 1)
    return (
        Gauge(init_opts=opts.InitOpts(width="100%", height="320px"))
        .add(titulo, [(titulo, percentual)], min_=0, max_=100)
        .set_global_opts(title_opts=opts.TitleOpts(title=titulo))
    )


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
    js_conteudo = CAMINHO_ECHARTS_JS_LOCAL.read_text(encoding="utf-8")
    return html.replace(_MARCADOR_SCRIPT_CDN, f"<script>{js_conteudo}</script>")
