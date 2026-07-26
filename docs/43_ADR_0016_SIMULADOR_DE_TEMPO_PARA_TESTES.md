# ADR-0016 | Simulador de tempo para testes (interface de campo)

## Contexto

O motor de domínio (`src/workforce_core/engine.py`, `MotorJornada`) nunca lê
o relógio sozinho — todo `iniciar_jornada`, `iniciar_atividade`,
`iniciar_pausa`, `finalizar_pausa`, `encerrar_atividade` e
`encerrar_jornada` recebe o timestamp `quando` explicitamente. Isso já
estava correto.

O gargalo estava na interface de campo (`interface_campo/js/app.js`,
ADR-0004): os 7 pontos em que o app chama uma transição do motor
(`iniciarJornada`, `iniciarPausa`, `finalizarPausa`, `encerrarAtividade`
— em dois lugares — `iniciarAtividade`, `encerrarJornada`) passavam
`new Date()` direto. O responsável pelo produto testa o piloto no próprio
navegador/celular, em tempo real (CLAUDE.md, regra de ouro 10: testar em
celular real) — o que significa que testar uma jornada de 8h, uma pausa de
almoço de 1h, ou o comportamento em vários dias seguidos (fechamento de
jornada à meia-noite, jornadas em dias diferentes para o mesmo motivo de
pausa, etc.) exigia esperar o tempo real passar. Pedido do responsável pelo
produto (2026-07-26): um jeito de simular/adiantar o relógio para testar
todas as funcionalidades e ver como os dados se comportam, sem depender do
relógio real.

## Decisão

1. **Relógio por deslocamento, não relógio congelado**
   (`interface_campo/js/relogioSimulado.js`): `agora()` retorna
   `Date.now() + deslocamento_ms`. O tempo simulado continua fluindo
   normalmente (1s real = 1s simulado); só o deslocamento acumulado muda.
   Isso foi preferido a "congelar" o relógio num instante fixo porque um
   relógio congelado geraria timestamps idênticos em cliques sequenciais
   rápidos (ex.: iniciar e encerrar uma atividade de teste em menos de um
   segundo real produziria início == fim), o que é uma situação artificial
   que não ajuda a testar o comportamento real do motor.
2. **Escopo: só a interface de campo, só para teste.** O painel gerencial
   (`painel/dados.py::gerar_jornadas_exemplo`) já fabrica jornadas de vários
   dias instantaneamente para testar dashboards — isso não foi duplicado
   aqui. Este incremento resolve especificamente o teste manual, clique a
   clique, no app de campo.
3. **Armazenamento do deslocamento**: `localStorage`
   (`sgo_workforce_relogio_simulado_deslocamento_ms`), com fallback em um
   `Map` em memória quando `localStorage` não existe. O fallback existe por
   dois motivos: (a) torna o módulo testável em Node
   (`node --test tests/js`) sem depender de API de navegador; (b) é
   defensivo caso o navegador bloqueie `localStorage` (modo privado
   restritivo). O deslocamento persiste entre recarregamentos da página,
   igual à jornada em IndexedDB (`armazenamento.js`) — sem isso, cada F5
   voltaria silenciosamente ao tempo real, o que confundiria o teste.
4. **API exposta**: `agora()`, `avancar(ms)`, `definir(dataAlvo)`,
   `voltarParaTempoReal()`, `estaSimulando()`, `descreverDeslocamento()`, e
   as constantes `UM_MINUTO_MS`/`UMA_HORA_MS`/`UM_DIA_MS`.
5. **UI** (`interface_campo/index.html`): painel `<details>` recolhido por
   padrão, rotulado "Simulador de tempo (somente teste)", com aviso
   explícito de que nunca deve ser usado em operação real. Botões de atalho
   (+15min, +1h, +8h, +1 dia) cobrem os saltos mais úteis para testar
   pausas, jornadas de turno completo e virada de dia; um campo
   `datetime-local` cobre o caso de precisar de uma data/hora exata (ex.:
   testar exatamente a virada de meia-noite).
