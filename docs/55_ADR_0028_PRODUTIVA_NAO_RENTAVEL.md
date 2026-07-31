# ADR-0028 | Reintrodução de "Produtiva Não Rentável" em ClassificacaoHH

## Contexto

O ADR-0027 registrou, como decisões pendentes (`docs/23_DECISOES_PENDENTES.md`
itens 15 e 16), duas perguntas levantadas pela leitura dos manuais
originais do OptJob (`docs/21_APRENDIZADOS_HERDADOS_SGO.md`): a taxonomia
original tinha 5 níveis de "Tipo de Hora" (Produtiva, **Produtiva Não
Rentável**, Improdutiva, Ausente, Não Apontada), enquanto
`ClassificacaoHH` no Workforce só tinha 4 (sem a distinção "não
rentável"); e `EE16` "Desmontar atividade" estava `IMPRODUTIVA` no
catálogo atual, mas o original classificava como produtivo não rentável.

Em 2026-07-31 o responsável pelo produto respondeu diretamente: **"Pode
classificar como Produtiva Não Rentável."** — autorizando tanto a criação
da categoria quanto a reclassificação dos códigos correspondentes.

## Decisão

### 1. Nova categoria em `ClassificacaoHH`

`src/workforce_core/catalogo.py`: `ClassificacaoHH` ganha
`PRODUTIVA_NAO_RENTAVEL` — tempo de manutenção executável que não gera
faturamento direto. Mantido como `str, Enum` igual às demais, sem
nenhuma mudança de contrato (serialização já genérica em
`workforce_storage/serializacao.py`, nenhuma mudança necessária lá).

### 2. Reclassificação código a código (mapeamento 1:1 confirmado com a tabela original do OptJob)

`EE11`, `EE12`, `EE13`, `EE14`, `EE15`, `EE16`, `EE18`, `EE19`, `EE20`,
`EE22` passam de `PRODUTIVA` (ou `IMPRODUTIVA`, no caso de `EE16`) para
`PRODUTIVA_NAO_RENTAVEL` — a mesma correspondência nome-a-nome já
documentada em `docs/21_APRENDIZADOS_HERDADOS_SGO.md` (consulta a
documentação técnica, deslocamento rodoviário/ferroviário/a pé, preparar/
desmontar atividade, carregar/descarregar veículo, SMS, treinamento).
Resolve o item 15 (mismatch de `EE16`) e o item 16 (adoção da categoria)
de `docs/23_DECISOES_PENDENTES.md` — ambos marcados como resolvidos.

**Deliberadamente não tocado**: `EE17` (Manutenção Programada) e `EE21`
(Atendimento de Falha) continuam `PRODUTIVA`. Na tabela original,
"Ordem de Serviço" é a única entrada plenamente rentável, e "Manutenção
não planejada" (que teria uma leitura razoável como equivalente a
`EE21`) aparece como produtiva não rentável — mas essa correspondência
não é inequívoca o suficiente (não há garantia de que "manutenção não
planejada" no OptJob signifique exatamente "atendimento de falha" no
Workforce) para mudar sem confirmação explícita. Registrado como nova
pergunta em aberto.

### 3. Consequência direta: Utilização HH fica mais estrita

`workforce_core/consolidacao.resumo_por_classificacao_hh` já agregava por
`ClassificacaoHH` sem nenhuma mudança de código necessária — o novo valor
do enum simplesmente aparece como uma chave nova no dicionário resultado.
Mas isso **muda o número exibido no painel**: `utilizacao_hh_do_resumo`
(`painel/dados.py`) usa `por_classificacao_hh[PRODUTIVA]` como "Horas
Produtivas" — antes da reclassificação, esse bucket incluía deslocamento/
preparação/etc.; agora só inclui `EE17`/`EE21` (produtivo rentável
propriamente dito). O indicador de Utilização HH no painel fica mais
estrito (tende a cair) depois desta mudança — comportamento intencional,
não um bug.

### 4. Painel ganha visibilidade da nova fatia

`painel/dados.py::horas_produtiva_nao_rentavel_do_resumo(resumo)`: soma
`por_classificacao_hh[PRODUTIVA_NAO_RENTAVEL]`. `painel/telas/dashboard.py`
ganha um 6º card KPI ("HH produtivo não rentável") ao lado de Utilização
HH, para o gestor sempre ver as duas fatias separadas — nunca misturadas
num só número, mesmo espírito de nunca esconder estado (Regra de Ouro
nº 10 aplicada por analogia).

## Deliberadamente fora deste incremento

- `EE17`/`EE21` continuam `PRODUTIVA` — ver seção 2.
- Nenhuma mudança em `workforce_core/pcm.py` (mapeamento categoria→bucket
  de Capacidade PCM usa `Categoria`, não `ClassificacaoHH` — não afetado
  por este ADR, e PCM não é mais prioridade de evolução por decisão
  prévia do responsável do produto).
- Exportações (CSV/XLSX) não ganharam coluna/aba nova para
  `PRODUTIVA_NAO_RENTAVEL` nesta sessão — os totais que alimentam
  `por_classificacao_hh` já reconciliam com o painel (mesma fonte), a
  coluna é um próximo passo natural se pedido.

## Arquivos afetados

- `src/workforce_core/catalogo.py`.
- `painel/dados.py`, `painel/telas/dashboard.py`.
- `docs/21_APRENDIZADOS_HERDADOS_SGO.md`, `docs/23_DECISOES_PENDENTES.md`.
- `tests/test_catalogo_relatorio_1.py`, `tests/test_consolidacao.py`,
  `tests/test_painel.py`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 265/265 (era 264 antes deste ADR).
- Reconciliação confirmada: numa jornada de teste com deslocamento (EE12),
  atividade planejada (EE17) e atendimento de falha (EE21), a soma de
  `PRODUTIVA + PRODUTIVA_NAO_RENTAVEL + NAO_COMPUTAVEL` continua batendo
  exatamente com a jornada bruta inteira (Regra de Ouro nº 12).

## Validação NÃO realizada

- Teste manual do painel em navegador real (mesma limitação de sempre).
- Nenhuma validação retroativa de jornadas já sincronizadas em produção —
  esta reclassificação só afeta como o catálogo interpreta os códigos
  daqui pra frente; dados já persistidos não são recalculados
  automaticamente em lugar nenhum (o motor sempre reclassifica em tempo
  de leitura, a partir do catálogo atual, nunca grava a classificação
  junto com o evento).

## Data e responsáveis

- Data de registro: 2026-07-31.
- Registrado por: Claude Code, a partir da decisão de
  j.copaz@hotmail.com ("Pode classificar como Produtiva Não Rentável").
