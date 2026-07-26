# Changelog

## [Unreleased]
### Adicionado
- Simulador de tempo na interface de campo (`interface_campo/js/relogioSimulado.js`):
  painel "Simulador de tempo (somente teste)" com botões +15min/+1h/+8h/+1 dia
  e definição de data/hora exata, para testar jornadas de vários dias sem
  esperar o relógio real passar. Ver `docs/43_ADR_0016_SIMULADOR_DE_TEMPO_PARA_TESTES.md`.
- Backend real de sincronização (`src/workforce_api/`, FastAPI + Postgres
  hospedado): `POST /jornadas` e `GET /jornadas` autenticados por token
  fixo (`SYNC_TOKEN`), conectando a interface de campo ao painel pela
  primeira vez. Ver `docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md`.
- `interface_campo/js/sincronizacao.js` e `configSincronizacao.js`:
  sincronização best-effort da jornada com o backend a cada evento
  registrado, status "Sincronizado"/"Não sincronizado" na tela e botão
  manual "Sincronizar agora".
- `painel/dados.py::carregar_jornadas_via_api` e seletor "Fonte de dados"
  (Arquivo local / API (nuvem)) em `painel/app.py`.
### Alterado
- `interface_campo/js/app.js`: as 7 transições do motor de dominio agora usam
  `RelogioSimulado.agora()` em vez de `new Date()`; o resumo em andamento
  passou a mostrar o tempo decorrido de jornada/atividade/pausa; toda
  transição agora também dispara sincronização best-effort com o backend.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada de `v4`
  para `v6` (novos arquivos `relogioSimulado.js`, `configSincronizacao.js`
  e `sincronizacao.js` no app shell).
- `requirements.txt`: adiciona `requests` (cliente HTTP do painel).
- `docs/23_DECISOES_PENDENTES.md`: item 10 (hospedagem/autenticação do
  piloto) marcado como resolvido no escopo do piloto.
### Corrigido
### Testes
- `tests/js/relogioSimulado.test.mjs` (7 casos): avançar, definir data exata,
  voltar ao tempo real e formatação do deslocamento exibido.
- `tests/js/sincronizacao.test.mjs` (6 casos): conversão de payload,
  falha de rede nunca lança, erro HTTP, sucesso, sincronização não
  configurada não chama fetch.
- `tests/test_workforce_api.py` (7 casos): token ausente/errado, sem
  `SYNC_TOKEN` configurada, upsert idempotente, payload malformado -
  repositório injetado é `RepositorioJornadaArquivo` (sem Postgres real
  neste ambiente).
- `node --test tests/js`: 30/30 testes. `pytest`: 179/179 testes.
### Riscos
- Simulador de tempo é ferramenta de teste: precisa ser removido/bloqueado
  antes de qualquer piloto real com colaboradores (ver ADR-0016).
- Token de sincronização fixo não é confidencial (visível no JS público do
  site) - só evita escrita acidental, não protege contra atacante que leia
  o código-fonte (ver ADR-0017).
- Sem fila de retry automática no lado JS: uma falha de sincronização só é
  reprocessada se o colaborador tocar em "Sincronizar agora" de novo.
- Conexão real com Postgres, deploy real no Render e teste de ponta a
  ponta do site publicado ainda não foram realizados neste ambiente (ver
  ADR-0017).
- Teste manual em navegador/celular real deste incremento ainda pendente
  (mesmo gap conhecido do ADR-0004).
