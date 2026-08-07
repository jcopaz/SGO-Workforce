# ADR-0017 | Sincronização real: app de campo → backend hospedado → painel

## Contexto

`interface_campo` (PWA publicado no Netlify, `sgoworkforce.netlify.app`) e
`painel` (Streamlit) eram ilhas isoladas: a interface grava só em IndexedDB
do navegador (zero chamadas de rede, ADR-0004) e o painel só lê arquivos
locais em `dados_locais/jornadas` (`RepositorioJornadaArquivo`, ADR-0002).
Isso já estava registrado como pendência no ADR-0003 ("não existe API real
ainda") e como decisão pendente #10 em `docs/23_DECISOES_PENDENTES.md`
("Hospedagem e autenticação do piloto").

Pedido do responsável pelo produto (2026-07-26): testar o app de campo
(inclusive com o simulador de tempo do ADR-0016) e ver os dados aparecerem
de verdade no painel — sincronização automática real, não uma ponte
manual de exportar/importar arquivo.

## Decisão

Três perguntas em aberto foram respondidas explicitamente pelo responsável
pelo produto antes de qualquer código (não inventadas pelo agente, conforme
`docs/23_DECISOES_PENDENTES.md` exige):

1. **Hospedagem do backend: Render.com.** Free tier, deploy automático a
   partir do GitHub, mesmo padrão já usado no Netlify (frontend) e
   Streamlit Community Cloud (painel).
2. **Persistência: banco de dados hospedado (Postgres), não arquivo local
   efêmero.** Evita perder dados de teste a cada reinício/redeploy do
   serviço gratuito.
3. **Autenticação: token fixo simples.** Uma variável de ambiente
   (`SYNC_TOKEN`) comparada com o header `X-Sync-Token` em toda chamada.

**Isso resolve a decisão pendente #10 no escopo do piloto** — não é o
desenho de autenticação final de produção. Ressalva de segurança
explícita: o token fica dentro do JavaScript público do site no Netlify
(`interface_campo/js/configSincronizacao.js`) — **não é confidencial**
contra alguém que inspecione o código-fonte da página; só evita que
alguém que descubra a URL do backend por acaso grave dados aleatórios
nela.

### Arquitetura

```
interface_campo (Netlify, JS)  --POST /jornadas (header X-Sync-Token)-->  Backend FastAPI (Render)  <-->  Postgres (Render)
painel (Streamlit Cloud)       --GET  /jornadas (header X-Sync-Token)-->  Backend FastAPI (Render)
```

O backend é a única fonte de verdade para dado sincronizado. O painel
mantém a leitura de arquivo local como opção (útil para rodar tudo sem
depender de rede) e ganha uma segunda fonte, "API (nuvem)".

### Peças novas

1. **`src/workforce_api/repositorio_postgres.py`** —
   `RepositorioJornadaPostgres`, mesma forma pública de
   `RepositorioJornadaArquivo` (`salvar`/`carregar`/`listar_ids`/`listar_abertas`),
   reaproveitando `workforce_storage.serializacao.jornada_para_dict`/`jornada_de_dict`
   (as mesmas funções já testadas usadas em todo o resto do sistema).
   Schema mínimo — a jornada inteira vira uma linha
   `jornadas(id UUID PRIMARY KEY, dados JSONB, atualizado_em TIMESTAMPTZ)`,
   sem modelar cada campo relacionalmente (mesmo espírito provisório do
   ADR-0002). `salvar()` faz upsert (`INSERT ... ON CONFLICT (id) DO UPDATE`),
   mesma garantia de idempotência do ADR-0003 — reenviar a mesma jornada
   nunca duplica.
2. **`src/workforce_api/app.py`** — FastAPI com `POST /jornadas` (recebe,
   valida com `jornada_de_dict()`, salva), `GET /jornadas` (lista tudo, o
   painel consome), `GET /saude` (healthcheck sem token, para o Render
   verificar liveness). `exigir_token`: **fail closed por requisição** —
   se `SYNC_TOKEN` não estiver configurada no servidor, toda chamada
   autenticada recebe `503`, nunca é aceita "por omissão" (regra de ouro 9
   do CLAUDE.md). O repositório é injetado via `Depends(obter_repositorio)`,
   permitindo testar a API inteira com `RepositorioJornadaArquivo` (já
   testado) num diretório temporário, sem precisar de Postgres real — ver
   `tests/test_workforce_api.py`.
3. **`interface_campo/js/configSincronizacao.js`** — `URL_BASE_API` e
   `TOKEN_SINCRONIZACAO` como constantes simples (placeholder até o
   responsável pelo produto preencher com os valores reais do Render).
4. **`interface_campo/js/sincronizacao.js`** — `paraPayloadSincronizacao`
   (função pura, converte o objeto JS camelCase para o mesmo contrato de
   `jornada_para_dict()`; sempre manda `eventos_secundarios: []` e
   `dados_falha: null` porque o motor JS ainda não tem esses campos,
   ADR-0004) e `sincronizar()` (POST best-effort — **nunca lança**, uma
   falha de rede não pode impedir o registro local do evento, mesmo
   princípio de offline-first do resto do app).
5. **`interface_campo/js/app.js`** — dispara `sincronizar()` best-effort
   depois de cada `persistir()` local, mostra "Sincronizado" / "Não
   sincronizado" na tela, e ganhou um botão manual "Sincronizar agora".
6. **`painel/dados.py`** — `carregar_jornadas_via_api(url, token)`, mesma
   assinatura de retorno de `carregar_jornadas()` (jornadas válidas +
   lista de erros), usando `requests` e `jornada_de_dict()`.
7. **`painel/app.py`** — seletor "Fonte de dados": Arquivo local ou API
   (nuvem), estado em `st.session_state` (regra de ouro 10 — nunca esconder
   widget stateful entre reruns).

## O que fica deliberadamente fora de escopo

- **Fila de retry automática com backoff no lado JS**: `sincronizar()` é
  uma tentativa única por evento, mais o botão manual "Sincronizar agora".
  Uma fila persistente (como `workforce_sync.FilaSincronizacao` já existe
  no lado Python, mas para um cliente Python, não para o navegador) fica
  para um incremento futuro se o volume de falhas de rede em campo
  justificar.
- **Autenticação de usuário real / múltiplos tokens**: um único token
  fixo compartilhado, adequado para um piloto testado por uma pessoa.
- **Migração de schema versionada no Postgres**: `CREATE TABLE IF NOT EXISTS`
  simples; sem ferramenta de migração (Alembic etc.) neste incremento.
- **Sincronização de eventos individuais**: a granularidade continua sendo
  a jornada inteira, mesma decisão do ADR-0003.

## Validação de qualidade realizada

- `pytest tests/test_workforce_api.py` (7 testes): token ausente/errado →
  401; sem `SYNC_TOKEN` configurada → 503; POST válido aparece no GET
  seguinte; POST repetido faz upsert sem duplicar; POST malformado → 400;
  `/saude` sem token → 200. Repositório injetado é
  `RepositorioJornadaArquivo` (já testado), não Postgres real.
- `pytest` completo do projeto: 179/179 (nenhuma regressão).
- `node --test tests/js` (inclui `sincronizacao.test.mjs`, 6 casos novos):
  conversão de payload fiel ao contrato Python, `sincronizar()` nunca
  lança em falha de rede, reporta erro HTTP corretamente, reporta sucesso
  e envia o token no header esperado.
- `node --check` em todos os arquivos JS tocados/criados.
- `CACHE_VERSAO` do service worker incrementada (`v5` → `v6`).

## Validação NÃO realizada — depende de contas que só o responsável pelo produto tem acesso

- **Conexão real com Postgres**: não há servidor Postgres disponível neste
  ambiente de desenvolvimento. `RepositorioJornadaPostgres` foi validado
  por leitura de código e pela mesma cobertura indireta que
  `jornada_para_dict`/`jornada_de_dict` já têm — não por um teste de
  integração rodando contra um banco de verdade.
- **Deploy real no Render** (backend + Postgres) e **configuração real do
  Streamlit Cloud** (secrets `SYNC_API_URL`/`SYNC_TOKEN`).
- **Chamada de ponta a ponta do site publicado no Netlify contra o backend
  publicado**: CORS, HTTPS misto e o comportamento real do
  `fetch()` em produção só podem ser confirmados depois do deploy.

Isso segue exatamente o padrão já registrado nos ADRs anteriores (ADR-0004,
ADR-0016) para o que este ambiente de desenvolvimento não consegue validar
sozinho — fica como tarefa explícita do responsável pelo produto antes de
usar os dados sincronizados para qualquer decisão.

### Atualização: painel travado em loop de deploy no Streamlit Cloud (2026-07-26)

O responsável pelo produto reportou que o deploy do painel no Streamlit
Community Cloud ficava preso num ciclo — clonava o repositório, processava
dependências (`Resolved 61 packages`) e reiniciava o processo inteiro do
zero, sem nunca chegar a subir o servidor Streamlit nem mostrar um erro
explícito.

**Primeira hipótese (parcialmente certa, mas não a causa raiz)**:
`requirements.txt` era compartilhado pelos dois serviços (painel no
Streamlit Cloud e backend no Render), então o painel tentava instalar
`fastapi`, `uvicorn` e `psycopg2-binary` — que ele nunca importa, já que
fala com o backend só por HTTP (`requests`). Corrigido separando em dois
arquivos: `requirements.txt` (painel) e `requirements-api.txt` (backend,
usado no build command do Web Service no Render). Essa separação é uma
melhoria válida por si só (build mais enxuto para os dois lados), mas
**não resolveu o travamento** — o painel continuou preso no mesmo ponto
mesmo já sem essas três dependências (log foi de 61 para 54 pacotes
resolvidos, mesmo loop).

**Causa raiz confirmada**: a versão do Python usada pelo Streamlit Cloud
para esse app era `3.14.6` — recém-lançada demais para o ecossistema de
pacotes (pandas, Streamlit, Folium etc.) ter cobertura confiável de
wheels pré-compiladas, travando/demorando indefinidamente na etapa de
instalação (`uv pip install` nunca chegava a imprimir "Installed N
packages"). A versão do Python só pode ser escolhida na criação do app
(campo "Python version" em "Advanced settings"), não depois — não havia
essa opção nas configurações do app já criado. **Correção**: apagar o app
e recriá-lo do zero, desta vez fixando a versão em **3.12** nas Advanced
settings. Confirmado pelo responsável pelo produto em 2026-07-26: com
Python 3.12, o deploy completou e o painel subiu normalmente.

**Recomendação para deploys futuros deste projeto** (painel ou qualquer
outro serviço Python): sempre fixar explicitamente a versão do Python nas
Advanced settings ao criar o app no Streamlit Cloud (ou o equivalente nas
outras plataformas) em vez de aceitar o padrão da plataforma - o padrão
pode mudar para uma versão muito recente antes do ecossistema de pacotes
acompanhar.

## Alternativas consideradas

- **Ponte manual de exportar/importar JSON** (proposta inicialmente,
  antes desta decisão): mais simples, sem hospedagem nova, mas não é
  sincronização automática — rejeitada porque o pedido explícito era ver
  o comportamento em tempo real.
- **Persistência em arquivo local no próprio backend** (em vez de
  Postgres): mais rápida de implementar, mas o responsável pelo produto
  preferiu persistência mais robusta (dados sobrevivem a reinício do
  serviço gratuito do Render).
- **painel lendo o Postgres diretamente** (credenciais de banco no
  Streamlit Cloud): rejeitada em favor de painel e interface de campo
  serem os dois clientes HTTP do mesmo backend — evita duplicar segredo
  de banco em dois lugares e mantém uma única fonte de verdade sobre o
  formato dos dados.

## Instruções de deploy (ações do responsável pelo produto, fora deste editor)

1. Render → New → PostgreSQL (plano free) → copiar a "Internal Database URL".
2. Render → New → Web Service, repositório `jcopaz/SGO-Workforce`:
   - Build command: `pip install -r requirements-api.txt` (não
     `requirements.txt` — esse é o do painel, tem Streamlit/pandas/Folium
     que o backend não usa e só deixa o build mais pesado à toa).
   - Start command: `PYTHONPATH=src uvicorn workforce_api.app:app --host 0.0.0.0 --port $PORT`.
   - Variáveis de ambiente: `DATABASE_URL` (passo 1), `SYNC_TOKEN`
     (escolher uma string aleatória), `ORIGENS_PERMITIDAS`
     (`https://sgoworkforce.netlify.app,http://localhost:8000`).
3. Copiar a URL pública do backend.
4. Preencher `interface_campo/js/configSincronizacao.js` com essa URL e o
   mesmo `SYNC_TOKEN` — commit/push (Netlify redeploya sozinho).
5. Streamlit Cloud → Secrets: `SYNC_API_URL` e `SYNC_TOKEN` iguais aos do
   backend.

## Validação operacional

Ainda não realizada. Decisão de escopo-piloto, sujeita a revisão do
responsável pelo produto após o deploy real e o primeiro teste de ponta a
ponta com o site publicado.

## Data e responsáveis

- Data de registro: 2026-07-26.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), que decidiu explicitamente hospedagem,
  persistência e autenticação antes da implementação.
- Revisão pendente: deploy real (Render + Postgres + Streamlit Cloud) e
  teste de ponta a ponta com o site publicado no Netlify.
