# ADR-0033 | Reescrita dos gráficos (legenda inferior, sem título interno) e logo em vídeo na sidebar

## Contexto

Em 2026-07-31, após três rodadas de correções pontuais no mesmo dia
(ADR-0032: sobreposição título/legenda, corte de eixo X, legenda lateral
colidindo com o scatter, título duplicando o cabeçalho do expander), o
responsável do produto considerou o resultado "estranho" e pediu para
refazer os gráficos do zero, com uma regra única em vez de exceções por
gráfico:

> "Os gráficos estão estranhos, refaça do zero todos eles. Deixe em abas
> recolhíveis. Apenas as Abas deverão ter títulos (os Gráficos deverão
> ter apenas a legenda abaixo do gráfico) e todos os rótulos do eixo x e
> y aparecendo. Refaça todo o painel, acrescente o novo logo que está em
> formato mp4 [...] no side bar. Se for o caso veja o que foi feito no
> app.py da pasta Gestão_OS para utilizar como referência."

## Decisão

### 1. Referência confirmada em Gestão_OS - e por que não trocar de biblioteca

`Gestão_OS/app.py` usa `streamlit_echarts` (`st_echarts`, options em
dict cru), não `pyecharts`. Inspecionado: nenhuma das 20 chamadas
`st_echarts(...)` usa a chave `"title"` do ECharts (grep confirmou -
"title" só aparece em `gauge`/`toolbox`, nunca como componente de
título do gráfico); a legenda é sempre `"legend": {"bottom": ...}`.
Esse é exatamente o padrão pedido - confirma que "refazer do zero" é
alinhar com uma convenção já validada em produção, não inventar uma
nova.

Testado neste ambiente: `import streamlit_echarts` **ainda falha** com
o Streamlit 1.57 instalado aqui (`StreamlitAPIException: Component
'streamlit-echarts.streamlit_echarts' must be declared in
pyproject.toml with asset_dir...`) - a mesma incompatibilidade que
motivou a troca para `pyecharts` no ADR-0009 continua valendo. Decisão:
manter `pyecharts`, replicar a *convenção visual* de Gestão_OS
(sem título interno, legenda sempre embaixo) usando a API do pyecharts,
não trocar de biblioteca.

### 2. Regra única de layout (substitui as exceções do ADR-0032)

`painel/graficos.py` foi reescrito do zero. Em vez de decidir
título/legenda caso a caso (a fonte dos bugs do ADR-0032 - hora
escondia, hora mostrava, dependendo se o gráfico dividia o expander com
outro), toda função de gráfico agora segue **sem exceção**:

- `title_opts=_SEM_TITULO` (`opts.TitleOpts(is_show=False)`, constante
  única reaproveitada) - quem identifica o bloco é sempre o
  `st.expander(titulo, ...)` em `painel/telas/*.py`.
- `legend_opts=_legenda_inferior_opts()` - legenda sempre visível,
  horizontal, embaixo (`pos_bottom="1%"`, `pos_left="center"`),
  `type_="scroll"` pagina com setas se não couber numa linha. Única
  exceção: o gauge (`grafico_gauge_percentual`) não tem legenda -
  não é um gráfico categórico, não há o que legendar (mesmo motivo já
  documentado no ADR-0031 para o título).
- `_aplicar_grid()` com `is_contain_label=True` e margem inferior
  generosa o bastante pra caber rótulo de eixo rotacionado **e** a
  linha de legenda, sem os dois brigarem por espaço - cada gráfico
  ajusta o valor conforme o próprio rótulo (mais margem pra rótulo
  rotacionado longo, menos pra eixo sem rotação).
- Pizza/donut/sankey/sunburst deslocam `center` pra cima (ex.:
  `["50%", "42%"]` em vez de `["63%", "58%"]`) pra abrir espaço pra
  legenda embaixo, em vez da legenda lateral usada antes.

Quando dois gráficos dividem o mesmo `st.expander` (ex.: "Ranking por
duração e distribuição por sintoma", que tem o ranking **e** o donut de
sintoma), a diferenciação virou um `st.caption(...)` do Streamlit acima
de cada gráfico em `painel/telas/*.py` - texto fora do próprio ECharts,
então não viola "os Gráficos deverão ter apenas a legenda". Essa
resolução também segue o padrão de Gestão_OS, que usa `st.caption`/
`st.markdown("**...**")` fartamente acima de cada `st_echarts(...)`.

