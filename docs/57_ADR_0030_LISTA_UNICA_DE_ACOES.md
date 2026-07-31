# ADR-0030 | Lista única de ações na tela de topo da interface de campo

## Contexto

A tela "jornada aberta, sem atividade em andamento" (`interface_campo/js/app.js`)
acumulou, incremento a incremento, quatro elementos de interação
simultâneos: um botão "Iniciar atividade", um botão "Iniciar atendimento
de falha", um seletor + botão "Iniciar deslocamento/espera/apoio" (15
códigos, ADR-0005/0024) e um botão "Encerrar jornada". O responsável pelo
produto pediu, em 2026-07-31, uma tela mais simples: **uma lista única**
com todas as opções, um botão "Iniciar" embaixo dela que vira "Encerrar"
quando algo está em andamento, e ao encerrar volta para a mesma lista.
Dentro dessa lista, escolher "Iniciar atividade" ou "Atendimento de
falha" abre os formulários que já existem para cada um.

O exemplo dado pelo responsável do produto usava "DDS/APR" como primeira
ação, logo após "Iniciar Jornada" — mas `EE20` "DDS/APR" é hoje um código
de **pausa** (`tipo_registro = "pausa"`), e `Pausa` exige uma `Atividade`
ativa para existir (`PausaExigeAtividadeAtivaError`). Isso não é só uma
questão de UI: os outros 4 códigos de pausa (`EE02` Refeição, `EE07`
Reunião/ADM, `EE11` Consulta à documentação técnica, `EE22` Treinamento)
têm a mesma restrição. Perguntado explicitamente, o responsável do
produto confirmou: esses 5 códigos devem poder ser iniciados soltos,
sem nenhuma atividade em andamento — igual aos 15 códigos de
deslocamento/espera/apoio já funcionam hoje.

## Decisão

### 1. Reaproveitar EventoSecundario, não criar mecanismo novo

`EventoSecundario` já é exatamente "um evento de nível jornada, com
motivo, início/fim, mutuamente exclusivo com Atividade, sem exigir
Atividade ativa" — o mecanismo certo para os 5 códigos de pausa quando
usados soltos. `Pausa` continua estruturalmente amarrada a uma
`atividade_id` (campo obrigatório) e **não foi alterada** — pausar de
dentro de uma atividade em andamento continua funcionando exatamente
como antes, motor e catálogo sem nenhuma mudança nesse caminho.

`src/workforce_core/catalogo.py`: `EE02`, `EE07`, `EE11`, `EE20`, `EE22`
ganham `tipo_evento_secundario = TipoEventoSecundario.APOIO` (mesma
categoria genérica já usada para o grupo heterogêneo de apoio -
preparar/desmontar atividade, carregar/descarregar veículo, serviço
interno da coordenação). `tipo_registro` desses 5 códigos **continua
"pausa"** - nenhuma mudança na tabela `codigos_relatorio_1_por_tipo_registro`
nem no seletor de pausa aninhado dentro de uma atividade
(`criarSeletorMotivoPausa`, inalterado).

Como a reconciliação de HH (`workforce_core.consolidacao`) já procura a
`categoria`/`classificacao_hh` de um evento pelo **código** (`catalogo.obter(motivo)`),
não pela entidade que gravou a duração, o tempo de "DDS/APR" soma no
mesmo bucket de relatório/painel independente de ter sido registrado via
`Pausa` (de dentro de uma atividade) ou via `EventoSecundario` (solto) -
nenhuma mudança necessária em `consolidacao.py`, exportações ou painel.

### 2. Backend/reparo automático (ADR-0026) cobre os 5 códigos novos de graça

`RepositorioCatalogoPostgres._reparar_tipo_evento_secundario` já
preenche `tipo_evento_secundario` para qualquer código com esse campo
definido em `catalogo_relatorio_1_manutencao()` - passa de 15 para 20
códigos sem nenhuma mudança de código no backend, só porque a fonte de
dados (`_RELATORIO_1_ENTRADAS`) mudou.

### 3. Frontend: lista única + botão Iniciar/Encerrar

