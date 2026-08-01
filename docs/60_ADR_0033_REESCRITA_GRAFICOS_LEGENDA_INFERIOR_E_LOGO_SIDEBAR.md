# ADR-0033 | Reescrita dos gráficos (legenda inferior, sem título interno), logo em vídeo na sidebar e simulador ETL

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

### 4. Simulador ETL de dados em volume

Pedido do responsável do produto: "coloque um simulador de dados ETL
para ver como vai ficar os gráficos com uma maior quantidade de dados".
`gerar_jornadas_exemplo` (Incremento 9) já existia, mas gera só 3
jornadas fixas - não estressa legenda paginada, eixo com muitas
categorias, sankey/scatter com muitas séries. `painel/dados.py` ganhou
`gerar_jornadas_exemplo_volumoso(diretorio, quantidade_colaboradores,
dias, semente)`:

- Usa exatamente o mesmo motor de domínio (`MotorJornada`) que a
  interface de campo real - nenhum atalho que pule as regras do motor
  só por ser dado de teste (evento secundário sempre fora de atividade
  principal, pausa sempre dentro de atividade ativa, atendimento de
  falha com sua própria atividade). Cada jornada colaborador×dia sorteia
  1-3 eventos secundários, 0-2 pausas dentro da atividade principal, e
  ~18% de chance de um atendimento de falha (ativo/sintoma/objeto
  sorteados de pools fabricados em contexto ferroviário, sempre
  marcados "dado simulado" na observação).
- Só sorteia entre os ~19 códigos EE reais
  (`catalogo_relatorio_1_manutencao`), filtrando explicitamente por
  `codigo.startswith("EE")` - a primeira versão também sorteava os
  motivos legados de `catalogo_padrao()` (PAUSA_TESTE, REFEICAO, DDS,
  REUNIAO, TREINAMENTO), que têm `tipo_registro` "pausa" por padrão e
  duplicavam visualmente o mesmo motivo com dois códigos diferentes
  (ex.: "REFEICAO" e "EE02 - Refeição 1 hora" como barras separadas) -
  corrigido antes de expor a função.
- EE23 (Manutenção Programada Não Concluída) deliberadamente fora -
  fecha por um método diferente (`encerrar_atividade_nao_concluida`),
  caso raro sem valor extra pro objetivo (volume/variedade visual, não
  cobertura exaustiva do catálogo).
- `painel/telas/dashboard.py`: novo expander "Simulador de dados (ETL) -
  testar gráficos com volume maior", com `st.number_input` pra
  colaboradores/dias e um botão - ao lado do botão de dados de exemplo
  já existente, mesma aba "Arquivo local".

Bug real encontrado e corrigido durante a implementação:
`iniciar_atendimento_falha` abre sua própria atividade principal (não
aninha dentro da atividade EE17 já aberta) - a primeira versão tentava
abrir o atendimento de falha com a atividade EE17 ainda ativa e
disparava `AtividadeJaAtivaError` do motor. Corrigido encerrando a
atividade EE17 antes do bloco de falha condicional.

### 5. Dois bugs reais encontrados pelo próprio simulador ETL (mesmo dia)

O simulador cumpriu o que se propôs: gerando dado em volume de verdade
(10 ativos x 8 sintomas simulados), o responsável do produto reportou
(com captura de tela real) dois problemas que nenhum dos testes
anteriores (poucas categorias) tinha revelado:

- **Tooltip cortado na borda do iframe**: gráficos com `trigger="axis"`
  e muitas séries (ex.: "HH por colaborador", até ~19 categorias
  empilhadas) mostram um tooltip que lista o valor de cada série ao
  passar o mouse - com muitas séries esse tooltip fica alto o bastante
  pra estourar o topo do iframe do Streamlit
  (`components.html(..., scrolling=False)` não deixa o conteúdo
  extravasar), cortando as primeiras linhas em vez de reposicionar.
  Corrigido com `is_confine=True` em **todos os 13** `TooltipOpts` do
  módulo (não só no gráfico relatado - o mesmo risco existe em qualquer
  gráfico com tooltip de várias séries) - `confine` é a opção nativa do
  ECharts pra manter o tooltip sempre dentro da área do próprio
  gráfico, reposicionando em vez de cortar.
- **Sunburst "Falhas por ativo e sintoma" ilegível com volume real**:
  10 ativos x 8 sintomas = 80 fatias - cada uma fina demais pra caber o
  texto do rótulo, todas tentando mostrar ao mesmo tempo. Corrigido com
  `label.minAngle=8` (esconde rótulo de fatia com ângulo menor que 8°,
  mantém só os que cabem de verdade - o resto continua no tooltip ao
  passar o mouse) - opção nativa do ECharts não exposta como parâmetro
  nomeado por `opts.LabelOpts` do pyecharts, passada como dict puro
  (`.opts` + a chave extra) em vez do objeto `LabelOpts`. Radius e
  altura também aumentados (`"68%"` → `"70%"`, `600px` → `640px`) pra
  dar mais espaço aos rótulos que continuam visíveis.

### 6. Sunburst substituído por funil (mesmo dia)

O ajuste de `minAngle` da seção anterior não foi suficiente - o
responsável do produto relatou (nova captura de tela real, mesmo dado
de volume) que o sunburst continuava ilegível, e pediu diretamente a
troca por um gráfico de funil (referência visual anexada). Diferente
das correções anteriores desta ADR (todas preservaram o tipo de
gráfico), esta é uma troca de tipo genuína - o sunburst não escala bem
com muitas combinações ativo×sintoma independente de ajuste fino de
rótulo, e o pedido do responsável do produto foi direto.