Efeito colateral positivo: mover a legenda do scatter "Duração média x
frequência por motivo" da lateral esquerda pra baixo **resolve de
graça** o bug do ADR-0032 (legenda larga com até 19 itens colidindo com
os pontos de frequência baixa) - uma legenda horizontal embaixo nunca
disputa espaço com a área de plotagem, ao contrário de uma legenda
vertical lateral. `_aplicar_grid(..., left="30%")`, a correção pontual
do ADR-0032 pra esse gráfico especificamente, foi removida - o
`left="3%"` default volta a valer em todo grafico, scatter incluso.

`grafico_donut_contagem(titulo, contagem)`: `titulo` deixou de virar
título do ECharts (não existe mais) e passou a ser o nome da série
(`.add(titulo, dados, ...)`) - aparece no tooltip padrão do ECharts
(`{a}`) ao passar o mouse, informação que antes só existia no título
fixo. Assinatura da função não mudou (mesmo parâmetro, só o uso interno
mudou) - nenhum teste ou chamador precisou ser alterado por causa disso.

`grafico_hh_por_motivo`, `grafico_ranking_duracao_falhas`,
`grafico_duracao_media_por_sintoma`, `grafico_reincidencia_ativos`:
o `altura_px` retornado continua sendo exatamente a altura usada no
`InitOpts` do próprio gráfico (contrato documentado desde o ADR-0031) -
descartada uma tentativa inicial de somar +40 ao valor retornado sem
mudar a altura real do gráfico, o que teria descasado os dois números.

### 3. Logo em vídeo na sidebar

`painel/app.py` ganhou um segundo elemento de identidade visual na
sidebar, abaixo do logo corporativo MRS (`st.logo`, que fica no slot
fixo do Streamlit, inalterado): o vídeo `Logo - SGO Workforce 1x1.mp4`
fornecido pelo responsável do produto, copiado para
`painel/assets/logo_sgo_workforce.mp4` (arquivo original na raiz do
repositório mantido intacto - só copiado, não movido).

`st.sidebar.video(caminho, loop=True, autoplay=True, muted=True,
width=180)` em vez de um `<video>` HTML cru embutido em base64 via
`st.markdown(unsafe_allow_html=True)`: decisão deliberada de
performance. O painel reexecuta o script inteiro a cada interação de
filtro (padrão de execução do Streamlit) - um `<video>` em base64
(~3.8MB codificado) seria reenviado por inteiro a cada rerun via
websocket, já que Streamlit não faz diff binário de conteúdo de
markdown. `st.video` serve o arquivo pelo endpoint de mídia dedicado do
Streamlit, cacheado normalmente pelo navegador via HTTP - só uma
referência pequena é reenviada a cada rerun, não os 2.8MB do vídeo.
Troca aceita: perde-se o controle fino sobre esconder a barra de
controles nativa do `<video>` do navegador (não há parâmetro
`controls` em `st.video` nesta versão do Streamlit), ganha-se
desempenho real numa tela com vários filtros interativos.

## Validação de qualidade realizada

- `python -m py_compile` em `painel/graficos.py`, `painel/telas/
  dashboard.py`, `painel/telas/falhas.py`, `painel/app.py`: OK.
- As 16 funções de gráfico renderizadas com dado realista (19
  categorias, nomes longos, 19 motivos) e inspecionadas via
  `dump_options()`: `title[0].show == False` em todas, `legend[0].show
  == True` e `legend[0].bottom == "1%"` em todas exceto o gauge
  (`False`, sem legenda), `grid.containLabel == True` em todo gráfico
  cartesiano (barra/linha/scatter). Sem exceção, sem caso especial.
- `pytest` completo: 299 passed, sem regressão (rodado de novo após a
  reescrita completa e de novo após os ajustes de `painel/telas/*.py`).
- Smoke test real do `painel/app.py`: `streamlit run` em background,
  `curl` na porta local devolveu HTTP 200, log do processo sem
  traceback/exceção - confirma que `st.sidebar.video(...)` e o resto do
  launcher executam sem erro em runtime (não só `py_compile`).

## Validação NÃO realizada

- Teste manual em navegador real (visual, não só HTTP 200) - mesma
  limitação de sempre, sandbox sem Playwright/Chromium instalado (ver
  ADR-0032). O smoke test HTTP confirma que o script roda sem exceção,
  não confirma a renderização visual pixel a pixel (legenda paginando
  corretamente, vídeo tocando em loop, etc.) - vale conferir no
  primeiro uso real.

## Arquivos afetados

- `painel/graficos.py` (reescrito por completo).
- `painel/telas/dashboard.py`, `painel/telas/falhas.py` (alturas de
  `components.html` ajustadas ao novo layout, `st.caption` adicionado
  onde dois gráficos dividem um expander).
- `painel/app.py` (logo em vídeo na sidebar).
- `painel/assets/logo_sgo_workforce.mp4` (novo).
