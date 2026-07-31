# ADR-0032 | Revisão premium dos gráficos e abas recolhíveis no painel

## Contexto

Em 2026-07-31, após o dashboard completo do ADR-0031 ir ao ar, o
responsável do produto relatou (com capturas de tela reais, dados de
produção) um bug ainda não coberto: no gráfico "HH por categoria" (e,
por extensão, em vários outros), o rótulo do eixo X aparecia cortado na
base, e um texto de legenda aparecia desenhado por cima do título
("HH ▪por catategoria"). Pedido explícito: corrigir o eixo X, remover a
sobreposição título/legenda, agrupar cada bloco de gráficos (Visão Geral
e Falhas) numa aba recolhível, e fazer uma revisão geral de design em
todos os gráficos - "sem sobreposição de nada, visão clara e gráficos
compatíveis com as informações".

## Decisão

### 1. Causa raiz do novo bug de sobreposição título/legenda

O ADR-0031 introduziu `_legenda_lateral_opts`/`_legenda_superior_opts`
para os gráficos que já tinham `legend_opts` explícito (pizza/donut,
barra empilhada por colaborador) - mas **não** cobriu os gráficos de
série única, que nunca passavam `legend_opts` para `set_global_opts`.
Inspecionando `chart.dump_options()["legend"]` desses gráficos, o
pyecharts registra uma legenda mesmo sem `legend_opts` explícito (o
default do parâmetro é `LegendOpts()`, não `None`) - e sem posição
explícita, o ECharts nativo centraliza essa legenda no topo, exatamente
onde `_titulo_opts` também centraliza o título. Resultado: o nome da
série (`"HH (horas)"`) desenhado por cima do texto do título.

Correção: `_legenda_oculta_opts()` (`LegendOpts(is_show=False)`),
aplicada a todo gráfico de série única - a legenda só duplicaria o nome
da série, já visível no eixo/tooltip. Mesmo raciocínio já usado no gauge
de Utilização HH (ADR-0031), agora generalizado para 12 funções:
`grafico_hh_por_categoria`, `grafico_evolucao_diaria`,
`grafico_hh_por_motivo`, `grafico_utilizacao_por_colaborador`,
`grafico_sankey_colaborador_categoria`,
`grafico_ranking_duracao_falhas`, `grafico_evolucao_diaria_falhas`,
`grafico_hh_falhas_por_colaborador`, `grafico_duracao_media_por_sintoma`,
`grafico_reincidencia_ativos`, `grafico_sunburst_ativo_sintoma`,
`grafico_gauge_percentual`.

### 2. Causa raiz do corte no eixo X

Nenhum gráfico definia `containLabel` na área de plotagem (grid) -
sem isso, o ECharts reserva uma margem fixa (não proporcional ao
tamanho real do rótulo) para o eixo, e um rótulo rotacionado com nome
longo ("Deslocamento rodoviário" a 35°, 19 categorias reais) estoura
essa margem e é cortado na borda do canvas em vez de aparecer inteiro.

Correção: `_aplicar_grid(grafico, bottom, top)`, com
`is_contain_label=True` e margens generosas (até 28% no gráfico com
rótulos mais longos e mais rotacionados). **Detalhe de implementação
importante**: o pyecharts instalado neste ambiente é a versão 2.1.0, que
**removeu** o parâmetro `grid_opts` de `Chart.set_global_opts()`
(diferente da API clássica documentada em tutoriais/exemplos online, que
ainda é a 1.x/2.0) - `grid` só é configurável nessa versão via o
container composto `pyecharts.charts.Grid`, que exigiria reescrever cada
gráfico como uma composição de dois objetos só para ajustar margem.
`_aplicar_grid` escreve direto em `grafico.options["grid"]` - o mesmo
mecanismo que o próprio pyecharts usa internamente para popular
`xAxis`/`yAxis` (`RectChart.add_xaxis`), confirmado por inspeção do
código-fonte instalado (`pyecharts/charts/chart.py`).

### 3. Abas recolhíveis