`grafico_sunburst_ativo_sintoma` foi **substituído** por
`grafico_funil_duracao_por_sintoma` (`pyecharts.charts.Funnel`).
Diferença estrutural importante: funil é série única (uma lista
ordenada de valores), não uma hierarquia de 2 níveis - a dimensão
"ativo" é colapsada (soma-se a duração de cada sintoma por cima de
todos os ativos) antes de virar funil. Isso não perde informação
relevante: "Ativos reincidentes" e a tabela "Ocorrências por ativo"
(mais abaixo na mesma tela) já cobrem a dimensão ativo isoladamente. O
funil ranqueado por sintoma (maior duração total primeiro) responde uma
pergunta nova que nenhum gráfico de Falhas respondia ainda - "quais
sintomas mais consomem HH de atendimento" (duração, não só contagem de
ocorrências, que já é o donut "Ocorrências por sintoma" ao lado).

A assinatura de entrada não mudou (`Dict[ativo, Dict[sintoma,
timedelta]]`, mesmo `agrupar_atendimentos_ativo_sintoma` de
`painel/dados.py`) - só o que a função faz com o dado. O expander em
`painel/telas/falhas.py` foi renomeado de "Falhas por ativo e sintoma"
para "Duração de falhas por sintoma", com `st.caption` explicando a
diferença pro donut de contagem ao lado.

### 7. Rótulo (nome + valor) dentro da área colorida - funil, pizza e donut

Pedido explícito do responsável do produto: "coloque as legendas e os
valores dentro das cores" - referenciando a mesma imagem do funil que
motivou a seção 6, onde cada faixa colorida mostra nome+valor
centralizado, em vez de rótulo do lado de fora com linha apontando (o
padrão default do ECharts pra pizza/donut, e o que o funil também
usava antes deste ajuste).

- `grafico_funil_duracao_por_sintoma`: `label_opts` ganhou
  `position="inside"`.
- `grafico_distribuicao_pizza`, `grafico_donut_contagem`:
  `label_opts` ganhou `position="inside"` e cor branca (contraste sobre
  a fatia colorida, antes era a cor de texto padrão do eixo - clara
  demais e ilegível sobre cor saturada). `min_show_label_angle=8`
  (parâmetro nativo de `Pie.add()`, não precisa do truque de dict cru
  usado no sunburst) esconde o rótulo de fatia fina demais pro texto
  caber - mesmo raciocínio do `label.minAngle` do sunburst (seção 5),
  necessário porque esses dois gráficos também podem ter muitas
  categorias com o simulador ETL (até 19 na pizza "Distribuição de
  HH").

## Validação de qualidade realizada

- `python -m py_compile` em `painel/graficos.py`, `painel/telas/
  dashboard.py`, `painel/telas/falhas.py`, `painel/app.py`: OK.
- As 16 funções de gráfico renderizadas com dado realista (19
  categorias, nomes longos, 19 motivos) e inspecionadas via
  `dump_options()`: `title[0].show == False` em todas, `legend[0].show
  == True` e `legend[0].bottom == "1%"` em todas exceto o gauge
  (`False`, sem legenda), `grid.containLabel == True` em todo gráfico
  cartesiano (barra/linha/scatter). Sem exceção, sem caso especial.
- `pytest` completo: 300 passed, sem regressão (rodado de novo após a
  reescrita completa, de novo após os ajustes de `painel/telas/*.py`, e
  de novo após o simulador ETL).
- `gerar_jornadas_exemplo_volumoso` chamado direto (20 colaboradores, 30
  dias): 513-520 jornadas geradas (varia com a semente/aleatoriedade de
  "nem todo colaborador trabalha todo dia"), 0 `com_erro` ao recarregar,
  20 motivos EE distintos, 20 colaboradores distintos, ~90-99
  atendimentos de falha, 8 sintomas distintos - novo teste
  `test_gerar_jornadas_exemplo_volumoso_produz_dado_variado` cobre isso
  (`tests/test_painel.py`).
- Smoke test real do `painel/app.py`: `streamlit run` em background,
  `curl` na porta local devolveu HTTP 200, log do processo sem
  traceback/exceção - rodado três vezes (após o vídeo na sidebar, após o
  simulador ETL, e de novo após a troca sunburst→funil) - confirma que
  `st.sidebar.video(...)` e o resto do launcher executam sem erro em
  runtime (não só `py_compile`).
- `grafico_funil_duracao_por_sintoma` testado com dado de 2 ativos
  compartilhando o mesmo sintoma - confirma que a duração é somada
  entre ativos, não duplicada (`test_grafico_funil_duracao_por_sintoma_soma_entre_ativos`),
  e com o volume do simulador (10 ativos x 8 sintomas): itens do funil
  corretamente ordenados do maior pro menor via `dump_options()`.

## Validação NÃO realizada

- Teste manual em navegador real (visual, não só HTTP 200) - mesma
  limitação de sempre, sandbox sem Playwright/Chromium instalado (ver
  ADR-0032). O smoke test HTTP confirma que o script roda sem exceção,
  não confirma a renderização visual pixel a pixel (legenda paginando
  corretamente, vídeo tocando em loop, etc.) - vale conferir no
  primeiro uso real.

## Arquivos afetados

- `painel/graficos.py` (reescrito por completo).
- `painel/telas/dashboard.py` (alturas de `components.html` ajustadas ao
  novo layout, `st.caption` onde dois gráficos dividem um expander, novo
  expander do simulador ETL).
- `painel/telas/falhas.py` (alturas de `components.html` ajustadas,
  `st.caption` onde dois gráficos dividem um expander).
- `painel/app.py` (logo em vídeo na sidebar).
- `painel/assets/logo_sgo_workforce.mp4` (novo).
- `painel/dados.py` (`gerar_jornadas_exemplo_volumoso`, novo).
- `tests/test_painel.py` (novo teste do simulador ETL).
