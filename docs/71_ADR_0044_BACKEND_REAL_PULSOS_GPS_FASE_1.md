# ADR-0044 | Backend real de pulsos GPS - Fase 1 da captação de geolocalização

## Contexto

Sequência de ADR-0042 (levantamento de lacunas) e ADR-0043 (decisões de
negócio) desta mesma sessão. A lacuna concreta identificada: o motor de
domínio de pulsos GPS (`PulsoGps`, avaliação de qualidade, repositório
local) existe e é testado desde o ADR-0007, mas nunca foi alimentado por
dado real - não existe endpoint de pulsos no backend hospedado, nem o
painel lê pulsos de lá.

Investigação confirmou que `src/workforce_sync/` (sincronizador Python com
cursor/lote) nunca foi conectado a nada real - é um protótipo de algoritmo
isolado, já que a interface de campo é toda JavaScript. O caminho real de
integração é replicar o padrão já usado e testado para `/jornadas`.

Este ADR cobre só a **Fase 1**: backend (`/pulsos` no FastAPI + tabela
Postgres) e painel (mapa operacional lendo de lá). Não depende de celular
real - inteiramente testável neste ambiente. A Fase 2 (captação periódica
na interface de campo, fila offline, "GPS obrigatório") fica para uma
sessão futura que consiga validar em dispositivo real.

## Decisão

### 1. `src/workforce_storage/repositorio_pulsos_gps.py` - `gravar_lote` + correção de dois bugs reais

Adicionado `gravar_lote(pulsos)` (chama `gravar_pulso` por item) para
`RepositorioPulsosGpsArquivo` ter a mesma forma pública do novo repositório
Postgres (mesmo espírito de `RepositorioJornadaArquivo`/
`RepositorioJornadaPostgres`).

Os próprios testes escritos para o endpoint novo (usando este repositório
como dublê) revelaram **dois bugs reais** em `ler_pulsos`/
`ler_pulsos_com_erros`, que existiam desde o Incremento 7 mas nunca tinham
sido exercitados por um cenário de reenvio/lote fora de ordem:

- **Sem ordenação cronológica**: a leitura devolvia os pulsos na ordem em
  que foram gravados no arquivo, não na ordem do `timestamp_dispositivo`.
  Para uma gravação pulso-a-pulso isso nunca importou (a ordem de escrita
  já é cronológica), mas um lote que chega fora de ordem (rede lenta,
  reenvio) embaralharia a trajetória no mapa.
- **Sem deduplicação por id**: reenviar o mesmo pulso (ack perdido) grava
  uma segunda linha idêntica no arquivo - a leitura não deduplicava, então
  o pulso aparecia duas vezes.

Corrigido na leitura (não na escrita, que continua um `append` puro e
barato, de propósito - ver docstring da classe): `ler_pulsos_com_erros`
agora acumula os pulsos num dict por `id` (reenvio do mesmo id sobrescreve
- último grava vence, mesma semântica do `ON CONFLICT ... DO UPDATE` do
lado Postgres) e ordena o resultado por `timestamp_dispositivo` antes de
devolver. Os testes já existentes (`test_gravar_e_ler_pulsos_em_ordem`,
`test_linha_corrompida_nao_apaga_as_demais`) continuam passando sem
alteração - eles já gravavam em ordem cronológica e sem duplicata, então a
correção não muda o resultado esperado, só passa a garantir isso mesmo
quando não é o caso.

### 2. `src/workforce_api/repositorio_pulsos_postgres.py` (novo)

Espelha `repositorio_postgres.py` (`RepositorioJornadaPostgres`): `CREATE
TABLE IF NOT EXISTS pulsos_gps (id UUID PRIMARY KEY, jornada_id UUID NOT
NULL, dados JSONB NOT NULL, criado_em TIMESTAMPTZ DEFAULT now())` + índice
em `jornada_id` (mesma ausência de migração versionada, padrão já aceito
no ADR-0017). `gravar_lote` usa `psycopg2.extras.execute_values` numa
transação só (upsert por id, `ON CONFLICT ... DO UPDATE SET dados = ...` -
nunca toca `criado_em` de novo, um pulso é um fato imutável, diferente de
jornada). `ler_pulsos` ordena por `dados->>'timestamp_dispositivo'` no
próprio SQL.

### 3. `src/workforce_api/app.py` - `POST /pulsos` e `GET /pulsos`

Mesmo padrão de `/jornadas` (`Depends(exigir_token)`, fail-closed sem
`SYNC_TOKEN`/`DATABASE_URL`). Diferenças deliberadas do formato de
`/jornadas`:

