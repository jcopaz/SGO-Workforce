# ADR-0027 | Indicadores de Utilização HH e Performance

## Contexto

O responsável pelo produto forneceu, em 2026-07-30, duas fórmulas de
indicador que devem passar a fazer parte do vocabulário do SGO Workforce:

> Utilização HH: Horas Produtivas / Horas Totais — quanto do período de
> trabalho do colaborador ele consegue converter em manutenção
> executável.
>
> Performance: Tempo Planejado / Tempo Real — quão aderente o
> colaborador estava em relação ao tempo planejado de execução da(s)
> atividade(s).

`docs/12_DASHBOARDS_ECHARTS.md` já antecipava os dois conceitos antes
mesmo de existir código para eles ("comparação planejado x realizado" na
aba Distribuição de HH, "capacidade efetiva e utilização do plano" na aba
Capacidade, "gauge para capacidade/utilização" nos gráficos
recomendados) — este ADR é a primeira implementação real.

### O que já existia para viabilizar Utilização HH

`ClassificacaoHH` (`PRODUTIVA`/`IMPRODUTIVA`/`NAO_COMPUTAVEL`/
`NAO_DEFINIDO`) já existe desde o Incremento 5 e já está **validada
código a código** para os 23 códigos reais do Relatório 1
(`docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md`). Ou seja,
"Horas Produtivas" já é um conceito calculável com o catálogo real, sem
nenhuma decisão de negócio nova. Faltava apenas agregar HH por
`ClassificacaoHH` (o motor já agregava por `Categoria`, um recorte
diferente) e a divisão em si.

### O que NÃO existia para Performance

"Tempo Planejado" não é modelado em nenhum lugar do sistema — nem `OS`
(`workforce_core/entities.py::OrdemServico`, ADR-0025, é só um número em
texto livre) nem `Atividade` têm uma duração estimada. Isso já era uma
lacuna conhecida: `docs/23_DECISOES_PENDENTES.md` não tinha esse item
listado explicitamente até este ADR. Inventar uma fonte de tempo
planejado (ex.: uma média histórica, um valor fixo por tipo de atividade)
violaria a regra de ouro nº 3 do `CLAUDE.md` em espírito — nenhum número
usado num indicador deve ser fabricado sem memória de cálculo validada
pelo responsável do produto.

## Decisão

### 1. Utilização HH — implementada e exibida no painel

- `src/workforce_core/consolidacao.py`:
  - `resumo_por_classificacao_hh(jornada, catalogo)`: mesma estrutura de
    `resumo_por_categoria`, mas agrega por `ClassificacaoHH` em vez de
    `Categoria`. Pausas/eventos secundários usam a `classificacao_hh` do
    motivo no catálogo (`catalogo.obter(motivo)`); atividades não têm
    `motivo` (são tipadas por `Categoria` via `_categoria_atividade`), então
    usam a `classificacao_hh` da entrada do catálogo cuja `categoria` bate
    com a `Categoria` derivada — única correspondência automática
    permitida, mesma fonte de verdade do catálogo, nada reclassificado por
    fora dele.
  - `ResumoConsolidado` ganha o campo `por_classificacao_hh: Dict[ClassificacaoHH,
    timedelta]`, populado em `resumo_consolidado()` do mesmo jeito que
    `por_categoria`.
  - `utilizacao_hh(horas_produtivas, horas_totais) -> Optional[float]`:
    função pura, sem nenhuma fonte de dado embutida (mesmo princípio de
    `taxa_qualidade_pulsos`) — quem chama decide o numerador/denominador.
    Retorna `None` quando `horas_totais` é zero, nunca
    `ZeroDivisionError`.
- `painel/dados.py`: `utilizacao_hh_do_resumo(resumo)` — conveniência que
  usa `por_classificacao_hh[PRODUTIVA]` e `jornada_bruta_total` de um
  `ResumoConsolidado` já calculado (a mesma fonte que o resto do painel
  já usa, para o número nunca divergir de HH bruto/classificado exibidos
  ao lado).
- `painel/graficos.py`: `grafico_gauge_percentual(titulo, fracao)` — o
  tipo de gráfico "gauge" já recomendado em `docs/12` para
  capacidade/utilização, ainda não usado em nenhuma tela até este ADR.
