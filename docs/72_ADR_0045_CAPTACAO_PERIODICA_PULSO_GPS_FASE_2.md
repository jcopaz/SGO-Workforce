# ADR-0045 | Captação periódica de pulso GPS na interface de campo - Fase 2

## Contexto

Sequência de ADR-0042 (levantamento), ADR-0043 (decisões de negócio) e
ADR-0044 (Fase 1 - backend `/pulsos` + mapa operacional, já no ar). A
Fase 1 deixou o "cofre" pronto; faltava ensinar a interface de campo
(`interface_campo/`, PWA em JavaScript puro, sem build) a de fato capturar
e enviar pulsos. Este ADR cobre a Fase 2, fechando o ciclo.

Decisões de negócio já tomadas no ADR-0043, implementadas aqui ao pé da
letra:

- **1 pulso por minuto**, durante toda a jornada ativa (`ABERTA`),
  independente do que estiver acontecendo dentro dela (atividade, pausa,
  evento secundário).
- **GPS obrigatório** (leitura local bem-sucedida - não depende de rede,
  só do sensor do aparelho) para iniciar/encerrar jornada e
  iniciar/encerrar atividade.
- Pulsos periódicos de fundo **nunca bloqueiam** se a captura falhar - só
  deixam de gerar aquele pulso (a lacuna fica visível pela ausência do
  dado, nunca por uma trava).
- **100% offline durante o dia**: nenhuma chamada de rede acontece
  enquanto a jornada está em andamento só por causa do GPS. A
  sincronização de pulsos usa o mesmo gatilho que a jornada já usa hoje
  (`dispararSincronizacao()` - dispara best-effort após cada transição
  confirmada, e manualmente pelo botão "Sincronizar agora" ao encerrar).
  Isso entrega estritamente mais durabilidade do que "só sincronizar no
  fim do dia": os pulsos vão sendo confirmados ao longo do turno, não
  ficam todos vulneráveis a uma perda de aparelho até o fim.

## Decisão

### 1. `interface_campo/js/entidades.js`

`gerarId()` (antes privada) passa a ser exportada, e ganha uma nova
fábrica `novoPulsoGps({...})` - mesmo padrão das demais entidades (objeto
simples, gravável direto no IndexedDB via structured clone). Além dos
campos que espelham `workforce_core.entities.PulsoGps`, o objeto local
carrega um campo **só-cliente** `sincronizado: boolean`, controle de fila
que não existe (nem precisa existir) do lado Python.

### 2. `interface_campo/js/geolocalizacao.js`

- `capturarPosicaoAtual` passa a devolver também `velocidadeMetrosSegundo`
  e `direcaoGraus` (de `coords.speed`/`coords.heading`, quando o navegador
  fornece - `null` quando não). Mudança aditiva: quem já usava a função
  (captura pontual do atendimento de falha, D2) ignora os campos novos
  sem quebrar. Habilita, do lado do domínio, a avaliação de qualidade por
  velocidade reportada pelo próprio aparelho (`qualidade_gps.py`, pronta
  desde o Incremento 7, nunca alimentada com dado real até agora).
- Duas funções novas: `iniciarCapturaPeriodica(aoCapturar, { intervaloMs = 60000 })`
  (um `setInterval` que chama `capturarPosicaoAtual()` a cada ciclo e só
  invoca `aoCapturar` quando a captura dá certo - best-effort, mesmo
  espírito da captura pontual) e `pararCapturaPeriodica(idIntervalo)`
  (`clearInterval`).

### 3. `interface_campo/js/armazenamento.js`

`VERSAO_BANCO` 1 → 2. `onupgradeneeded` ganha um segundo
`objectStoreNames.contains` criando o object store `pulsos` (`keyPath:
"id"`) - upgrade puramente aditivo, quem já tinha o banco na v1 mantém a
jornada gravada e só ganha o store novo.

Três funções novas, mesmo estilo de `salvarJornada`/`listarJornadasAbertas`:
`salvarPulso(pulso)` (put atômico), `listarPulsosPendentes(jornadaId)`
(filtro em memória por `jornadaId` e `!sincronizado`, sem índice novo - o
volume por jornada, no máximo alguns milhares de pulsos por turno a
1/minuto, não justifica) e `marcarPulsosSincronizados(ids)` (get+put por
id, dentro de uma única transação).

