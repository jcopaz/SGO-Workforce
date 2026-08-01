"""Construcao dos graficos ECharts do painel (Incremento 9, expandido no
ADR-0031, ajustado no ADR-0032, reescrito do zero no ADR-0033 - sistema
de layout unico para todo grafico do painel).

Usa pyecharts (gera a option JSON do Apache ECharts em Python) em vez do
pacote streamlit-echarts original do Requirements.txt, que esta
incompativel com a versao do Streamlit disponivel neste ambiente - troca
documentada em docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md, a decisao
arquitetural posterior que a regra de ouro do CLAUDE.md permite. A mesma
incompatibilidade foi reconfirmada no ADR-0033 (streamlit_echarts, usado
no app.py de referencia de Gestao_OS, ainda quebra neste ambiente com o
Streamlit 1.57).

O grafico e renderizado para HTML autocontido, com o JS do ECharts
embutido inline (ver painel/assets/echarts.min.js) em vez de referenciar o
CDN publico do pyecharts - o painel gerencial nao deveria depender de
acesso externo so para desenhar um grafico.

Rotulos (Categoria, codigo de motivo) vem de `dados.rotulo_categoria`/
`dados.rotulo_motivo` - fonte unica compartilhada com os filtros das
telas (ver ADR-0031), nunca `categoria.value`/codigo cru direto num
grafico.

## Sistema de layout (ADR-0033)

Pedido explicito do responsavel do produto: "Apenas as Abas deverao ter
titulos (os Graficos deverao ter apenas a legenda abaixo do grafico) e
todos os rotulos do eixo x e y aparecendo" - referenciando o padrao ja
usado no app.py de Gestao_OS (`streamlit_echarts`, legenda sempre em
`bottom`, sem `title` no option). Regra unica, sem excecao por
contexto (ao contrario do ADR-0032, que so escondia titulo/legenda em
alguns casos - a fonte dos varios bugs de sobreposicao relatados):

- Todo grafico usa `_SEM_TITULO` (`title_opts` sempre oculto) - quem
  identifica o bloco e o `st.expander(titulo, ...)` em
  `painel/telas/*.py`, nunca o proprio ECharts.
- Todo grafico usa `_legenda_inferior_opts()` (legenda sempre visivel,
  horizontal, embaixo, com paginacao automatica se nao couber numa
  linha) - unica excecao e o gauge (`grafico_gauge_percentual`, nao e um
  grafico categorico, nao ha o que legendar).
- Todo grafico cartesiano (barra/linha/scatter) usa `_aplicar_grid()`
  com `is_contain_label=True` e margem generosa o bastante pra caber
  rotulo de eixo rotacionado + a linha de legenda embaixo, sem cortar
  nenhum dos dois.
- Pizza/donut/sankey/sunburst deslocam seu centro pra cima (`center`)
  pra abrir espaco pra legenda embaixo, em vez da legenda lateral usada
  antes do ADR-0033.

Quando dois graficos dividem o mesmo `st.expander` (ex.: ranking +
donut de sintoma em Falhas), a diferenciacao entre os dois vira um
`st.caption(...)` do Streamlit acima de cada grafico em
`painel/telas/*.py` - nunca um titulo dentro do proprio ECharts, que
violaria a regra acima.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pyecharts import options as opts
from pyecharts.charts import Bar, Funnel, Gauge, Line, Pie, Sankey, Scatter

from workforce_core.catalogo import Categoria
from workforce_core.consolidacao import LinhaAtendimentoFalha, LinhaEvento

from dados import rotulo_categoria, rotulo_motivo

_DIRETORIO_MODULO = Path(__file__).resolve().parent
CAMINHO_ECHARTS_JS_LOCAL = _DIRETORIO_MODULO / "assets" / "echarts.min.js"
_MARCADOR_SCRIPT_CDN = (
    '<script type="text/javascript" '
    'src="https://assets.pyecharts.org/assets/v6/echarts.min.js"></script>'
)


# Paleta do painel (ADR-0032) - alinhada as cores de marca ja usadas nos
# cards KPI (painel/estilo.py: kpi-border-blue/red/amber): azul para
# indicadores de produtividade (Visao Geral), vermelho para indicadores
# de alerta/severidade de falha, ambar para os demais indicadores de
# falha. Nunca uma cor arbitraria nova por grafico.
COR_PRODUTIVIDADE = "#2563EB"
COR_FALHA_INFO = "#F59E0B"
COR_FALHA_ALERTA = "#DC2626"

_COR_GRADE = "#E2E8F0"
_COR_EIXO = "#94A3B8"
_COR_TEXTO_EIXO = "#475569"

_ITEM_STYLE_BARRA_VERTICAL = opts.ItemStyleOpts(border_radius=[4, 4, 0, 0])
_ITEM_STYLE_BARRA_HORIZONTAL = opts.ItemStyleOpts(border_radius=[0, 4, 4, 0])

# Titulo sempre oculto (ADR-0033) - constante unica reaproveitada em todo
# grafico em vez de criar um `opts.TitleOpts(is_show=False)` novo a cada
# funcao.
_SEM_TITULO = opts.TitleOpts(is_show=False)


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


def _legenda_inferior_opts() -> opts.LegendOpts:
    """Legenda horizontal, sempre embaixo do grafico (ADR-0033) - unica
    posicao de legenda usada no painel inteiro, em vez de uma posicao
    diferente por tipo de grafico (lateral para pizza, superior para
    barra empilhada, oculta para serie unica) como era antes. `type_=
    "scroll"` faz a lista paginar com setas quando os itens nao cabem
    numa linha so, em vez de quebrar em varias linhas e crescer a altura
    do grafico de forma imprevisivel."""
    return opts.LegendOpts(
        type_="scroll",
        orient="horizontal",
        pos_bottom="1%",
        pos_left="center",
        item_width=14,
        item_height=10,
        textstyle_opts=opts.TextStyleOpts(font_size=11, color=_COR_TEXTO_EIXO),
    )


def _aplicar_grid(grafico, bottom: str = "20%", top: str = "6%", left: str = "3%"):
    """Aplica a area de plotagem (grid) com `is_contain_label=True`
    (ADR-0032/0033): pede ao ECharts para reservar de verdade o espaco
    ocupado pelos rotulos do eixo (numero de caracteres, rotacao, fonte)
    antes de posicionar a area de plotagem. Sem isso, rotulo rotacionado
    com nome longo (ex.: "Deslocamento rodoviario" a 35 graus) estoura a
    margem reservada e e cortado na borda do canvas em vez de aparecer
    inteiro - bug real relatado com dado real em 2026-07-31 no grafico
    HH por categoria.

    `bottom` default generoso o bastante pra caber rotulo de eixo
    rotacionado **e** a linha de legenda (ADR-0033: legenda agora sempre
    embaixo, ver `_legenda_inferior_opts`) sem os dois brigarem por
    espaco - cada grafico ajusta esse valor conforme o rotulo do seu
    eixo (mais margem pra rotulo rotacionado longo, menos pra eixo
    numerico ou categoria sem rotacao).

    Escrito direto em `grafico.options["grid"]` em vez de passado como
    `grid_opts` para `set_global_opts` porque o pyecharts 2.1 (versao
    instalada neste ambiente) removeu esse parametro da assinatura de
    `Chart.set_global_opts` - `grid` so e configuravel via o container
    composto `pyecharts.charts.Grid` nessa versao, que exigiria reescrever
    todo grafico como uma composicao de dois objetos so para ajustar
    margem. Escrever direto em `.options` e o mesmo mecanismo que o
    proprio pyecharts usa internamente para xAxis/yAxis (ver
    `RectChart.add_xaxis`) - `options` e um dict simples, vira o JSON do
    ECharts do jeito esperado."""
    grafico.options["grid"] = opts.GridOpts(
        is_contain_label=True, pos_top=top, pos_bottom=bottom, pos_left=left, pos_right="4%"
    ).opts
    return grafico


def _eixo_valor_opts(nome: str = "") -> opts.AxisOpts:
    """Eixo numerico com estilo consistente entre todos os graficos do
    painel (linha suave + grade tracejada clara) em vez do preto solido
    padrao do ECharts, que destoa do restante do card."""
    return opts.AxisOpts(
        name=nome,
        name_gap=18,
        axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=_COR_EIXO)),
        axislabel_opts=opts.LabelOpts(color=_COR_TEXTO_EIXO, font_size=11),
        splitline_opts=opts.SplitLineOpts(
            is_show=True, linestyle_opts=opts.LineStyleOpts(type_="dashed", color=_COR_GRADE)
        ),
    )


def _eixo_categoria_opts(rotate: int = 0) -> opts.AxisOpts:
    """Eixo de categoria (rotulo de texto) com mesmo estilo do eixo
    numerico - usado no eixo com os nomes (categoria/colaborador/data),
    rotacionado quando o rotulo e longo demais para caber na horizontal."""
    return opts.AxisOpts(
        axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=_COR_EIXO)),
        axislabel_opts=opts.LabelOpts(rotate=rotate, font_size=11, color=_COR_TEXTO_EIXO, margin=10),
    )


# ----------------------------------------------------------------------
# Visao geral - HH por categoria/colaborador/tempo (Incremento 9,
# corrigido e ampliado no ADR-0031, reescrito no ADR-0033)
# ----------------------------------------------------------------------
def grafico_hh_por_categoria(por_categoria: Dict[Optional[Categoria], timedelta]) -> Bar:
    itens = sorted(por_categoria.items(), key=lambda kv: kv[1], reverse=True)
    rotulos = [rotulo_categoria(c) for c, _ in itens]
    valores = [_horas(d) for _, d in itens]

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height="540px"))
        .add_xaxis(rotulos)
        .add_yaxis("HH (horas)", valores, color=COR_PRODUTIVIDADE, itemstyle_opts=_ITEM_STYLE_BARRA_VERTICAL)
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            xaxis_opts=_eixo_categoria_opts(rotate=35),
            yaxis_opts=_eixo_valor_opts("HH (horas)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        )
        .set_series_opts(label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10, color=_COR_TEXTO_EIXO))
    )
    return _aplicar_grid(grafico, bottom="34%")


def grafico_distribuicao_pizza(por_categoria: Dict[Optional[Categoria], timedelta]) -> Pie:
    dados = [(rotulo_categoria(c), _horas(d)) for c, d in por_categoria.items()]
    return (
        Pie(init_opts=opts.InitOpts(width="100%", height="520px"))
        .add("HH", dados, radius="55%", center=["50%", "42%"])
        .set_global_opts(title_opts=_SEM_TITULO, legend_opts=_legenda_inferior_opts())
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

    grafico = (
        Line(init_opts=opts.InitOpts(width="100%", height="440px"))
        .add_xaxis(rotulos)
        .add_yaxis(
            "HH (horas)",
            valores,
            is_smooth=True,
            symbol_size=7,
            linestyle_opts=opts.LineStyleOpts(width=3, color=COR_PRODUTIVIDADE),
            itemstyle_opts=opts.ItemStyleOpts(color=COR_PRODUTIVIDADE),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.12, color=COR_PRODUTIVIDADE),
            label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10, color=_COR_TEXTO_EIXO),
        )
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            xaxis_opts=_eixo_categoria_opts(rotate=30),
            yaxis_opts=_eixo_valor_opts("HH (horas)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        )
    )
    return _aplicar_grid(grafico, bottom="26%")


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

    grafico = Bar(init_opts=opts.InitOpts(width="100%", height="540px")).add_xaxis(colaboradores)
    for rotulo in rotulos_categoria:
        valores = [_horas(totais[rotulo].get(colaborador, timedelta())) for colaborador in colaboradores]
        grafico.add_yaxis(rotulo, valores, stack="total")
    grafico.set_global_opts(
        title_opts=_SEM_TITULO,
        tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        legend_opts=_legenda_inferior_opts(),
        xaxis_opts=_eixo_categoria_opts(rotate=20),
        yaxis_opts=_eixo_valor_opts("HH (horas)"),
    )
    return _aplicar_grid(grafico, bottom="24%", top="4%")


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
        .add_yaxis("HH (horas)", valores, color=COR_PRODUTIVIDADE, itemstyle_opts=_ITEM_STYLE_BARRA_HORIZONTAL)
        .reversal_axis()
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
            xaxis_opts=_eixo_valor_opts("HH (horas)"),
            yaxis_opts=_eixo_categoria_opts(),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right", color=_COR_TEXTO_EIXO, font_size=10))
    )
    grafico = _aplicar_grid(grafico, bottom="10%", top="4%")
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

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
        .add_xaxis(colaboradores)
        .add_yaxis(
            "Utilização HH (%)", percentuais, color=COR_PRODUTIVIDADE, itemstyle_opts=_ITEM_STYLE_BARRA_VERTICAL
        )
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            xaxis_opts=_eixo_categoria_opts(rotate=20),
            yaxis_opts=opts.AxisOpts(
                name="Utilização (%)",
                max_=100,
                name_gap=18,
                axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=_COR_EIXO)),
                axislabel_opts=opts.LabelOpts(color=_COR_TEXTO_EIXO, font_size=11),
                splitline_opts=opts.SplitLineOpts(
                    is_show=True, linestyle_opts=opts.LineStyleOpts(type_="dashed", color=_COR_GRADE)
                ),
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        )
        .set_series_opts(label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10, color=_COR_TEXTO_EIXO))
    )
    return _aplicar_grid(grafico, bottom="24%")


def grafico_scatter_duracao_frequencia(dados_por_motivo: Dict[str, Tuple[int, timedelta]]) -> Scatter:
    """Duração média x frequência por motivo (docs/12_DASHBOARDS_ECHARTS.md,
    "scatter para duração x frequência") - identifica motivos que são ao
    mesmo tempo frequentes e demorados (prioritários para investigar),
    sem misturar com os raros/curtos. Cada motivo vira sua própria série
    de 1 ponto (em vez de um único eixo categórico) para o tooltip padrão
    do ECharts mostrar o nome do motivo sem precisar de JS customizado.
    `dados_por_motivo` vem de `contagem_e_duracao_media_por_motivo`
    (painel/dados.py): motivo -> (frequência, duração média).

    ADR-0033: a legenda (um item por motivo, ate ~19) foi movida da
    lateral esquerda pra embaixo do grafico, junto com todo o resto do
    painel - isso tambem resolve, de graca, o bug do ADR-0032 (legenda
    lateral larga colidindo com os pontos de frequencia baixa perto do
    eixo Y): uma legenda horizontal embaixo, com paginacao automatica
    (`type_="scroll"`), nunca disputa espaco com a area de plotagem."""
    grafico = Scatter(init_opts=opts.InitOpts(width="100%", height="500px"))
    grafico.add_xaxis([])
    for motivo, (frequencia, duracao_media) in dados_por_motivo.items():
        grafico.add_yaxis(
            rotulo_motivo(motivo),
            [[frequencia, _horas(duracao_media)]],
            symbol_size=18,
            label_opts=opts.LabelOpts(is_show=False),
        )
    grafico.set_global_opts(
        title_opts=_SEM_TITULO,
        xaxis_opts=opts.AxisOpts(
            name="Frequência (nº de ocorrências)",
            type_="value",
            axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=_COR_EIXO)),
            axislabel_opts=opts.LabelOpts(color=_COR_TEXTO_EIXO, font_size=11),
            splitline_opts=opts.SplitLineOpts(
                is_show=True, linestyle_opts=opts.LineStyleOpts(type_="dashed", color=_COR_GRADE)
            ),
        ),
        yaxis_opts=_eixo_valor_opts("Duração média (horas)"),
        tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{a}<br/>Freq.: {c}", is_confine=True),
        legend_opts=_legenda_inferior_opts(),
    )
    return _aplicar_grid(grafico, bottom="16%", top="6%")


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

    grafico = Sankey(init_opts=opts.InitOpts(width="100%", height="600px"))
    grafico.add(
        "HH",
        nodes,
        links,
        pos_top="4%",
        pos_bottom="14%",
        linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
        label_opts=opts.LabelOpts(font_size=11, color=_COR_TEXTO_EIXO),
    )
    grafico.set_global_opts(
        title_opts=_SEM_TITULO,
        legend_opts=_legenda_inferior_opts(),
        tooltip_opts=opts.TooltipOpts(trigger="item", trigger_on="mousemove", is_confine=True),
    )
    return grafico


# ----------------------------------------------------------------------
# Falhas - tempo de atendimento e detalhamento (ADR-0029, ampliado no
# ADR-0031, reescrito no ADR-0033)
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
        .add_yaxis(
            "Duração (horas)", valores, color=COR_FALHA_ALERTA, itemstyle_opts=_ITEM_STYLE_BARRA_HORIZONTAL
        )
        .reversal_axis()
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
            xaxis_opts=_eixo_valor_opts("Duração (horas)"),
            yaxis_opts=_eixo_categoria_opts(),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right", color=_COR_TEXTO_EIXO, font_size=10))
    )
    grafico = _aplicar_grid(grafico, bottom="10%", top="4%")
    return grafico, altura_px


def grafico_donut_contagem(titulo: str, contagem: Dict[str, int]) -> Pie:
    """Donut genérico rótulo->contagem (ADR-0029) - usado para a
    distribuição de atendimentos de falha por sintoma/objeto. Diferente
    de grafico_distribuicao_pizza (que soma duração por Categoria), este
    soma contagem de ocorrências por um rótulo de texto livre.

    `titulo` (ADR-0033) não aparece mais como título dentro do ECharts
    (regra única do painel: só a aba tem título) - vira o nome da série,
    usado pelo tooltip padrão do ECharts (`{a}`) ao passar o mouse sobre
    uma fatia. Quem chama (`painel/telas/falhas.py`) usa `st.caption()`
    acima do gráfico para rotular visualmente, quando ele divide o
    expander com outro gráfico."""
    dados = sorted(contagem.items(), key=lambda item: item[1], reverse=True)
    return (
        Pie(init_opts=opts.InitOpts(width="100%", height="520px"))
        .add(titulo, dados, radius=["32%", "52%"], center=["50%", "42%"])
        .set_global_opts(title_opts=_SEM_TITULO, legend_opts=_legenda_inferior_opts())
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}", font_size=11))
    )


def grafico_gauge_percentual(titulo: str, fracao: float) -> Gauge:
    """Gauge 0-100% - tipo de grafico recomendado em
    docs/12_DASHBOARDS_ECHARTS.md para capacidade/utilizacao (ADR-0027,
    indicador de Utilizacao HH). `fracao` e um valor 0..1 (ex.: saida de
    workforce_core.consolidacao.utilizacao_hh) - a conversao para
    percentual e so de exibicao, feita aqui, nunca antes.

    Sem titulo interno nem legenda (ADR-0031/0033: nao e um grafico
    categorico, nao ha o que legendar, e o texto duplicava literalmente
    o titulo do card KPI do Streamlit logo acima) - so o mostrador com o
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
            itemstyle_opts=opts.ItemStyleOpts(color=COR_PRODUTIVIDADE),
        )
        .set_global_opts(title_opts=_SEM_TITULO, legend_opts=opts.LegendOpts(is_show=False))
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

    grafico = (
        Line(init_opts=opts.InitOpts(width="100%", height="440px"))
        .add_xaxis(rotulos)
        .add_yaxis(
            "Duração (horas)",
            valores,
            is_smooth=True,
            symbol_size=7,
            linestyle_opts=opts.LineStyleOpts(width=3, color=COR_FALHA_INFO),
            itemstyle_opts=opts.ItemStyleOpts(color=COR_FALHA_INFO),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.14, color=COR_FALHA_INFO),
            label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10, color=_COR_TEXTO_EIXO),
        )
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            xaxis_opts=_eixo_categoria_opts(rotate=30),
            yaxis_opts=_eixo_valor_opts("Duração (horas)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        )
    )
    return _aplicar_grid(grafico, bottom="26%")


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

    grafico = (
        Bar(init_opts=opts.InitOpts(width="100%", height="480px"))
        .add_xaxis(colaboradores)
        .add_yaxis("Duração (horas)", valores, color=COR_FALHA_INFO, itemstyle_opts=_ITEM_STYLE_BARRA_VERTICAL)
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            xaxis_opts=_eixo_categoria_opts(rotate=20),
            yaxis_opts=_eixo_valor_opts("Duração (horas)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
        )
        .set_series_opts(label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10, color=_COR_TEXTO_EIXO))
    )
    return _aplicar_grid(grafico, bottom="24%")


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
        .add_yaxis(
            "Duração média (horas)", valores, color=COR_FALHA_ALERTA, itemstyle_opts=_ITEM_STYLE_BARRA_HORIZONTAL
        )
        .reversal_axis()
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
            xaxis_opts=_eixo_valor_opts("Duração média (horas)"),
            yaxis_opts=_eixo_categoria_opts(),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right", color=_COR_TEXTO_EIXO, font_size=10))
    )
    grafico = _aplicar_grid(grafico, bottom="10%", top="4%")
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
        .add_yaxis("Atendimentos", quantidades, color=COR_FALHA_ALERTA, itemstyle_opts=_ITEM_STYLE_BARRA_HORIZONTAL)
        .reversal_axis()
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
            tooltip_opts=opts.TooltipOpts(trigger="axis", is_confine=True),
            xaxis_opts=_eixo_valor_opts("Atendimentos"),
            yaxis_opts=_eixo_categoria_opts(),
        )
        .set_series_opts(label_opts=opts.LabelOpts(position="right", color=_COR_TEXTO_EIXO, font_size=10))
    )
    grafico = _aplicar_grid(grafico, bottom="10%", top="4%")
    return grafico, altura_px


