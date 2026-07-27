# ADR-0025 | Associação de Ordem de Serviço a EE17/EE23 na interface de campo

## Contexto

O ADR-0023 (reclassificação do catálogo do Relatório 1) criou o código
`EE23` ("Manutenção Programada Não Concluída") como contraparte de
`EE17` ("Manutenção Programada"), mas deixou explicitamente registrado
que a mecânica de uso — associação de uma ou mais OS em texto livre a
uma atividade EE17, exclusão parcial de OS não concluídas, os dois
botões de encerramento que produzem EE17 ou EE23 — era "um incremento de
produto separado, ainda não implementado", com as decisões de negócio já
tomadas com o responsável pelo produto: **texto livre** (não o
`ReferenciaOS` estruturado que `DadosFalha.os_referencia` já usa, nunca
implementado na interface), **múltiplas OS por atividade**, **exclusão
individual das não concluídas**, **dois botões** ("Concluir atividade" →
EE17, "Atividade não concluída" → EE23), **sem transferência entre
colaboradores**.

Antes deste ADR, `EE17` era só *inferido* — qualquer `Atividade`
encerrada sem `dados_falha` virava `ATIVIDADE_PLANEJADA` em
`consolidacao.py`, e não existia nenhum caminho de código que produzisse
`EE23`. Este ADR fecha essa lacuna.

## Decisão

### 1. `Atividade` ganha `ordens_servico` e `resultado`

`src/workforce_core/entities.py`: nova dataclass `OrdemServico` (`numero:
str`, `id`, `criada_em`, `excluida: bool = False`). `Atividade` ganha
`ordens_servico: List[OrdemServico]` e `resultado: Optional[ResultadoAtividade]`
(novo enum em `enums.py`: `CONCLUIDA`/`NAO_CONCLUIDA`). `excluida` é
soft-delete — nunca remove da lista, mesmo princípio de "correção nunca
apaga o evento original" já aplicado ao campo `ativo` do catálogo. Isso é
a leitura escolhida para "exclusão parcial de OS não concluídas" do
ADR-0023: marcar como excluída, não apagar do registro.

`resultado is None` (qualquer `Atividade` encerrada antes deste ADR) é
tratado como `CONCLUIDA` na consolidação — preserva o comportamento
implícito que já existia, sem reclassificar dados já sincronizados.

### 2. Novas transições no motor (`engine.py`, espelhadas em `motorJornada.js`)

- `adicionar_ordem_servico(quando, numero)`: exige atividade ativa **sem**
  `dados_falha` (`OrdemServicoExigeAtividadeSemFalhaError` — OS não se
  aplica a atendimento de falha, que já tem seu próprio campo
  `os_referencia`, estruturado e não relacionado) e número não vazio
  (`OrdemServicoNumeroObrigatorioError`).
- `excluir_ordem_servico(id)`: soft-delete, idempotente (excluir de novo
  a mesma OS não muda nada); `OrdemServicoNaoEncontradaError` se o id não
  existir na atividade ativa.
- `encerrar_atividade` (sem mudança de assinatura) agora grava
  `resultado = CONCLUIDA` explicitamente.
- `encerrar_atividade_nao_concluida(quando)`: mesma validação de
  `encerrar_atividade` (pausa aberta, atividade ativa, completude de
  `dados_falha` se houver), mas grava `resultado = NAO_CONCLUIDA`.
  Exige que a atividade **não** tenha `dados_falha`
  (`AtividadeNaoConcluidaExigeSemDadosFalhaError`) — atendimento de falha
  já tem seu próprio desfecho equivalente
  (`transferir_atendimento_falha`, "Falha não Concluída", D4).

### 3. Consolidação usa `resultado` para produzir EE23

`consolidacao.py`: nova `_categoria_atividade(atividade)`, usada em
`resumo_por_categoria` e `linhas_eventos_classificadas` — `dados_falha`
tem precedência (sempre `ATENDIMENTO_FALHA`), senão `resultado ==
NAO_CONCLUIDA` produz `ATIVIDADE_PLANEJADA_NAO_CONCLUIDA` (EE23), senão
`ATIVIDADE_PLANEJADA` (EE17, comportamento anterior preservado para
`resultado is None`).

### 4. Persistência e sincronização

`workforce_storage/serializacao.py`: `atividade_para_dict`/
`atividade_de_dict` serializam `ordens_servico` e `resultado`.
`FORMATO_VERSAO` 4 → 5, retrocompatível (`.get(..., [])`/`.get("resultado")`
— jornadas gravadas antes deste ADR continuam lendo normalmente).
`interface_campo/js/sincronizacao.js` serializa os mesmos campos no
payload de `POST /jornadas`; como a rota já recebe `Dict[str, Any]`
genérico (mesma constatação do ADR-0024), **nenhuma mudança de API foi
necessária**.

### 5. Interface de campo

`app.js`: na tela de atividade comum em andamento (sem `dados_falha`),
novo bloco com lista de OS ativas (cada uma com botão "Excluir"), campo
de texto e botão "Adicionar OS". O botão único de encerramento vira dois:
"Concluir atividade" (`encerrarAtividade`) e "Atividade não concluída"
(`encerrarAtividadeNaoConcluida`). Atendimento de falha mantém seu único
botão "Concluir atendimento" e seu próprio fluxo de "Falha não
concluída" — nenhuma mudança nesse caminho.

## Deliberadamente fora deste incremento

- **Exportações (CSV/XLSX/GeoJSON)**: nenhum dashboard exibe OS ainda;
  fica para quando isso for pedido.
- **Transferência de atividade entre colaboradores**: decisão já tomada
  de que não entra.
- **`ReferenciaOS`/`os_referencia` estruturado**: continua existindo só
  em `DadosFalha`, sem uso na interface de campo — não foi tocado nem
  reaproveitado aqui, são dois conceitos de OS diferentes.

## Arquivos afetados

- `src/workforce_core/enums.py`, `entities.py`, `engine.py`,
  `exceptions.py`, `consolidacao.py`, `__init__.py`.
- `src/workforce_storage/serializacao.py`.
- `interface_campo/js/enums.js`, `entidades.js`, `erros.js`,
  `motorJornada.js`, `sincronizacao.js`, `app.js`.
- `tests/test_ordem_servico.py` (novo, 19 casos),
  `tests/js/motorJornada.test.mjs`, `tests/js/sincronizacao.test.mjs`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: 249/249 (era 230 depois do ADR-0024).
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js`: 102/102 (era 89 depois do ADR-0024).
- Casos novos cobrem: adicionar/excluir OS (inclusive idempotência e
  guarda contra atendimento de falha), os dois desfechos de
  encerramento, precedência de `dados_falha` sobre `resultado` na
  consolidação, round-trip de serialização com OS excluída, e
  compatibilidade retroativa (dict sem `ordens_servico`/`resultado`).

## Validação NÃO realizada

- Teste manual em navegador/celular real da nova tela — mesma limitação
  de sempre.
- Nenhuma migração de produção é necessária aqui: `POST /jornadas` já
  aceita o payload novo sem mudança de schema (diferente do ADR-0024, que
  precisou de `ALTER TABLE` no catálogo).

## Data e responsáveis

- Data de registro: 2026-07-28.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com). Decisões de negócio (texto livre, múltiplas OS,
  dois botões, sem transferência) já haviam sido validadas no ADR-0023;
  a interpretação de "exclusão parcial" como soft-delete é deste ADR,
  sinalizada explicitamente para revisão.
