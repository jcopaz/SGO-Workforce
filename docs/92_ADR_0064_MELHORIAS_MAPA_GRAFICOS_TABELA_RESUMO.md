# ADR-0064 | Melhorias de mapa, gráficos e tabela resumo do mapa operacional

## Contexto

Pedido original do responsável pelo produto (mesma mensagem de
2026-08-07 que abriu a integração com o SGO): padronizar paleta de
cores em todos os gráficos, mostrar a atividade/evento no popup do
mapa (não só a qualidade), mostrar o código dentro de cada barra da
linha do tempo com legenda, usar o scroll do ECharts para zoom, e criar
uma tabela resumo (Atividade/Evento, Data/Hora Início, Data/Hora
Término, Localização Início/Encerramento) abaixo do mapa e do gráfico.
Sequenciado como micro-sessão própria, depois da integração de
login/SSO com o SGO (ADR-0062) e da aba Equipe (ADR-0063), a pedido
explícito do responsável do produto ("pode seguir com as pendências").

## Decisões

### 1. Popup do mapa mostra a atividade/evento (`painel/mapa.py`)

`_popup_pulso` ganhou um parâmetro `rotulo: Optional[str]`, exibido como
primeira linha ("Atividade/Evento: ...") quando informado.
`construir_mapa` ganhou `rotulo_por_pulso: Optional[Dict[UUID, str]]`
(mesmo formato de `cor_por_pulso`, já existente). `mapa_operacional.py`
já calculava `rotulos_por_pulso` (usado pro filtro de atividade e pra
colorir) - só faltava chegar até o popup.

### 2. Paleta de cores padronizada (`painel/graficos.py`)

`grafico_distribuicao_pizza` (pizza por Categoria) e
`grafico_hh_por_colaborador` (barra empilhada por colaborador x
Categoria) passam a usar `cor_por_rotulo` (já usado pelo mapa e pela
linha do tempo) em vez da paleta automática do pyecharts - mesma
categoria = mesma cor em qualquer gráfico do painel e no mapa.
`opts.PieItem` (com `itemstyle_opts` por fatia) substitui o par
nome/valor cru na pizza - é a única forma do pyecharts 2.1 aceitar cor
por fatia individual.

**Fora de escopo, deliberadamente**: `grafico_hh_por_categoria`,
`grafico_utilizacao_por_colaborador` e os indicadores de falha
(`COR_FALHA_INFO`/`COR_FALHA_ALERTA`) continuam com cor única fixa - são
indicadores de KPI (ADR-0032: azul=produtividade, vermelho=alerta,
âmbar=falha), não uma quebra por categoria/motivo que precise bater com
o mapa. Os gráficos de sintoma/objeto (RASF) também ficam de fora - são
um espaço de rótulos completamente diferente do usado no mapa
(sintomas, não códigos EE), então padronizar a cor ali não criaria a
consistência visual pedida.

### 3. Código + legenda + zoom por scroll na linha do tempo (`painel/graficos.py`)

- **Código dentro do segmento**: `_codigo_do_segmento(tipo, motivo)` -
  para PAUSA/EVENTO_SECUNDARIO usa o prefixo do `motivo` (ex.: "EE07");
  ATIVIDADE/ATENDIMENTO_FALHA não têm `motivo` na classificação (só
  PAUSA/EVENTO_SECUNDARIO têm), então usam os códigos fixos já
  documentados em `interface_campo/js/app.js`
  (`VALOR_INICIAR_ATIVIDADE`/`VALOR_ATENDIMENTO_FALHA`): EE17 e EE21.
  Só aparece dentro do segmento quando a duração é ≥ 30 min (limiar
  visual, evita texto cortado/ilegível em segmentos curtos).
- **Legenda**: a legenda nativa do ECharts continua desligada (as
  séries do gráfico são sintéticas por posição - `_pos_0`, `_pos_1`... -
  não por código; uma legenda presa a nome de série mostraria isso sem
  sentido nenhum, ver docstring de `grafico_linha_do_tempo`). Nova
  função `legenda_linha_do_tempo(por_dia, catalogo)` devolve os rótulos
  distintos do dia com sua cor (`cor_por_rotulo`) - `mapa_operacional.py`
  renderiza isso como uma legenda HTML simples (chips coloridos) abaixo
  do gráfico.
- **Zoom por scroll**: `datazoom_opts=[opts.DataZoomOpts(type_="inside",
  orient="vertical", ...)]` no eixo Y (hora do dia) - zoom por
  roda do mouse/pinça no celular, sem barra deslizante visível ocupando
  espaço extra no layout (diferente de `type_="slider"`).

### 4. Tabela resumo (`painel/mapa.py` + `painel/telas/mapa_operacional.py`)

Nova função `resumo_jornada_com_localizacao(jornada, pulsos, catalogo)`:
uma linha por intervalo real da jornada (`workforce_core.consolidacao.linha_do_tempo`
- não fatiado por dia, a jornada inteira), com o pulso mais próximo do
timestamp de início e do timestamp de fim de cada intervalo. "Sem
atividade" (lacuna) fica fora - não é algo que o colaborador fez, não
tem o que reportar de localização.

Como GPS é obrigatório em toda transição (ADR-0043/0048), o pulso mais
próximo do início/fim de um intervalo tende a ser exatamente o pulso
capturado naquela transição - não é uma estimativa vaga, é a mesma
leitura que travou a transição.

`mapa_operacional.py` renderiza isso via `st.dataframe`, colunas
Atividade/Evento, Data/Hora Início, Data/Hora Término e "Localização
Início/Encerramento" (uma única coluna com as duas localizações, pedido
explícito do responsável do produto: `"Início: lat,lon (hora) → Fim:
lat,lon (hora)"`). Usa a **jornada inteira e os pulsos completos** (não
`pulsos_filtrados`/`data_filtro` do mapa) - mesmo espírito da linha do
tempo, que também sempre mostra o dia/jornada inteira, independente do
filtro do mapa.

## Validação de qualidade realizada

- `python -m py_compile` em todos os arquivos tocados: OK.
- `pytest` completo: 435 passed (16 testes novos: 2 popup do mapa, 2
  consistência de cor, 7 código/legenda/zoom da linha do tempo, 4
  `resumo_jornada_com_localizacao`, 1 AppTest da tabela na tela).

## Validação NÃO realizada

- Conferência visual real (`streamlit run`) - este ambiente não tem
  navegador disponível; validado só por teste automatizado (estrutura
  do JSON de opções do ECharts, HTML renderizado, AppTest). Vale
  conferir visualmente antes de considerar concluído de verdade.

## Arquivos afetados

- `painel/mapa.py` (`_popup_pulso`, `construir_mapa`,
  `resumo_jornada_com_localizacao`, `LinhaResumoJornada`,
  `_pulso_mais_proximo`).
- `painel/graficos.py` (`grafico_distribuicao_pizza`,
  `grafico_hh_por_colaborador`, `grafico_linha_do_tempo`,
  `_codigo_do_segmento`, `legenda_linha_do_tempo`).
- `painel/telas/mapa_operacional.py` (repassa `rotulo_por_pulso`,
  renderiza a legenda HTML e a tabela resumo).
- `tests/test_mapa.py`, `tests/test_painel.py`,
  `tests/test_linha_do_tempo.py`, `tests/test_mapa_operacional_painel.py`
  (testes novos).

## Data e responsáveis

- Data de registro: 2026-08-07.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
