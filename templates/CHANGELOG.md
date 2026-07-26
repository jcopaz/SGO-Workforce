# Changelog

## [Unreleased]
### Adicionado
- Simulador de tempo na interface de campo (`interface_campo/js/relogioSimulado.js`):
  painel "Simulador de tempo (somente teste)" com botões +15min/+1h/+8h/+1 dia
  e definição de data/hora exata, para testar jornadas de vários dias sem
  esperar o relógio real passar. Ver `docs/43_ADR_0016_SIMULADOR_DE_TEMPO_PARA_TESTES.md`.
### Alterado
- `interface_campo/js/app.js`: as 7 transições do motor de dominio agora usam
  `RelogioSimulado.agora()` em vez de `new Date()`; o resumo em andamento
  passou a mostrar o tempo decorrido de jornada/atividade/pausa.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada de `v4`
  para `v5` (novo arquivo `relogioSimulado.js` no app shell).
### Corrigido
### Testes
- `tests/js/relogioSimulado.test.mjs` (7 casos): avançar, definir data exata,
  voltar ao tempo real e formatação do deslocamento exibido.
- `node --test tests/js/motorJornada.test.mjs tests/js/relogioSimulado.test.mjs`:
  24/24 testes.
### Riscos
- Simulador de tempo é ferramenta de teste: precisa ser removido/bloqueado
  antes de qualquer piloto real com colaboradores (ver ADR-0016).
- Teste manual em navegador/celular real deste incremento ainda pendente
  (mesmo gap conhecido do ADR-0004).