### 4. `interface_campo/js/sincronizacao.js`

`pulsoParaPayload(pulso)` (pura, exportada) - mesmo contrato de
`workforce_storage.serializacao.pulso_gps_para_dict`, em snake_case.
`sincronizarPulsos(pulsos, opcoes)` - mesmo formato de `sincronizar()`
(`fetchImpl`/`urlBase`/`token`/`configurada` injetáveis, sempre
`{ok, mensagem}`, nunca lança). Lote vazio é sucesso trivial, sem chamada
de rede. `POST {urlBase}/pulsos` com o array inteiro no corpo, mesmo
contrato do endpoint da Fase 1.

### 5. `interface_campo/js/app.js` - a integração

- `sincronizarEstadoCapturaPeriodica()`: liga/desliga o intervalo
  conforme `motor?.jornada.estado === "ABERTA"`. Chamada na primeira
  linha de `render()` - cobre tanto o clique em "Iniciar jornada" quanto
  a recuperação de uma jornada aberta ao reabrir o app (`iniciar()`),
  sem duplicar a lógica em cada botão. Idempotente: chamar de novo a cada
  render nunca duplica nem perde o intervalo em andamento.
- `registrarPulsoCapturado(posicao)`: monta um `novoPulsoGps` a partir da
  jornada/matrícula atuais e grava via `salvarPulso` - usada tanto pela
  captura periódica quanto pela trava de GPS obrigatório (a leitura é
  reaproveitada como pulso de verdade, nunca descartada).
- `sincronizarPulsosPendentes(jornadaId)`: busca pendentes, chama
  `sincronizarPulsos`, marca sincronizado só se o backend confirmar.
  Chamada dentro de `dispararSincronizacao()`, em paralelo ao sync de
  jornada (fire-and-forget, não interfere no status mostrado na tela, que
  é reservado para a jornada).
- `executarComGpsObrigatorio(transicao)`: captura posição; se falhar,
  mostra erro e **não aplica a transição** (trava de verdade, diferente
  da captura de fundo); se der certo, grava o pulso e só então chama
  `executar(transicao)`. Devolve `true`/`false` para quem chama decidir
  se continua com passos que só fazem sentido após a transição ter sido
  de fato aplicada (relevante no fluxo de "retomar atendimento de falha
  pendente" ao iniciar jornada, que só deve avisar/consumir a
  continuação se a jornada realmente abriu).
- Trocado `executar(...)` por `executarComGpsObrigatorio(...)` nos 6
  pontos que a decisão de negócio cobre: "Iniciar jornada" (os dois
  caminhos - com e sem continuação de falha pendente), "Encerrar
  jornada", "Iniciar" quando a ação escolhida é atividade ou atendimento
  de falha (não quando é pausa/evento secundário avulso - fora do escopo
  da decisão do ADR-0043), "Concluir atividade", "Concluir atendimento" e
  "Atividade não concluída". O handler do botão "Iniciar" virou `async`
  (mesmo padrão já usado no botão "Iniciar jornada").

### 6. `interface_campo/index.html` e `interface_campo/service-worker.js`

Aviso fixo da tela atualizado (não dizia mais a verdade depois desta
mudança). `CACHE_VERSAO` "v17" → "v18" e rodapé "Versão v17" → "Versão
v18" (nenhum arquivo novo criado - tudo aditivo em arquivos já listados
em `ARQUIVOS_APP_SHELL`, só a versão do cache precisava mudar).

### 7. Testes novos (`node --test tests/js`)

- `tests/js/geolocalizacao.test.mjs`: velocidade/direção presentes ou
  `null`; `iniciarCapturaPeriodica` chama o callback repetidamente só
  quando a captura dá certo, nunca quando falha; `pararCapturaPeriodica`
  realmente para novas chamadas. Usa `intervaloMs` curto (15-20ms) e
  `setTimeout` real em vez de fake timers - simples, sem dependência
  nova, e rápido o bastante para não pesar a suíte.
