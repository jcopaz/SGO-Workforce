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
- Filtros no painel (colaborador, período, categoria, motivo/justificativa)
  e 3 gráficos novos (evolução diária, HH por colaborador, treemap de
  motivos), baseados em `LinhaEvento`/`linhas_eventos_classificadas`
  (`src/workforce_core/consolidacao.py`). Ver `docs/45_ADR_0018_FILTROS_E_GRAFICOS_DASHBOARD.md`.
- `catalogo_completo()` em `src/workforce_core/catalogo.py` (união de
  `catalogo_padrao()` e `catalogo_relatorio_1_manutencao()`).
- Catálogo dinâmico de motivos: `GET`/`POST /catalogo` no backend
  (`src/workforce_api/repositorio_catalogo_postgres.py`, com seed
  automático dos 23 códigos reais), consumido pela interface de campo
  (`interface_campo/js/catalogoMotivos.js`, com cache offline e fallback
  mínimo) e administrado em `painel/pages/4_Catalogo.py`. Ver
  `docs/46_ADR_0019_CATALOGO_DINAMICO.md`.
### Alterado
- `interface_campo/js/app.js`: as 7 transições do motor de dominio agora usam
  `RelogioSimulado.agora()` em vez de `new Date()`; o resumo em andamento
  passou a mostrar o tempo decorrido de jornada/atividade/pausa; toda
  transição agora também dispara sincronização best-effort com o backend.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada de `v4`
  para `v8` ao longo destas sessões (novos arquivos `relogioSimulado.js`,
  `configSincronizacao.js`, `sincronizacao.js` e `catalogoMotivos.js` no
  app shell).
- `requirements.txt`: adiciona `requests` (cliente HTTP do painel).
- `docs/23_DECISOES_PENDENTES.md`: item 10 (hospedagem/autenticação do
  piloto) marcado como resolvido no escopo do piloto.
- `painel/dados.py::montar_resumo` usa `catalogo_completo()` por padrão
  (antes usava `catalogo_padrao()`, só motivos de teste).
- Data/hora em `dd/mm/aaaa hh:mm:ss` no painel (`formatar_data_hora`,
  usada em `painel/app.py` e `painel/pages/1_Mapa_Operacional.py`) e na
  interface de campo (`interface_campo/js/app.js::formatoHora`) - mesmo
  padrão nos dois lados. Exportações CSV/XLSX continuam em ISO 8601
  (decisão consciente, ver ADR-0018).
- Tabela "Jornadas carregadas" no painel: remove coluna `id`, mostra
  Colaborador/Estado/Início/Fim.
- `interface_campo/js/app.js`: motivos de pausa do seletor deixam de vir
  hardcoded (`MOTIVOS_PAUSA_RELATORIO_1` removida) e passam a vir do
  catálogo dinâmico buscado em `iniciar()`.
- `EntradaCatalogo` (`src/workforce_core/catalogo.py`) ganha
  `tipo_registro` e `ativo`; `catalogo_relatorio_1_manutencao()` popula
  `tipo_registro` de verdade no objeto (antes só existia na tupla interna).
### Corrigido
- Categoria "sem classificação" em toda pausa real sincronizada da
  interface de campo: `montar_resumo` usava `catalogo_padrao()` (só
  motivos de teste), que não conhece os códigos reais do Relatório 1
  (EE02/EE07/EE11/EE21/EE23). Corrigido com `catalogo_completo()`. Ver
  ADR-0018.
- Deploy do painel travava em loop no Streamlit Community Cloud
  (`Resolved N packages` e reiniciava sem subir o servidor). Separado
  `requirements.txt` (painel) de `requirements-api.txt` (backend, usado no
  build command do Render) - melhoria válida, mas não era a causa raiz.
  Causa raiz confirmada: Python 3.14 (padrão da plataforma) era recente
  demais para o ecossistema de pacotes ter wheels prontas, travando a
  instalação. Corrigido fixando Python 3.12 nas Advanced settings do app
  (exige recriar o app - a versão do Python não é editável depois de
  criado). Ver ADR-0017.
- Sincronização nunca acontecia mesmo com backend e token corretos:
  `configSincronizacao.js` foi atualizado com a URL/token reais sem
  incrementar `CACHE_VERSAO` do Service Worker, então o navegador
  continuava servindo a versão antiga (placeholder) em cache - exatamente
  a armadilha já registrada no ADR-0004. `CACHE_VERSAO` incrementada de
  `v6` para `v7`.
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
- `tests/test_consolidacao.py`: 3 novos testes de `linhas_eventos_classificadas`.
- `tests/test_painel.py`: novos testes de `formatar_data_hora`,
  `montar_linhas_eventos`/`agrupar_duracao_por_categoria` e dos 3 gráficos
  novos.
- `tests/test_serializacao_catalogo.py` (novo, 4 casos): round-trip de
  `entrada_catalogo_para_dict`/`entrada_catalogo_de_dict`.
- `tests/test_workforce_api.py`: 5 novos casos de `/catalogo` (token,
  upsert idempotente, inativos omitidos, payload malformado).
- `tests/js/catalogoMotivos.test.mjs` (6 casos): fallback mínimo, cache
  offline, erro HTTP, token no header.
- `node --test tests/js`: 36/36 testes. `pytest`: 197/197 testes.
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
- Login/autenticação de usuário continua adiado (decisão explícita do
  responsável pelo produto em 2026-07-27, ver ADR-0018) - painel e
  interface de campo seguem sem login, só com o token de sincronização.
- Cards de HH produtivo/improdutivo do `docs/12_DASHBOARDS_ECHARTS.md`
  continuam bloqueados: nenhum motivo do catálogo tem
  `classificacao_hh` definida ainda (decisão de negócio pendente).
- Catálogo dinâmico (`motivos_catalogo`) não foi testado contra Postgres
  real neste ambiente (mesma limitação já registrada para `jornadas` no
  ADR-0017) - só validado com repositório falso em memória. Ver ADR-0019.