6. **Faixa de aviso sempre visível**: quando `estaSimulando()` é
   verdadeiro, uma faixa de aviso aparece fora do `<details>` (não fica
   escondida se o painel estiver recolhido), mostrando o deslocamento atual
   — para nunca deixar dúvida de que o app está fora do tempo real.
7. **`renderResumoEmAndamento` passou a usar `RelogioSimulado.agora()`**
   (antes tinha uma variável `agora = new Date()` que não era usada) para
   mostrar o tempo decorrido de jornada/atividade/pausa em andamento,
   reaproveitando `calculo.formatarDuracao`. Isso não viola a regra de ouro
   "não calcular duração pelo relógio visual do cliente": o valor exibido
   usa exatamente o mesmo relógio que será persistido se o colaborador
   clicar em um botão agora, não um relógio desconectado do dado real.
8. **Cache do Service Worker**: `relogioSimulado.js` foi adicionado a
   `ARQUIVOS_APP_SHELL` e `CACHE_VERSAO` foi incrementada (`v4` → `v5`) em
   `service-worker.js` — lição já registrada no ADR-0004 (sem isso, o
   Service Worker serviria a versão antiga do app indefinidamente).

## Validação de qualidade realizada

- `node --check` em todos os arquivos JS de `interface_campo/js/` e em
  `service-worker.js`: sintaxe válida.
- `node --test tests/js/motorJornada.test.mjs tests/js/relogioSimulado.test.mjs`:
  24/24 testes (17 já existentes do motor + 7 novos do relógio simulado:
  acompanhar tempo real sem uso, avançar, acumular avanços sucessivos,
  definir data exata, voltar ao tempo real, e formatação do deslocamento
  exibido).

## Validação NÃO realizada — mesma limitação do ADR-0004

Este ambiente continua sem acesso a um navegador real ou Playwright
(bloqueio de rede/proxy corporativo). O fluxo completo do simulador
(expandir o painel, clicar nos botões, ver a faixa de aviso aparecer,
confirmar que os timestamps persistidos no IndexedDB refletem o avanço)
**não foi clicado em um navegador real** — só validado por leitura de
código e pelos testes de lógica pura em Node. Isso precisa ser testado
manualmente (`python -m http.server` dentro de `interface_campo/`) antes de
qualquer uso do simulador para gerar dados de teste que alimentem decisões.

## Alternativas consideradas

- **Congelar o relógio num instante fixo em vez de deslocar**: rejeitado —
  ver item 1 da Decisão (gera timestamps duplicados em cliques rápidos).
- **Simular o tempo no backend**: não há backend real ainda (ADR-0003), e o
  motor de domínio já é agnóstico de relógio — não havia nada para mudar
  ali.
- **Adicionar os mesmos controles ao painel gerencial (Streamlit)**:
  descartado por ora porque o painel já resolve o caso de uso equivalente
  via `gerar_jornadas_exemplo` (dados fabricados instantaneamente, sem
  precisar de um relógio simulado interativo).

## Consequências

- O simulador é uma ferramenta de teste, não um recurso de produto. Se este
  mesmo código for usado num piloto real com colaboradores, o painel de
  simulação precisa ser removido ou bloqueado antes — isso deve ser
  revisitado explicitamente antes de qualquer piloto operacional (mesma
  natureza do aviso "piloto técnico" já presente na tela).
- Continua pendente o teste manual em navegador/celular real (gap já
  registrado no ADR-0004, agora também cobrindo o simulador).
- O deslocamento de relógio é local ao navegador/dispositivo (localStorage)
  — não sincroniza entre dispositivos nem com o painel gerencial.

## Validação operacional

Ainda não realizada. Decisão técnica para destravar teste manual, sujeita a
teste em navegador/celular real antes de ser usada para gerar qualquer dado
que alimente decisão de produto.

## Data e responsáveis

- Data de registro: 2026-07-26.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
- Revisão pendente: teste manual em navegador/celular real por qualquer
  pessoa com acesso a um dispositivo.