- `tests/js/sincronizacao.test.mjs`: `pulsoParaPayload` (contrato
  correto) e `sincronizarPulsos` (lote vazio não chama fetch, não
  configurada, erro de rede, erro HTTP, sucesso com o corpo/token
  corretos) - mesmo padrão exaustivo já usado para `sincronizar()`.
- `armazenamento.js` (IndexedDB) e a integração em `app.js` (DOM,
  orquestração) **não ganharam teste automatizado** - mesma limitação que
  já valia para `salvarJornada`/`render()` antes desta mudança (sem
  IndexedDB nem DOM disponível em Node puro, projeto sem
  `package.json`/build para trazer uma dependência nova só para isso).

## Validação de qualidade realizada

- `node --check` nos 5 arquivos JS tocados (`app.js`, `armazenamento.js`,
  `geolocalizacao.js`, `sincronizacao.js`, `entidades.js`): sem erro de
  sintaxe.
- `node --test tests/js`: 118 passed (94 anteriores + 24 novos), sem
  regressão.
- `pytest` completo: 318 passed, sem regressão - esperado, nenhum arquivo
  `.py` foi tocado nesta fase.
- Leitura completa dos 3 arquivos-chave depois de editados
  (`app.js`, `armazenamento.js`, `geolocalizacao.js`), conferindo os 6
  pontos de `executarComGpsObrigatorio` e que
  `sincronizarEstadoCapturaPeriodica()` cobre tanto o clique em "Iniciar
  jornada" quanto a recuperação de jornada aberta em `iniciar()`.
- `CACHE_VERSAO`/rodapé conferidos manualmente como pareados (v18/v18).

## Validação NÃO realizada

- **Teste em celular real** - a limitação mais importante deste ADR.
  Nada aqui foi validado num navegador/PWA de verdade: permissão de
  geolocalização, comportamento em segundo plano quando a tela é
  bloqueada ou o app perde foco (navegadores throttlam/suspendem timers
  de aba em background de formas que variam por SO/navegador - o
  `setInterval` pode não disparar pontualmente, ou nada, com a tela
  apagada), consumo de bateria de `enableHighAccuracy: true` a cada
  minuto por um turno inteiro, e o próprio fluxo de upgrade do IndexedDB
  (v1 → v2) num aparelho que já tinha o app instalado antes desta versão.
  Necessário antes de considerar a Fase 2 pronta para operação real, não
  só para revisão de código.
- Conexão real com o backend hospedado (Postgres) - mesma ressalva já
  registrada no ADR-0044.

## Deliberadamente fora deste ADR

- Limiares numéricos de qualidade (`precisao_maxima_aceitavel_metros`,
  `velocidade_maxima_plausivel_metros_segundo`) continuam sem valor
  definido - a avaliação (`qualidade_gps.avaliar_pulso`) roda no domínio
  Python, não no cliente; os pulsos chegam ao backend com `qualidade:
  NAO_AVALIADO` até uma decisão de negócio definir os limiares.
- Retenção/expurgo automático de 90 dias (ADR-0043) - mecanismo ainda não
  implementado em nenhum repositório (nem local nem Postgres).
- Perfis de acesso à trajetória, avaliação LGPD formal - pendentes, não
  decidíveis num ADR técnico.

## Arquivos afetados

- `interface_campo/js/entidades.js` (`gerarId` exportada, `novoPulsoGps`).
- `interface_campo/js/geolocalizacao.js` (velocidade/direção,
  `iniciarCapturaPeriodica`/`pararCapturaPeriodica`).
- `interface_campo/js/armazenamento.js` (`VERSAO_BANCO` v2, store
  `pulsos`, `salvarPulso`/`listarPulsosPendentes`/`marcarPulsosSincronizados`).
- `interface_campo/js/sincronizacao.js` (`pulsoParaPayload`,
  `sincronizarPulsos`).
- `interface_campo/js/app.js` (integração completa - captura periódica,
  sincronização de pulsos, trava de GPS obrigatório nos 6 pontos).
- `interface_campo/index.html` (aviso atualizado, versão v18).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v18).
- `tests/js/geolocalizacao.test.mjs`, `tests/js/sincronizacao.test.mjs`
  (casos novos).