- `painel/telas/dashboard.py`: novo card KPI "Utilização HH" (5ª coluna,
  ao lado dos 4 já existentes) e um gauge na nova seção "Indicadores",
  calculados a partir do mesmo `resumo` (jornada+período filtrados) já
  usado pelos outros cards — nenhuma consulta nova, nenhum dado
  duplicado.

### 2. Performance — fórmula pronta, sem fonte de "tempo planejado" (deliberadamente não exibida)

- `src/workforce_core/consolidacao.py::performance(tempo_planejado,
  tempo_real) -> Optional[float]`: implementa a fórmula exata fornecida
  pelo responsável do produto, pura, sem nenhuma fonte de tempo planejado
  embutida. Fica pronta para o dia em que essa fonte existir (ex.: tempo
  planejado por OS vindo do SGO na Fase 5 de integração).
- **Deliberadamente não conectada a nenhuma tela**: mostrar Performance
  hoje exigiria inventar um "tempo planejado" (ex.: média histórica,
  valor fixo por categoria) sem validação do responsável do produto — a
  regra de ouro nº 3 do `CLAUDE.md` ("não calcule duração pelo relógio
  visual do cliente... calcule por timestamps persistidos") e o espírito
  geral de "nada fabricado sem memória de cálculo" se aplicam aqui por
  analogia. O painel mostra um aviso explícito no lugar do indicador,
  citando a decisão pendente, em vez de simplesmente omitir o assunto.
- `docs/23_DECISOES_PENDENTES.md`: novo item 14, "Fonte de tempo
  planejado por atividade/OS para o indicador de Performance" — decisão
  de negócio explicitamente pendente, não inventada.

## Deliberadamente fora deste incremento

- Nenhuma meta/limiar de "boa" ou "má" Utilização HH (ex.: colorir o
  card de verde/vermelho acima/abaixo de X%) — não é uma decisão técnica,
  é uma meta operacional que só o responsável do produto pode validar.
- Utilização HH por colaborador individual (só o agregado do filtro
  atual, igual aos outros 4 cards) — decisão de UX de detalhamento fica
  para quando houver pedido explícito.
- Qualquer alteração em `Capacidade PCM` (`workforce_core/pcm.py`) — o
  responsável do produto já decidiu que PCM não é mais prioridade de
  evolução (`docs/23_DECISOES_PENDENTES.md`, item 5); esses indicadores
  não tocam esse módulo.
- Exportações (CSV/XLSX) não ganharam colunas de Utilização HH/Performance
  nesta sessão — os totais que alimentam essas fórmulas já reconciliam
  com o painel (mesma fonte, `workforce_core.consolidacao`), adicionar as
  colunas é um próximo passo natural se pedido.

## Arquivos afetados

- `src/workforce_core/consolidacao.py`.
- `painel/dados.py`, `painel/graficos.py`, `painel/telas/dashboard.py`.
- `docs/07_MOTOR_EVENTOS_E_HH.md`, `docs/12_DASHBOARDS_ECHARTS.md`,
  `docs/23_DECISOES_PENDENTES.md`.
- `tests/test_consolidacao.py`, `tests/test_painel.py`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: ver `CHANGELOG.md` para a contagem exata desta sessão.
- Caso de teste completo com códigos reais do Relatório 1 (`EE12`
  deslocamento, `EE02` pausa refeição, `EE17`/`EE21` atividade/falha)
  confirma `resumo_por_classificacao_hh` reconciliando com a jornada
  bruta inteira (nenhuma hora perdida entre os buckets de
  classificação), e `utilizacao_hh` calculando a fração esperada a
  partir desse resumo.
- Gráfico gauge testado com `renderizar_embutido` (mesma checagem de
  "sem CDN" já aplicada aos outros gráficos).

## Validação NÃO realizada

- Nenhuma validação com a operação real de qual "meta" de Utilização HH
  seria considerada boa/ruim — deliberadamente fora de escopo (ver
  seção acima).
- Teste manual do painel em navegador real (mesma limitação de sempre,
  `docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md`).

## Data e responsáveis

- Data de registro: 2026-07-30.
- Registrado por: Claude Code, a partir das fórmulas fornecidas por
  j.copaz@hotmail.com.