`interface_campo/js/app.js`:
- `criarSeletorAcaoPrincipal()` (substitui `criarSeletorEventoSecundario`,
  removida): um único `<select>` com dois `<optgroup>` - "Ação principal"
  (Iniciar atividade / Atendimento de falha, valores sentinela
  `__ATIVIDADE__`/`__FALHA__`) e "Pausa, deslocamento e apoio" (os 20
  códigos - 5 de pausa + 15 de evento secundário - combinados e
  ordenados por código).
- Um único botão "Iniciar" despacha para `iniciarAtividade`,
  `iniciarAtendimentoFalha` ou `iniciarEventoSecundario` conforme o valor
  selecionado.
- Enquanto o evento está ativo, a tela mostra "`<descrição>` em
  andamento." (antes era um texto fixo "Deslocamento/espera/apoio em
  andamento." - não fazia mais sentido cobrindo também DDS/Refeição/etc.)
  e o botão "Encerrar evento" - ao encerrar, `render()` cai de novo no
  mesmo ramo `else`, mostrando a lista única de novo. Fluxo completo:
  Iniciar Jornada → lista única → Iniciar → (Encerrar, volta pra lista) →
  repete, exatamente como descrito pelo responsável do produto.
- "Encerrar jornada" continua um botão separado, fora da lista - decisão
  técnica deliberada: é uma ação terminal/destrutiva (encerra o turno
  inteiro), não "mais uma coisa que se está fazendo".
- `tipoEventoSecundarioParaCodigo` e a nova `descricaoParaCodigo` agora
  procuram em `motivosPausa` **e** `eventosSecundarios`, já que os 20
  códigos podem vir de qualquer uma das duas listas buscadas do catálogo.

`interface_campo/js/catalogoMotivos.js`: `CATALOGO_MINIMO_OFFLINE` e
`TIPO_EVENTO_SECUNDARIO_CONHECIDO` (fallback local, ver ADR-0026)
atualizados com os 5 códigos novos; `obterMotivosPausa()` passa a aplicar
o mesmo reparo defensivo (`repararTipoEventoSecundarioAusente`) que
`obterEventosSecundarios()` já aplicava - sem isso, os 5 códigos ficariam
vulneráveis ao mesmo bug do ADR-0026 assim que o backend de produção
ainda não tivesse reiniciado com este ADR.

## Deliberadamente fora deste incremento

- Nenhuma mudança na regra "Pausa exige Atividade ativa" - continua
  válida para pausa aninhada dentro de uma atividade em andamento.
- Nenhuma mudança em `Refeição` (EE02) além de ganhar o uso avulso - o
  comportamento de "trava 1 hora e retoma automaticamente" observado no
  OptJob original (`docs/21_APRENDIZADOS_HERDADOS_SGO.md`) não foi
  pedido nem implementado aqui.
- Reordenar/agrupar a lista por categoria (produtivo/improdutivo) em vez
  de por código - manteve a ordem numérica do formulário em papel, que é
  o que a operação já conhece.

## Arquivos afetados

- `src/workforce_core/catalogo.py`.
- `interface_campo/js/app.js`, `interface_campo/js/catalogoMotivos.js`,
  `interface_campo/service-worker.js` (`CACHE_VERSAO` v14 → v15).
- `tests/test_catalogo_relatorio_1.py`, `tests/test_repositorio_catalogo_postgres.py`,
  `tests/js/catalogoMotivos.test.mjs`.
- `docs/11_TELAS_E_UX.md`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 276/276 (inalterado em quantidade de testes de domínio, só
  valores esperados atualizados - a contagem de testes do catálogo/reparo
  Postgres mudou de forma, ver diffs).
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js/*.test.mjs`: 107/107 (era 105).
- Reconciliação confirmada por leitura de código: `consolidacao.py`
  classifica por código de catálogo, não por qual entidade (`Pausa` ou
  `EventoSecundario`) gravou a duração - nenhum número de HH/painel muda
  de comportamento com esta mudança.

## Validação NÃO realizada

- Teste manual em navegador/celular real (mesma limitação de sempre).
- Nenhuma validação com a operação de que "Ação principal" no topo do
  `<optgroup>` (em vez dos 20 códigos primeiro) é a ordem mais intuitiva
  - decisão de UX do agente, não validada.

## Data e responsáveis

- Data de registro: 2026-07-31.
- Registrado por: Claude Code, a partir do fluxo descrito por
  j.copaz@hotmail.com, com confirmação explícita sobre pausas avulsas via
  pergunta direta.