def grafico_funil_duracao_por_sintoma(agrupado: Dict[str, Dict[str, timedelta]]) -> Funnel:
    """Funil de duração total de atendimento por sintoma (ADR-0033) -
    substitui o sunburst ativo>sintoma do ADR-0031. O sunburst nao
    escalava com dado em volume: com o simulador ETL (10 ativos x 8
    sintomas = 80 fatias), nenhum ajuste de `minAngle`/fonte/raio deixou
    os rotulos legiveis de verdade - bug real relatado com captura de
    tela mesmo depois da primeira correcao. Pedido explicito do
    responsavel do produto: trocar por um funil.

    Funil e serie unica (uma lista ordenada de valores, nao uma
    hierarquia de 2 niveis) - por isso a dimensao "ativo" e colapsada
    aqui (soma-se a duracao de cada sintoma por cima de todos os
    ativos). Nao perde informacao relevante: "Ativos reincidentes" e a
    tabela "Ocorrencias por ativo" (mais abaixo na mesma tela) ja cobrem
    a dimensao ativo isoladamente. O funil ranqueado por sintoma
    responde uma pergunta que nenhum outro grafico de Falhas respondia
    ainda: "quais sintomas mais consomem HH de atendimento" (duracao
    total, nao so contagem de ocorrencias - essa ja e o donut
    'Ocorrencias por sintoma')."""
    total_por_sintoma: Dict[str, timedelta] = {}
    for por_sintoma in agrupado.values():
        for sintoma, duracao in por_sintoma.items():
            total_por_sintoma[sintoma] = total_por_sintoma.get(sintoma, timedelta()) + duracao

    dados = sorted(
        ((sintoma, _horas(duracao)) for sintoma, duracao in total_por_sintoma.items()),
        key=lambda item: item[1],
        reverse=True,
    )

    return (
        Funnel(init_opts=opts.InitOpts(width="100%", height="560px"))
        .add(
            "Duração (horas)",
            dados,
            sort_="descending",
            gap=2,
            label_opts=opts.LabelOpts(formatter="{b}: {c}h", font_size=11, color="#FFFFFF"),
            tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c}h", is_confine=True),
        )
        .set_global_opts(
            title_opts=_SEM_TITULO,
            legend_opts=_legenda_inferior_opts(),
        )
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
