# ADR-0031 | Dashboard completo de produtividade/execução e detalhamento de falhas

## Contexto

Em 2026-07-31, testando o painel publicado no Streamlit Cloud com dados
reais, o responsável do produto relatou capturas de tela mostrando
gráficos genuinamente quebrados: título e legenda desenhados um em cima
do outro (pizza "Distribuição de HH", donut "Ocorrências por sintoma"),
o gauge de Utilização HH com o mesmo texto duplicado se sobrepondo, o
treemap "HH por motivo/justificativa" com caixas pequenas cortando o
rótulo em "EE" ilegível, e rótulos de categoria em código cru
(`ATIVIDADE_PLANEJADA`, `DESLOCAMENTO_A_PE`) em vez de texto legível.
Pedido explícito: corrigir os gráficos, garantir rótulos descritivos, e
"explorar a biblioteca ECharts" para construir um dashboard completo de
produtividade/execução na Visão Geral e um dashboard completo de
detalhamento na aba Falhas (ADR-0029).

## Decisão

### 1. Causa raiz dos bugs visuais e correção sistemática

Título (`title_opts`) e legenda (`legend_opts`) do pyecharts, sem
posição explícita, competem pelo canto superior-esquerdo por padrão -
com muitas categorias de nome longo (12+ na Visão Geral real), a legenda
quebra em várias linhas e cobre o título. `painel/graficos.py` ganhou
dois helpers de posicionamento fixo, usados em todo gráfico com
título/legenda:

- `_titulo_opts(titulo)`: título sempre centralizado, topo (`pos_top="0%"`).
- `_legenda_lateral_opts()`: legenda vertical na lateral esquerda,
  começando a 16% do topo (bem abaixo do título) - para pizza/donut.
- `_legenda_superior_opts()`: legenda horizontal empurrada a 9% do topo -
  para barra/linha com várias séries.

Gráficos de pizza/donut também tiveram o `center` deslocado
(`["6x%", "58%"]`) para abrir espaço à legenda na lateral esquerda.

O **gauge** (Utilização HH) tinha o texto do indicador duplicado: o
`title_opts` do gráfico e o "title" interno da série do ECharts (nome do
ponto de dado) mostravam o mesmo texto longo um sobre o outro. Os dois
foram ocultados (`is_show=False`) - o card KPI do Streamlit acima do
gráfico já mostra o título, o gauge só precisa do mostrador e do
percentual.

O **treemap** "HH por motivo/justificativa" foi **substituído por uma
barra horizontal** (`grafico_hh_por_motivo`, mesmo padrão já usado em
`grafico_ranking_duracao_falhas` desde o ADR-0029): treemap não tem
onde caber um rótulo longo numa caixa pequena, e o pedido do responsável
do produto era justamente rótulo mais descritivo, não mais compacto.
Barra horizontal com rótulo "EE07 - Reunião ou ADM" resolve os dois
problemas (rótulo completo sempre legível, sem sobreposição).

Gráficos de barra horizontal com número variável de itens
(`grafico_hh_por_motivo`, `grafico_duracao_media_por_sintoma`,
`grafico_reincidencia_ativos`, `grafico_ranking_duracao_falhas`) agora
retornam `(grafico, altura_px)` em vez de só o gráfico - a altura do
gráfico cresce com a quantidade de itens (`_altura_lista_px`), e quem
chama (`painel/telas/*.py`) precisa usar a mesma altura no
`components.html(..., height=...)` do Streamlit, senão o conteúdo extra
fica cortado dentro do iframe.

### 2. Rótulos legíveis - fonte única

`painel/dados.py` ganhou `ROTULOS_CATEGORIA` (dicionário com as 28
categorias de `workforce_core.catalogo.Categoria`, cada uma com um texto
em português) e `rotulo_categoria()`/`rotulo_motivo()` - usados tanto
pelos filtros das telas (`painel/telas/dashboard.py`) quanto pelos
gráficos (`painel/graficos.py`), para o rótulo de um multiselect e o de
uma legenda nunca divergirem. `rotulo_motivo(codigo)` busca a descrição
no catálogo dinâmico e formata `"EE07 - Reunião ou ADM"` (mesmo formato
já usado nos seletores da interface de campo, familiar para a operação);
cai no próprio código se não encontrado no catálogo, nunca quebra.

Os textos de `ROTULOS_CATEGORIA` são apresentação (texto livre em
português), não dado de negócio - não precisam de validação do
responsável do produto, diferente de uma reclassificação de
`ClassificacaoHH` (ADR-0028) ou de catálogo.

### 3. Indicadores novos - Visão Geral

Todos construídos sobre agregações já existentes em
`workforce_core.consolidacao`/`painel/dados.py`, sem nenhum dado
fabricado:

- **Utilização HH por colaborador** (`grafico_utilizacao_por_colaborador`):
  nova `resumo_consolidado_por_colaborador` (consolidacao.py) agrupa
  jornadas por matrícula antes de calcular `ResumoConsolidado` - permite
  comparar quem está convertendo mais período de trabalho em manutenção
  rentável, não só o agregado do período inteiro.
