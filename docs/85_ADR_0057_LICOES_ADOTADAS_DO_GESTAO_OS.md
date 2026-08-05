# ADR-0057 | Lições adotadas da leitura completa do Gestão_OS

## Contexto

Depois da leitura completa do app irmão Gestão_OS (registrada em
memória de sessão, `project-analise-gestao-os-2026-08-05`), pedido
explícito do responsável do produto: "registre tudo o que você aprendeu
e implemente as coisas que entende ser de grande valia aqui, e adote a
mesma postura de registro de erros e afins."

Do levantamento completo, a maioria dos padrões bons encontrados exigia
conceitos que o Workforce ainda não tem (autenticação de usuário,
geofence/pátio, pool de conexões) - mudanças arquiteturais maiores que
não cabem em "implemente o que for de grande valia" sem uma decisão de
negócio própria. Três itens, porém, eram lacunas técnicas puras,
seguras de aplicar sem nenhuma decisão nova:

## Decisão

### 1. Sanitização de nome de arquivo antes do upload (Supabase Storage)

`src/workforce_api/supabase_storage.py::enviar_foto` montava o caminho
do objeto (`f"{uuid4()}-{nome_arquivo}"`) direto com o nome de arquivo
recebido do cliente, sem nenhuma normalização. Bug real já documentado
no Gestão_OS (mesma integração Supabase Storage): nome de arquivo
acentuado (comum em foto com nome automático do celular) faz o Storage
recusar o upload com HTTP 400.

Nova `_sanear_nome_arquivo`: normaliza Unicode (NFKD, separa a letra do
acento), codifica em ASCII descartando o que sobrar do acento, e
substitui qualquer caractere fora de `[A-Za-z0-9._-]` por `_`. Nome
vazio depois da sanitização (ex.: nome só de emoji) cai no fallback
`"foto.jpg"`.

### 2. `dry_run` seguro por padrão em `POST /pulsos/expurgar`

Lição direta do Gestão_OS: endpoints destrutivos (lá, limpeza de
evidências) sempre com `dry_run=True` por padrão, prova antes de apagar
de verdade. O endpoint de expurgo do Workforce (ADR-0054) apagava
direto, sem nenhuma proteção do lado da API - a única barreira era a
confirmação no painel.

`POST /pulsos/expurgar` ganhou `dry_run: bool = True`: por padrão só
conta quantos pulsos seriam apagados (`RepositorioPulsosGpsPostgres.contar_pulsos_anteriores_a`/
`RepositorioPulsosGpsArquivo.contar_pulsos_anteriores_a`, novos,
espelham a query de `apagar_pulsos_anteriores_a` trocando `DELETE` por
`SELECT COUNT(*)`), retornando `{"dry_run": true, "seriam_apagados": N}`.
Só apaga de verdade com `dry_run=false` explícito, retornando
`{"dry_run": false, "apagados": N}` - **mudança de contrato** em relação
ao ADR-0054 (a resposta antes era só `{"apagados": N}`), atualizado nos
testes e no botão do painel.

`painel/telas/configuracoes_catalogo.py` ganhou um botão novo "🔍
Pré-visualizar (não apaga nada)" - chama sem `dry_run` (fica no padrão
seguro), mostra a contagem via `st.info`, nunca apaga. O botão "🗑️
Expurgar pulsos antigos" (já existia, com a confirmação por checkbox do
ADR-0054) passou a enviar `dry_run=False` explicitamente - é o único
caminho que apaga de verdade.

### 3. Log de lições operacionais (`docs/84_LICOES_OPERACIONAIS_E_INCIDENTES.md`)

Inspirado em `Agente/09_APRENDIZADOS_E_ERROS.md` do Gestão_OS: um log
vivo de incidentes reais (causa raiz → correção → lição), separado dos
ADRs individuais (que já documentam o incidente em detalhe, mas
espalhado - o log consolida o padrão que se repete entre eles). Primeira
versão já povoada retroativamente com 7 incidentes reais desta sessão e
anteriores (timezone, EE22 esquecido, acordeão dos blocos, calendário
removido, qualidade de GPS nunca avaliada, CLAUDE.md desatualizado,
bug de billing do Netlify), fechando com uma seção "Lições
transversais". `CLAUDE.md` (seção "Forma de trabalho") passou a citar
esse arquivo como prática contínua daqui pra frente.

## Deliberadamente fora deste ADR (avaliado, não implementado)

- **Pool de conexões Postgres** com self-healing (padrão bom encontrado
  no Gestão_OS) - o Workforce hoje abre uma conexão nova por chamada em
  cada repositório Postgres (`psycopg2.connect`), sem pool. Mudança
  arquitetural real (concorrência, lifecycle compartilhado sob FastAPI),
  não uma lacuna técnica pequena - registrada como recomendação futura
  na memória de sessão, não implementada sem pedido explícito.
- **RBAC estruturado, autenticação de usuário, geofence/pátio fixo** -
  todos exigem conceito de domínio que o Workforce ainda não tem
  (usuário autenticado, pátio como entidade) - fora de escopo de
  "aplicar lição técnica", são decisões de produto já registradas como
  pendentes em `docs/23_DECISOES_PENDENTES.md`.
- **Reproduzir a pasta `Agente/` inteira** (13 arquivos de contexto pra
  IA) - só o pedaço de maior valor (log de lições) foi adotado.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados.
- `pytest` completo: 399 passed (8 testes novos: 2 em
  `test_supabase_storage.py` para sanitização, 3 em `test_gps.py` para
  `contar_pulsos_anteriores_a`, 2 atualizados + 1 novo em
  `test_workforce_api.py` para `dry_run`, 1 novo + 1 atualizado em
  `test_configuracoes_catalogo_painel.py`).

## Validação NÃO realizada

- Teste em celular real do botão de pré-visualização (mesma limitação de
  sempre).

## Arquivos afetados

- `src/workforce_api/supabase_storage.py` (`_sanear_nome_arquivo`).
- `src/workforce_api/app.py` (`dry_run` em `POST /pulsos/expurgar`).
- `src/workforce_api/repositorio_pulsos_postgres.py`,
  `src/workforce_storage/repositorio_pulsos_gps.py`
  (`contar_pulsos_anteriores_a`).
- `painel/telas/configuracoes_catalogo.py` (botão de pré-visualização,
  `dry_run=False` explícito no botão de apagar).
- `docs/84_LICOES_OPERACIONAIS_E_INCIDENTES.md` (novo).
- `CLAUDE.md` (referência ao log de lições).
- `tests/test_supabase_storage.py`, `tests/test_gps.py`,
  `tests/test_workforce_api.py`, `tests/test_configuracoes_catalogo_painel.py`.

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