- `POST /pulsos` recebe uma **lista** no corpo (não um objeto único) -
  reflete a decisão do ADR-0043: um POST por sincronização, com todos os
  pulsos acumulados offline desde a última vez.
- `GET /pulsos` exige `jornada_id` como query param **obrigatório** -
  nunca devolve pulsos de todo mundo de uma vez (mesmo padrão de `GET
  /continuacoes-falha?matricula=...`). `jornada_id` inválido → 400 (não
  500 - mesmo padrão de `consumir_continuacao_falha`).

### 4. `painel/dados.py` - `carregar_pulsos_via_api`

Mesma forma de `carregar_jornadas_via_api`: timeout de 60s (cold start do
Render free tier), retorna `(pulsos_validos, ids_com_erro)` - nunca
esconde erro de estrutura silenciosamente.

### 5. `painel/telas/mapa_operacional.py` - troca pra API

Mesmo padrão já aplicado a `dashboard.py`/`falhas.py` no ADR-0041: sem
`st.text_input` de diretório, `SYNC_API_URL`/`SYNC_TOKEN` só de secrets,
botão "Sincronizar dados" ao lado do título. **Botão "Gerar pulsos de
exemplo" removido** - escrevia num diretório local que a tela não lê
mais. Efeito esperado: a tela mostra "nenhum pulso encontrado" pra toda
jornada real até a Fase 2 (captação na interface de campo) existir - é o
estado real do sistema, não uma regressão desta mudança. Mensagem de
`st.info` atualizada para deixar isso explícito.

### 6. Testes novos

- `tests/test_gps.py`: `test_gravar_lote_grava_todos_os_pulsos`.
- `tests/test_workforce_api.py`: 9 casos novos para `/pulsos`, espelhando
  os já existentes para `/jornadas` (401/503/malformado/idempotência) +
  casos específicos de lote (ordem cronológica, filtro por `jornada_id`,
  `jornada_id` ausente → 422, inválido → 400). Usa
  `RepositorioPulsosGpsArquivo` como dublê via `app.dependency_overrides`,
  mesmo padrão de `/jornadas`.
- `tests/test_mapa_operacional_painel.py` (novo, `AppTest` end-to-end,
  mesmo padrão de `test_dashboard_painel.py`/`test_falhas_painel.py`) -
  confirma que `st_folium` (componente de terceiro) funciona sob `AppTest`
  em modo bare, incluindo o caminho feliz com pulsos reais construindo o
  mapa Folium de verdade.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: 318 passed (304 anteriores + 14 novos), sem
  regressão. Dois bugs reais de ordenação/deduplicação encontrados e
  corrigidos durante a escrita dos próprios testes desta ADR - não eram
  conhecidos antes.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- `test_mapa_operacional_painel.py` confirma que o mapa (incluindo
  `st_folium`, um componente de terceiro) roda sem exceção com pulsos
  reais construídos - risco que só um teste de ponta a ponta pega, não
  `py_compile` nem smoke test HTTP simples (que só exercita a página
  padrão "Visão geral", nunca o mapa).

## Validação NÃO realizada

- Conexão real com Postgres (sem servidor disponível neste ambiente,
  mesma ressalva de `repositorio_postgres.py`/ADR-0017) - `/pulsos` só
  testado com `RepositorioPulsosGpsArquivo` injetado.
- Teste visual em navegador real (mapa renderizando de verdade,
  alinhamento do botão "Sincronizar dados") - sandbox sem Playwright/
  Chromium, mesma limitação de sempre.

## Fora de escopo (Fase 2, sessão futura)

Captação periódica na interface de campo (`setInterval` chamando
`capturarPosicaoAtual` a cada 60s enquanto a jornada está aberta), novo
object store de pulsos no IndexedDB, fila offline, POST em lote no mesmo
momento em que a jornada já sincroniza hoje, e a trava "GPS obrigatório"
para iniciar/encerrar jornada/atividade. Precisa de teste em celular real.

## Arquivos afetados

- `src/workforce_storage/repositorio_pulsos_gps.py` (`gravar_lote` +
  correção de ordenação/deduplicação em `ler_pulsos_com_erros`).
- `src/workforce_api/repositorio_pulsos_postgres.py` (novo).
- `src/workforce_api/app.py` (`POST`/`GET /pulsos`).
- `painel/dados.py` (`carregar_pulsos_via_api`).
- `painel/telas/mapa_operacional.py` (fonte de dados fixa em API).
- `tests/test_gps.py`, `tests/test_workforce_api.py` (casos novos).
- `tests/test_mapa_operacional_painel.py` (novo).