Cada bloco de gráfico (subtítulo + gráfico(s) relacionados) em
`painel/telas/dashboard.py` e `painel/telas/falhas.py` passou a ficar
dentro de `st.expander(titulo, expanded=True)` em vez de
`st.subheader(titulo)` solto. `expanded=True` por padrão - nada fica
escondido até o usuário decidir recolher, só ganha a opção de recolher o
que não quer ver. Filtros, cartões de KPI e as tabelas brutas
("Jornadas carregadas", "Todos os atendimentos do período") continuam
fora de expander - não são "bloco de gráfico", são dado bruto/controle,
o pedido foi especificamente sobre gráficos.

Alturas dos `components.html(..., height=...)` de cada gráfico afetado
por `_aplicar_grid`/aumento de `InitOpts` foram ajustadas para manter
uma folga mínima acima da altura interna do gráfico (nunca exatamente
igual, para não arriscar corte de 1-2px em navegadores diferentes).

### 4. Revisão de design "premium"

Sem trocar nenhum tipo de gráfico (todos já eram adequados ao dado que
representam - revisado item a item, nenhuma substituição necessária).
Ajustes aplicados de forma consistente em todo `painel/graficos.py`:

- Paleta unificada (`COR_PRODUTIVIDADE`, `COR_FALHA_INFO`,
  `COR_FALHA_ALERTA`) alinhada às cores de marca já usadas nos cards KPI
  (`painel/estilo.py`), substituindo os hex ad-hoc (`#0f4c81`,
  `#f5c400`, `#b3261e`) espalhados pelo módulo.
- Eixos com estilo consistente (`_eixo_valor_opts`/`_eixo_categoria_opts`):
  linha e rótulo em cinza-azulado suave em vez do preto sólido padrão do
  ECharts, grade tracejada clara em vez de sólida.
- Nome no eixo de valor (`"HH (horas)"`, `"Duração (horas)"` etc.) nos
  gráficos que tiveram a legenda ocultada - a informação que a legenda
  antes carregava continua visível sem precisar do hover no tooltip.
- Cantos arredondados nas barras (`_ITEM_STYLE_BARRA_VERTICAL`/
  `_ITEM_STYLE_BARRA_HORIZONTAL`), área sob a linha nos gráficos de
  evolução diária (`AreaStyleOpts` com opacidade baixa) - toques visuais
  padrão de dashboard executivo, sem alterar dado nem interação.

### 5. Correção adicional - legenda lateral colidindo com o scatter (mesmo dia)

Após a primeira rodada desta ADR ir ao ar, o responsável do produto
relatou (nova captura de tela real) o gráfico "Duração média x
frequência por motivo" com a legenda lateral (um item por motivo, até
~19 itens, rótulo longo tipo "EE04 - Falta de ferramenta ou material")
desenhada por cima dos pontos de frequência baixa. Causa: `_aplicar_grid`
fixava a margem esquerda da área de plotagem em 2% para todo gráfico -
adequado para eixo de categoria comum, mas o scatter usa
`_legenda_lateral_opts()` (a mesma legenda vertical do pizza/donut), que
nos gráficos de pizza funciona porque o `center` do pizza já é deslocado
para a direita (`["63%", "58%"]`) para abrir espaço - o scatter não tinha
esse deslocamento equivalente na área de plotagem.

