# ADR-0053 | Lote de decisões pendentes de 2026-08-05 (EE21, RASF, Performance, GPS 2º plano) + ajustes no filtro de Jornada do mapa

## Contexto

Pedido do responsável pelo produto em 2026-08-04: "o que for pendente de
minha decisão já traga aqui para eu decidir e você ir atualizando e
codificando, atualiza tudo primeiro o que está pendente comigo aí depois
vamos fazer um pacote grande de atualização." Quatro itens de
`docs/23_DECISOES_PENDENTES.md` foram trazidos de uma vez
(`AskUserQuestion`) e decididos nesta conversa. No meio do mesmo turno,
dois ajustes menores foram pedidos sobre o filtro "Jornada" do mapa
operacional (ADR-0052, do dia anterior).

## Decisões

### 1. `EE21` "Atendimento de Falha": `PRODUTIVA` → `PRODUTIVA_NAO_RENTAVEL`

Item 17 de `docs/23_DECISOES_PENDENTES.md`. Confirma a leitura já
registrada como provável no ADR-0028 (manutenção não planejada no OptJob
original era produtiva não rentável). `EE23` (Manutenção Programada Não
Concluída) **não** foi incluída nesta decisão — continua `PRODUTIVA`, não
foi perguntada.

Implementado em `src/workforce_core/catalogo.py` (linha da tupla de
`EE21` em `_RELATORIO_1_ENTRADAS`, comentário reescrito acima). Cascata de
testes ajustada: `tests/test_catalogo_relatorio_1.py` (classificação
esperada), `tests/test_consolidacao.py` (2 asserções da jornada de
exemplo do Relatório 1: produtiva 3h20→2h50, produtiva não rentável
30min→1h), `tests/test_painel.py` (`test_horas_produtiva_nao_rentavel_do_resumo_com_dados_de_exemplo`
— a premissa do teste era "deveria ser zero", que deixou de ser verdade
porque a primeira jornada de `gerar_jornadas_exemplo` inclui um
atendimento de falha de 45 minutos; teste reescrito para afirmar
`timedelta(minutes=45)`).

### 2. RASF: continuar importação manual por enquanto

Item 12. Nenhuma automação de importação periódica entra em escopo agora
— mantém o processo manual já existente. Nenhum código alterado por esta
decisão (não havia nada implementado a mudar).

### 3. Indicador de Performance: esperar a Fase 5 (integração com o SGO)

Item 14. O tempo planejado por atividade/OS que alimenta
`workforce_core.consolidacao.performance` (Tempo Planejado / Tempo Real,
ADR-0027) deve vir do SGO quando a integração da Fase 5 existir, em vez
de uma tabela própria de tempos padrão inventada agora. A fórmula
continua pronta e sem uso até lá. Nenhum código alterado por esta
decisão.

### 4. GPS em segundo plano: manter só a mitigação atual por enquanto

Referente à investigação registrada na memória
`project_gps_segundo_plano_alternativas.md` (PWA com mitigação de
`visibilitychange`/captura ao voltar ao primeiro plano, vs. app Android
nativo, vs. integração Traccar). Decisão: não investir em app nativo nem
Traccar agora — a mitigação já implementada no ADR-0048 (captura ao
retornar ao primeiro plano) é suficiente para esta fase. Nenhum código
alterado por esta decisão; registrado para não reabrir a pergunta sem um
motivo novo.

### 5. Filtro "Jornada" do mapa: remover o calendário, rótulo só com a data

Pedido do responsável pelo produto, testando o ADR-0052 (do dia
anterior) ao vivo: "Pode retirar o calendário e o filtro ali Jornada
reduza o texto apenas para pegar a Data 05/08/2026 ao invés de
05/08/2026 06:02:41."

- **Calendário removido**: `calendar_input`
  (`streamlit-calendar-input`) tirado de
  `painel/telas/mapa_operacional.py` — import, coluna `col_calendario` e
  a lógica de restringir jornadas pelo dia clicado. O filtro
  "Colaborador" separado de "Jornada" (a outra metade do ADR-0052)
  **continua** — só o calendário ao lado saiu. Dependência
  `streamlit-calendar-input==0.0.3` removida de `requirements.txt`
  inteira (não tinha mais nenhum uso no projeto). O risco descrito no
  ADR-0052 (pacote pequeno/pouco maduro) deixa de existir junto.
- **Rótulo de Jornada mais curto**: nova função `dados.formatar_data`
  (formato `dd/mm/aaaa`, mesma conversão para horário de Brasília de
  `formatar_data_hora`, só sem hora/minuto/segundo) usada no rótulo do
  `st.selectbox` de Jornada em vez de `formatar_data_hora`.
  **Ressalva tratada**: como o motor de domínio não impede duas jornadas
  do mesmo colaborador no mesmo dia calendário, usar só a data como chave
  de um dict colidiria (uma jornada sumiria silenciosamente do
  dropdown). `_rotulo_jornada` conta quantas jornadas do colaborador caem
  em cada data (`collections.Counter`) e só volta a mostrar o
  horário completo (`formatar_data_hora`) nas jornadas cujo dia tem mais
  de uma — no caso comum (1 jornada por dia) o rótulo fica só a data.

## Validação de qualidade realizada

- `python -m py_compile` nos módulos tocados: OK.
- `pytest` completo: 369 passed (0 falhas, nenhuma regressão).
- `node --test tests/js/*.test.mjs`: 126 passed (suíte JS não foi tocada
  por este ADR, roda de novo por precaução).

## Validação NÃO realizada

- Teste em celular real do filtro de Jornada sem calendário (mesma
  limitação de ambiente de sempre).

## Arquivos afetados

- `src/workforce_core/catalogo.py` (EE21).
- `tests/test_catalogo_relatorio_1.py`, `tests/test_consolidacao.py`,
  `tests/test_painel.py` (cascata da reclassificação de EE21).
- `painel/dados.py` (`formatar_data`).
- `painel/telas/mapa_operacional.py` (remoção do calendário, rótulo de
  Jornada).
- `requirements.txt` (remoção de `streamlit-calendar-input`).
- `docs/23_DECISOES_PENDENTES.md` (itens 1, 4, 6, 9, 12, 14, 17 —
  esclarecidos ou marcados como resolvidos; itens 4 e 6 já estavam
  implementados sem nunca terem sido registrados aqui).
