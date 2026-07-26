# ADR-0019 | Catálogo dinâmico de motivos (admin no painel → backend → app de campo)

## Contexto

Até este incremento, o catálogo de motivos de pausa da interface de campo
era **hardcoded** em `interface_campo/js/app.js`
(`MOTIVOS_PAUSA_RELATORIO_1`, só 5 dos 23 códigos reais do Relatório de
Atividades Diárias de Manutenção — ver ADR-0014). Qualquer novo motivo ou
mudança de categoria exigia uma sessão de código e um novo deploy do app
de campo. Pedido do responsável pelo produto (item 3 do roteiro
combinado depois do ADR-0018): uma tela de administração no painel para
cadastrar/editar motivos, que a interface de campo passa a consumir sem
precisar de deploy novo.

Este incremento reaproveita a infraestrutura já paga/hospedada do
ADR-0017 (mesmo backend FastAPI no Render, mesmo Postgres, mesmo token de
sincronização) — não propõe nenhuma hospedagem nova.

## Decisão

### 1. `EntradaCatalogo` ganha `tipo_registro` e `ativo`

`src/workforce_core/catalogo.py`: dois campos novos com default
(`tipo_registro: str = "pausa"`, `ativo: bool = True`), que não quebram
nenhum construtor existente. `catalogo_relatorio_1_manutencao()` passa a
popular `tipo_registro` de verdade a partir de `_RELATORIO_1_ENTRADAS`
(antes esse dado só existia na tupla interna, não no objeto) — nenhuma
classificação de negócio nova foi inventada, só formalizada a que já
existia.

### 2. Persistência: nova tabela no mesmo Postgres do ADR-0017

`src/workforce_api/repositorio_catalogo_postgres.py`
(`RepositorioCatalogoPostgres`), mesmo espírito de
`RepositorioJornadaPostgres`: uma linha por motivo
(`motivos_catalogo(codigo PK, descricao, categoria, classificacao_hh,
tipo_registro, ativo, atualizado_em)`), upsert por código (idempotente,
mesma garantia do ADR-0003). **Sem `DELETE` físico** — "desativar" é
`ativo=false`, nunca apaga (mesmo princípio de
`docs/17_SEGURANCA_GOVERNANCA.md`, "correção nunca apaga o evento
original"). **Seed automático**: se a tabela estiver vazia na primeira
inicialização, popula com os 23 códigos reais de
`catalogo_relatorio_1_manutencao()` — a interface de campo nunca vê um
catálogo vazio.

### 3. Endpoints `GET`/`POST /catalogo`

`src/workforce_api/app.py`: mesmo padrão de autenticação/injeção de
`/jornadas` (token `X-Sync-Token`, repositório via `Depends`, testável
sem Postgres real). `GET /catalogo` só retorna motivos ativos.

### 4. Interface de campo busca o catálogo dinamicamente, com fallback offline

`interface_campo/js/catalogoMotivos.js` (novo): `obterMotivosPausa()` —
1. Tenta `GET /catalogo`; sucesso → filtra `tipo_registro === "pausa" &&
   ativo`, grava em cache local (`localStorage`) e retorna.
2. Falha de rede → usa o cache da última consulta bem-sucedida.
3. Nunca teve cache (primeiro uso já offline) → usa uma lista mínima
   embutida (os mesmos 5 códigos que já estavam hardcoded) — o seletor de
   pausa nunca fica vazio.

`app.js`: `iniciar()` busca `motivosPausa` uma vez (em paralelo com
`listarJornadasAbertas()`) antes do primeiro `render()`;
`criarSeletorMotivoPausa()` itera essa lista em vez da constante
removida.

### 5. Administração no painel

`painel/pages/4_Catalogo.py` (novo): só funciona via API (o backend é a
única fonte de verdade para o catálogo — não existe "catálogo em arquivo
local"). Reaproveita as mesmas chaves de `st.session_state`
(`painel_api_url`/`painel_api_token`) já usadas na página principal — se
o usuário já configurou lá, não precisa preencher de novo. Tabela de
leitura + formulário de criar/editar (upsert por código digitado).

**Aviso explícito na tela**: editar um motivo já usado em jornadas
antigas muda a classificação delas retroativamente — não há
versionamento de catálogo neste incremento (decisão consciente, não
escondida).

## Fora de escopo (explícito)

- Versionamento/histórico de catálogo.
- Fluxo de aprovação de quem pode editar (sem login ainda, ADR-0018 —
  protegido só pelo token de sincronização já aceito).
- Pré-preencher o formulário do painel ao escolher um código existente
  para editar (por ora, o admin lê os valores atuais na tabela acima e
  redigita) — simplificação deliberada para o piloto técnico.
- Sincronizar catálogo de `evento_secundario`/`atividade` para alguma
  tela na interface de campo — esses tipos ainda não têm UI própria lá
  (ADR-0004); o admin pode cadastrá-los, mas só os `tipo_registro="pausa"`
  aparecem em algum lugar do app hoje.

## Validação de qualidade realizada

- `tests/test_catalogo_relatorio_1.py`: novo teste de `tipo_registro`
  carregado corretamente por `EntradaCatalogo`.
- `tests/test_serializacao_catalogo.py` (novo): round-trip de
  `entrada_catalogo_para_dict`/`entrada_catalogo_de_dict`, com e sem
  categoria, defaults para campos ausentes (compatibilidade retroativa).
- `tests/test_workforce_api.py`: 5 novos testes de `/catalogo` (token
  ausente → 401, criar aparece no GET seguinte, upsert não duplica,
  inativos omitidos do GET, payload malformado → 400) — repositório fake
  em memória, sem Postgres real.
- `tests/js/catalogoMotivos.test.mjs` (6 casos): fallback mínimo sem
  configuração/cache, sucesso grava cache e filtra pausa+ativo, falha de
  rede usa cache anterior, erro HTTP usa cache anterior, não configurado
  com cache usa cache (não o fallback mínimo), token enviado no header.
- `pytest` completo: 197/197. `node --test tests/js`: 36/36.

## Validação NÃO realizada

Mesma limitação de sempre (ADR-0004, ADR-0016, ADR-0017, ADR-0018): sem
Postgres real neste ambiente, o `CREATE TABLE`/seed automático de
`RepositorioCatalogoPostgres` não foi exercitado contra um banco de
verdade — só por leitura de código e pelos testes de API com repositório
falso. Também pendente: teste de ponta a ponta (cadastrar um motivo no
painel publicado → aparecer no seletor de pausa do app de campo
publicado, depois de o navegador buscar o catálogo de novo).

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
- Revisão pendente: teste de ponta a ponta com os serviços publicados
  (Render + Streamlit Cloud + Netlify).