- **Duração média x frequência por motivo** (`grafico_scatter_duracao_frequencia`,
  scatter - recomendado em `docs/12_DASHBOARDS_ECHARTS.md`): identifica
  motivos frequentes *e* demorados, prioritários para investigar. Cada
  motivo vira sua própria série de 1 ponto (em vez de um eixo categórico
  único) para o tooltip padrão do ECharts mostrar o nome do motivo sem
  precisar de JS customizado (`JsCode`) - risco deliberadamente evitado.
- **Fluxo de HH: colaborador → categoria** (`grafico_sankey_colaborador_categoria`,
  sankey - recomendado em `docs/12`): versão "quem gastou tempo em quê",
  mais tratável que um sankey de sequência temporal de estados (exigiria
  reconstruir a ordem cronológica dos eventos dentro de cada jornada,
  fora de escopo).

### 4. Indicadores novos - Falhas

`src/workforce_core/consolidacao.py` ganhou `contagem_por_objeto`,
`duracao_media_por_sintoma`, `ativos_reincidentes` (mais de 1
atendimento - piso 2, definição, não limiar de negócio inventado) e
`agrupar_ativo_sintoma`. Telas:

- **Distribuição por objeto** (componente causador) - mesmo
  `grafico_donut_contagem` genérico já usado para sintoma.
- **Evolução diária de atendimentos** e **HH por colaborador** - mesmo
  padrão de série temporal/barra já usado na Visão Geral, aplicado a
  `LinhaAtendimentoFalha`.
- **Duração média por sintoma**: distinto do ranking por duração (que só
  mostra o pior caso individual) - mostra a tendência por tipo de falha.
- **Reincidência de ativos**: só aparece quando há pelo menos um ativo
  com mais de 1 atendimento no período filtrado (nunca um gráfico vazio
  fingindo que há dado).
- **Falhas por ativo e sintoma** (`grafico_sunburst_ativo_sintoma`,
  sunburst): `docs/12` recomenda um sunburst de 3 níveis
  "sistema > ativo > sintoma", mas `DadosFalha` não captura "sistema"
  hoje - o sunburst construído cobre só os dois níveis com dado real
  (ativo, sintoma). Causa, ação e sistema continuam sem tela - mostrar
  essas dimensões exigiria inventar dado, deliberadamente não feito.

### 5. Correção de performance real (JS local recarregado a cada gráfico)

`renderizar_embutido` relia `echarts.min.js` (1MB+) do disco a cada
gráfico desde o Incremento 9 - com poucos gráficos por tela isso nunca
foi perceptível, mas com o dashboard ampliado (uma tela chega a
renderizar mais de 10 gráficos) virou um gargalo real e mensurável
durante a validação deste ADR (uma bateria de testes que deveria durar
segundos chegou a 14 minutos). `_ler_js_echarts_local()` agora cacheia o
conteúdo em memória por processo (o arquivo nunca muda durante a vida do
processo) - mesma correção beneficia o Streamlit real, não só os testes.

## Deliberadamente fora deste incremento

- Heatmap dia x hora (recomendado em `docs/12`): exigiria hora do dia por
  evento, e `LinhaEvento`/`LinhaAtendimentoFalha` hoje só carregam a
  data, não o horário - extensão de domínio maior, fora de escopo desta
  sessão.
- Causa, ação e sistema em qualquer gráfico de Falhas - não capturados
  por `DadosFalha`/interface de campo hoje (ver também ADR-0029).
- Meta/limiar de "boa" Utilização HH (individual ou agregada) - decisão
  de negócio do responsável do produto, não inferida.
- Teste manual em navegador real (mesma limitação de sempre).

## Arquivos afetados

- `src/workforce_core/consolidacao.py` (novas agregações de falhas +
  `resumo_consolidado_por_colaborador`).
- `painel/dados.py` (rótulos legíveis, wrappers das novas agregações).
- `painel/graficos.py` (reescrito - correções de layout + gráficos novos
  + cache do JS local).
- `painel/telas/dashboard.py`, `painel/telas/falhas.py` (novas seções).
- `docs/12_DASHBOARDS_ECHARTS.md`.
- `tests/test_consolidacao.py`, `tests/test_painel.py`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- Todas as 16 funções de gráfico (existentes + novas) renderizadas num
  script isolado com dados multi-categoria realistas (12 categorias),
  confirmando ausência de exceção e inspecionando o JSON de opções
  gerado (`chart.dump_options()`) para confirmar que título/legenda
  ficam em posições não sobrepostas (`title.top="0%"` vs.
  `legend.top="16%"`) e que o gauge não duplica mais texto
  (`title.show=False`, `series.title.show=False`).
- `pytest` (`tests/test_consolidacao.py`, `tests/test_painel.py`): ver
  CHANGELOG para a contagem exata.

## Validação NÃO realizada

- Teste manual em navegador/celular real - mesma limitação de sempre.
  Como o bug relatado nesta sessão só apareceu com dado real em produção
  (nunca visível nos smoke tests anteriores, que usavam poucas
  categorias), este risco continua concreto: a correção foi validada por
  inspeção do JSON de opções gerado, não por renderização visual real.
