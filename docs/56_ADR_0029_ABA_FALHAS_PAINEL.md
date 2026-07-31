# ADR-0029 | Aba "Falhas" no painel (tempo de atendimento)

## Contexto

`docs/11_TELAS_E_UX.md` já listava "Falhas/RASF" como uma das abas do
painel desde o início do projeto, e `docs/12_DASHBOARDS_ECHARTS.md`
detalhava o que ela deveria mostrar ("Top sintomas, causas, ações,
sistemas, componentes, impacto, reincidência e HH consumido") — mas
nenhuma das duas nunca foi construída (o painel só tinha Visão Geral,
Mapa Operacional, Capacidade PCM, Exportações e Configurações).

Em 2026-07-31 o responsável do produto pediu explicitamente uma aba para
"ver uma visão do tempo de atendimento de falha", com uma captura de
tela de referência de outro painel operacional da MRS (ocorrências
ferroviárias): KPIs (total de ocorrências, tempo médio, maior duração,
duração total), uma tabela/ranking de ocorrências ordenada por duração
com barra visual embutida, um donut de distribuição por motivo, e uma
tabela de contagem por local.

## Decisão

### 1. Adaptação dos campos, não cópia literal do layout

A referência usa conceitos ferroviários que o Workforce não modela
(`Pátio Início/Fim`, "Motivo Ocorrência Operação Ferroviário"). O dado
real disponível é `DadosFalha` (`nota`, `ativo`, `sintoma`, `objeto`,
`observacao`, ver ADR-0021) preenchido pela interface de campo. Mapeamento
adotado:

| Referência | Workforce |
|---|---|
| Descrição Motivo Ocorrência | `sintoma` (catálogo RASF) |
| Nome Pátio Início (contagem) | `ativo` (equipamento) — não existe conceito de pátio no Workforce |
| Duração da ocorrência | `Atividade.fim - Atividade.inicio` (bruta, não líquida) |

### 2. Duração bruta, não líquida

`workforce_core/consolidacao.py::linhas_atendimento_falha` usa
`calculo.duracao_atividade_bruta` (tempo total decorrido do início ao
encerramento), diferente de `linhas_eventos_classificadas` (que usa
duração líquida, descontando pausas, para fins de HH do colaborador).
Aqui o interesse é "quanto tempo a falha ficou em aberto" — inclui
qualquer pausa que tenha ocorrido durante o atendimento, igual ao
conceito de "duração da ocorrência" da referência.

### 3. Inclui jornadas ainda abertas (desvio deliberado do padrão existente)

Diferente de `linhas_eventos_classificadas`/`resumo_consolidado` (que só
processam jornadas com `estado == ENCERRADA`),
`linhas_atendimento_falha` inclui qualquer atendimento de falha já
concluído (`Atividade.fim` preenchido), mesmo que a jornada em si ainda
esteja aberta. Uma falha resolvida às 10h deve aparecer no painel na
hora, não só depois que o colaborador encerrar o turno à noite — decisão
deliberada para uma visão operacional de falhas, documentada
explicitamente no docstring da função para não ser confundida com um
descuido.

### 4. Novo módulo de domínio, gráficos e tela

- `src/workforce_core/consolidacao.py`: `LinhaAtendimentoFalha`,
  `linhas_atendimento_falha`, `ResumoAtendimentosFalha`,
  `resumo_atendimentos_falha` (quantidade/total/média/maior duração, sem
  ZeroDivisionError em lista vazia), `contagem_por_sintoma`,
  `contagem_por_ativo` (ausência de dado vira rótulo explícito "Sem
  sintoma/ativo informado", nunca descartada).
- `painel/dados.py`: wrappers finos (`montar_linhas_atendimento_falha`,
  `resumo_atendimentos_falha_do_periodo`,
  `contagem_atendimentos_por_sintoma/ativo`) — mesma separação já
  existente entre `workforce_core` (domínio, testável sem Streamlit) e
  `painel/dados.py` (camada fina de conveniência para as telas).
- `painel/graficos.py`: `grafico_ranking_duracao_falhas` (barra
  horizontal, top 15 por duração, tipo de gráfico já recomendado em
  `docs/12` para "duração x frequência"), `grafico_donut_contagem`
  (rosca genérica rótulo→contagem, mesmo visual da referência).
- `painel/telas/falhas.py`: nova tela — mesmo padrão de fonte de
  dados/filtros de `dashboard.py` (chaves de sessão de fonte de
  dados/diretório/API **compartilhadas** com a Visão Geral, para o
  gestor não reconfigurar em cada aba; chaves de filtro
  colaborador/período **próprias** desta aba, porque o conjunto relevante
  de colaboradores/datas pode divergir do conjunto geral de jornadas).
  KPIs, ranking, donut, tabela de contagem por ativo e tabela completa
  (drill-down, regra de "Reconciliabilidade" de `docs/12`).
- `painel/app.py`: nova entrada de navegação "Falhas" em "Análise de
  Dados", entre "Visão geral" e "Mapa Operacional".

### 5. Formato de duração consistente com o resto do painel

A referência mistura formatos ("05:58", "23h 44min", "1264:07"). Optado
por usar `formatar_horas` (`"XhYY"`) em todos os cards desta aba, o mesmo
formato já usado em toda a Visão Geral — consistência interna do
Workforce teve prioridade sobre replicar pixel a pixel o formato da
referência externa.

## Deliberadamente fora deste incremento

- Causa, ação, sistemas, componentes causadores, impacto e reincidência
  (as demais dimensões listadas em `docs/12` para a aba "Falhas") — o
  pedido desta sessão foi especificamente "tempo de atendimento"; as
  demais dimensões existem em `DadosFalha`/catálogo RASF e podem virar
  gráficos adicionais na mesma aba se pedido.
- Filtro por sintoma/ativo dentro da própria aba de Falhas (só
  colaborador/período, mesmo padrão da Visão Geral) — próximo passo
  natural se a lista de atendimentos crescer o suficiente para precisar.
- Exibição da foto do atendimento (`foto_caminho`) nesta aba — já
  registrado como pendência antiga em `docs/23_DECISOES_PENDENTES.md`
  item 8 ("exibição da foto no painel ainda não existe").

## Arquivos afetados

- `src/workforce_core/consolidacao.py`.
- `painel/dados.py`, `painel/graficos.py`, `painel/telas/falhas.py` (novo), `painel/app.py`.
- `docs/11_TELAS_E_UX.md`, `docs/12_DASHBOARDS_ECHARTS.md`.
- `tests/test_consolidacao.py`, `tests/test_falhas_painel.py` (novo).

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 275/275 (era 265 antes deste ADR).
- **Primeira vez que uma tela do painel é testada de ponta a ponta**
  (`tests/test_falhas_painel.py`, via `streamlit.testing.v1.AppTest`) —
  roda o script real (`painel/telas/falhas.py`) num runtime Streamlit
  "bare mode" e confirma zero exceções, tanto com dados de exemplo quanto
  com diretório vazio. Todas as telas anteriores só testavam
  `dados.py`/`graficos.py` isoladamente (ver ADR-0009); esta é a primeira
  vez que o script inteiro (import, ordem de widgets, session_state) é
  exercitado sem depender de navegador real.

## Validação NÃO realizada

- Teste manual em navegador/celular real (mesma limitação de sempre).
- Nenhuma validação com a operação de quais dimensões (sintoma, ativo,
  causa etc.) são realmente as mais importantes para o gestor — a
  escolha de "ranking por duração + distribuição por sintoma + contagem
  por ativo" seguiu a referência fornecida, não uma decisão validada de
  indicadores oficiais.

## Data e responsáveis

- Data de registro: 2026-07-31.
- Registrado por: Claude Code, a pedido de j.copaz@hotmail.com, com uma
  captura de tela de referência de outro painel operacional da MRS.