Correção: `_aplicar_grid` ganhou um parâmetro `left` (antes fixo em
"2%"), e `grafico_scatter_duracao_frequencia` passou a chamar
`_aplicar_grid(..., left="30%")` - espaço suficiente para o rótulo mais
longo da legenda em qualquer largura de coluna. Além disso, o gráfico
saiu da coluna de metade da tela (`st.columns(2)`, pareado com "Evolução
diária de HH" em `painel/telas/dashboard.py`) e ganhou expander próprio
em largura cheia - pedido explícito do responsável do produto ("ajuste
esse gráfico ou coloque ele separado"), e também reduz a chance de o
mesmo tipo de colisão voltar a aparecer com filtros que produzam ainda
mais motivos distintos.

### 6. Correção adicional - título do gráfico duplicando o cabeçalho do expander (mesmo dia)

Consequência direta da seção 3 (abas recolhíveis): agora que todo bloco
de gráfico tem um `st.expander(titulo, ...)` visível acima, o título
interno do próprio ECharts (`_titulo_opts`) - que antes era a única
pista visual do que o gráfico mostrava - passou a repetir o mesmo texto
duas vezes empilhado sempre que o gráfico é o único do bloco. Relatado
com captura de tela real no gráfico "HH por motivo/justificativa"
("retire o titulo do grafico já tem no topo do item").

`_titulo_opts` ganhou um parâmetro `mostrar: bool = True`, e as funções
de gráfico que às vezes ficam sozinhas num expander ganharam
`mostrar_titulo: bool = True` (repassado para `_titulo_opts`):
`grafico_evolucao_diaria`, `grafico_hh_por_colaborador`,
`grafico_hh_por_motivo`, `grafico_utilizacao_por_colaborador`,
`grafico_sankey_colaborador_categoria`, `grafico_scatter_duracao_frequencia`,
`grafico_donut_contagem`, `grafico_sunburst_ativo_sintoma`. `painel/telas/
dashboard.py` e `painel/telas/falhas.py` passam `mostrar_titulo=False`
exatamente nos expanders com **um único** gráfico (onde o cabeçalho do
expander já basta) - **não** nos expanders que dividem o bloco entre dois
gráficos lado a lado (ex.: "Ranking por duração e distribuição por
sintoma", que tem o ranking **e** o donut de sintoma no mesmo expander)
- ali o título interno continua a única forma de saber qual gráfico é
qual sem precisar ler o código-fonte. O default do parâmetro é `True`
(mostra o título) - é preciso decisão explícita do chamador pra
esconder, nunca o inverso.

## Validação de qualidade realizada

- `python -m py_compile` em `painel/graficos.py`,
  `painel/telas/dashboard.py`, `painel/telas/falhas.py`: OK.
- As 13 funções de gráfico com `_legenda_oculta_opts`/`_aplicar_grid`
  renderizadas num script isolado com dado multi-categoria realista (19
  categorias, nomes longos) e inspecionadas via `dump_options()`:
  confirmado `legend[0].show == False` nos gráficos de série única,
  `legend[0].show == True` nos multi-série (`hh_por_colaborador`,
  scatter), `grid.containLabel == True` e `xAxis.axisLabel.rotate == 35`
  no gráfico antes quebrado (`grafico_hh_por_categoria`).
- `pytest` completo (299 testes, incluindo os 36 de `test_painel.py`):
  100% verde, sem regressão.
- Toggle `mostrar_titulo=False` verificado nas 8 funções que o recebem
  (mais `grafico_hh_por_motivo`, que retorna tupla) via `dump_options()`
  - `title[0].show == False` confirmado em todas, `title[0].show == True`
  confirmado no caso default (`grafico_donut_contagem` sem o parâmetro,
  usado quando dois gráficos dividem o expander). `pytest` completo
  rodado de novo depois: 299 passed.

## Validação NÃO realizada

- Teste manual em navegador real - o sandbox Windows deste ambiente não
  tem Playwright/Chromium nem outra ferramenta de automação de navegador
  instalada, e instalar esse stack só para esta validação (download
  pesado de binário) não foi considerado proporcional ao escopo da
  sessão. Mesma limitação e mesmo critério já registrados no ADR-0031 -
  a correção foi validada por inspeção direta do JSON de opções que o
  ECharts de fato consome (mais preciso que uma captura de tela para
  confirmar `legend.show`/`grid.containLabel`, mas não substitui
  verificação de pixel real). Risco mitigado pela precisão desse método
  de verificação (a opção `legend.show=False` categoricamente não
  renderiza legenda; `containLabel=True` é o mecanismo documentado do
  próprio ECharts para não cortar rótulo de eixo), mas ainda vale
  confirmar em uso real assim que possível.

## Arquivos afetados

- `painel/graficos.py` (helpers de legenda/grid revisados, paleta
  unificada, `_aplicar_grid` novo por causa da mudança de API do
  pyecharts 2.1).
- `painel/telas/dashboard.py`, `painel/telas/falhas.py` (blocos de
  gráfico envolvidos em `st.expander`, alturas de `components.html`
  ajustadas).
