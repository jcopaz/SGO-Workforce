# ADR-0070 — Pulso de GPS sincroniza no momento da captura, não só na próxima transição de jornada

- Status: aceito e implementado
- Data: 2026-08-14

## Contexto

Usuário relatou, após testar de um dia para o outro em celular real:

> "percebi que o sistema não está captando os pulsos quando eu alterno entre a
> página seja do navegador, seja com outro aplicativo (...) percebi que não
> ficou coletando os pulsos seja com a tela em primeiro plano seja alternando
> entre aplicativos."

Uma pergunta de esclarecimento (`AskUserQuestion`) confirmou o ponto decisivo:
os pulsos periódicos (1/min) **não apareceram nem com o app em primeiro
plano, sem trocar de aplicativo**. Isso descarta a hipótese inicial de
"limitação conhecida de throttling de aba em segundo plano" (já documentada
em `project_gps_segundo_plano_alternativas`) — a captura em si funcionava,
mas os pulsos não chegavam ao backend.

## Causa raiz

Em `interface_campo/js/app.js`, a função `registrarPulsoCapturado(posicao)`
— chamada tanto pelo `setInterval` da captura periódica quanto pelo listener
de `visibilitychange` (bônus ao voltar pro app) — só fazia:

```js
await salvarPulso(pulso); // grava local no IndexedDB
```

Não havia nenhum disparo de sincronização a partir daí. O único lugar do
código que chamava `sincronizarPulsosPendentes(jornadaId)` era
`dispararSincronizacao()`, e esta só era chamada de dentro de `persistir()`,
que só roda como efeito colateral de `executar()` — ou seja, **só quando uma
transição de domínio explícita acontece** (iniciar/encerrar jornada,
atividade, pausa, evento).

Consequência prática: um técnico numa única atividade longa (cenário comum
em manutenção de campo) gerava dezenas de pulsos periódicos que ficavam
presos no IndexedDB do celular até a *próxima* ação de jornada — que podia
não vir por horas. Do lado do painel (Mapa Operacional), a jornada aparecia
sem nenhum pulso intermediário, só com os poucos pulsos que por acaso
coincidiam com um clique de transição.

## Decisão

`registrarPulsoCapturado` agora dispara `sincronizarPulsosPendentes(jornadaId)`
logo após salvar o pulso localmente — **sem `await`** (fire-and-forget),
porque:

1. `executarComGpsObrigatorio` aguarda `registrarPulsoCapturado` antes de
   aplicar a transição de domínio; se a sincronização fosse aguardada ali,
   uma rede lenta ou offline atrasaria (ou pareceria travar) a ação do
   usuário — contradiz o princípio offline-first do golden rule #7.
2. `sincronizarPulsosPendentes`/`Sincronizacao.sincronizarPulsos` já são
   best-effort e nunca lançam exceção (garantido em `sincronizacao.js` e
   coberto por teste); chamar a mais é seguro e idempotente (o backend só
   recebe pulsos que ainda constam como pendentes localmente).

Efeito: cada pulso (periódico, de retorno ao foreground, ou vinculado a uma
transição) agora tenta sincronizar sozinho, no seu próprio ritmo, em vez de
depender de uma transição de jornada não relacionada para ser enviado.

## Alternativas consideradas

- **Sincronizar em lote com intervalo próprio (ex.: a cada 5 min) em vez de
  a cada pulso**: reduziria um pouco o número de chamadas de rede, mas
  adiciona um segundo temporizador para manter e ainda deixa uma janela sem
  garantia curta. Descartado por ora — pode ser revisitado se o consumo de
  dados/bateria virar problema relatado.
- **Sincronizar só no `visibilitychange` (retorno ao app)**: não cobre o caso
  confirmado pelo usuário de pulso perdido mesmo em primeiro plano contínuo.

## Validação

- `node --check interface_campo/js/app.js` — sintaxe ok.
- `node --test tests/js/*.test.mjs` — 158/158 testes passando (nenhum teste
  quebrou; a mudança não altera contrato de nenhuma função existente, só
  adiciona uma chamada extra best-effort).
- `CACHE_VERSAO` do service worker e rodapé do `index.html` bumpados para
  v36, para o PWA já instalado no celular pegar o `app.js` corrigido na
  próxima abertura.

## Pendências relacionadas (não resolvidas neste ADR)

O relato original do usuário tinha mais duas partes, tratadas separadamente:

- (b) o que fazer quando o colaborador não consegue completar o login online
  obrigatório no início do turno (reabre a decisão "bloqueia sempre" do
  ADR-0065) — decisão de negócio, ainda em aberto.
- (c) como o sistema se comporta ao perder conectividade no meio do turno
  (transição online→offline) — a arquitetura offline-first já cobre isso
  (fila local + sync best-effort), falta só confirmar/explicar formalmente.
