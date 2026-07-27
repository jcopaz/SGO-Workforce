# ADR-0021 | Atendimento de falha na interface de campo

## Contexto

O motor de domínio suporta atendimento de falha desde o Incremento 6
(`workforce_core/engine.py::iniciar_atendimento_falha`/`registrar_dados_falha`),
mas isso nunca chegou na interface de campo: não havia botão, não havia
formulário, e o motor JS espelhado (`motorJornada.js`) nem tinha esses
métodos (ADR-0004 já registrava isso como fora de escopo na época).

Pedido do responsável pelo produto: uma opção "Atendimento de falha" no
app de campo, com nota, identificação do ativo, sintoma (lista RASF),
objeto (lista RASF), observações/causa, e trava de encerramento até tudo
preenchido, com aviso visível. **Fora deste incremento** (tamanho):
captura de GPS no preenchimento, upload de foto e transferência de
atendimento entre colaboradores ("Falha não Concluída") — ficam para
incrementos seguintes.

## Decisão

### 1. Campo novo e simplificação de campos obrigatórios (decisão de negócio do responsável pelo produto, 2026-07-27)

Antes deste ADR, `encerrar_atividade` exigia 6 campos:
nota/ativo/sintoma/**causa**/**ação**/observação (`docs/27_ALINHAMENTO_OFICIAL...`
seção 3.5). O responsável pelo produto decidiu, ao ser perguntado
explicitamente sobre o campo "ação" (que seu pedido novo não citava):
**unificar `causa`, `ação` e `observação` em um único campo livre,
rotulado "Observações/Causa" na tela**, e adicionar um campo novo,
**`objeto`** (componente causador, catálogo RASF).

Nova lista de campos obrigatórios (`workforce_core/engine.py::CAMPOS_OBRIGATORIOS_FALHA`,
renomeada de `_CAMPOS_OBRIGATORIOS_FALHA` — antes privada, agora pública
para `workforce_export/csv_exportacao.py` importar em vez de duplicar,
ver item 4): **nota, ativo, sintoma, objeto, observação**.

`causa` e `acao` continuam existindo em `DadosFalha` (não removidos, para
não quebrar o formato de persistência de registros já gravados antes
deste ADR) mas não são mais exigidos nem aparecem no formulário da
interface de campo.

### 2. Catálogo RASF servido pelo backend, sem tabela nova no Postgres

`GET /catalogo-rasf` (`src/workforce_api/app.py`, mesma autenticação por
token dos demais endpoints) lê `catalogos/sintomas.csv` (53 itens) e
`catalogos/componentes_causadores.csv` (148 itens) via
`workforce_storage.catalogo_rasf` (já existente, Incremento 6) e retorna
só os valores ativos. **Sem tabela no Postgres**, ao contrário do
catálogo de motivos (ADR-0019): esses catálogos RASF ainda não têm fluxo
de edição/governança definido (`docs/09_ATENDIMENTO_FALHAS_RASF.md` já
dizia isso) — não faz sentido administrá-los pelo painel ainda, só servir
o que já existe nos CSVs versionados no repositório.

### 3. Motor JS ganha atendimento de falha

`interface_campo/js/motorJornada.js`: `iniciarAtendimentoFalha`,
`registrarDadosFalha` e a validação de campos obrigatórios em
`encerrarAtividade` (mesma ordem de validação do Python: timestamp antes,
depois campos de falha, só então marca encerrada). `entidades.js` ganhou
`novoDadosFalha()`; `erros.js` ganhou `AtendimentoFalhaNaoAtivoError` e
`AtendimentoFalhaCamposObrigatoriosError`.

`interface_campo/js/catalogoRasf.js` (novo): mesmo padrão de cache
offline de `catalogoMotivos.js` (ADR-0019) — busca uma vez, guarda em
`localStorage`, cai num fallback mínimo (poucas opções, deixando claro
que não é a lista completa) se nunca conseguiu buscar.

### 4. Tela do app de campo

- Estado "jornada aberta, sem atividade": novo botão **"Iniciar
  atendimento de falha"**.
- Enquanto a atividade ativa tem `dadosFalha`, a tela mostra o formulário
  (nota, ativo — texto livre; sintoma, objeto — `<select>` do catálogo
  RASF; observações/causa — texto livre) com um **aviso persistente**
  visível o tempo todo ("a atividade só pode ser encerrada depois de
  preencher..."), não um alerta que aparece e some. Cada campo salva ao
  perder o foco/mudar (`registrarDadosFalha`), sem duplicar a validação
  de completude no JS — quem decide se pode encerrar é sempre o motor
  (`encerrarAtividade`), mesmo caminho de erro (`ErroDominio` →
  mensagem na tela) já usado no resto do app.
- Botão fica rotulado "Concluir atendimento" em vez de "Encerrar
  atividade" quando há `dadosFalha`, mesmo `onClick`.
- Pausa continua disponível durante o atendimento de falha (regra do
  motor não distingue o tipo de atividade para pausa).

### 5. Correção de uma duplicação de regra encontrada durante o ajuste

`workforce_export/csv_exportacao.py` tinha sua **própria cópia** da
tupla de campos obrigatórios (`_CAMPOS_OBRIGATORIOS_FALHA`, usada para
marcar a coluna `completo` do CSV/XLSX de falhas) — desatualizada assim
que a regra mudou aqui. Corrigido importando
`workforce_core.engine.CAMPOS_OBRIGATORIOS_FALHA` (agora pública) em vez
de duplicar. Coluna `objeto` adicionada às exportações CSV e XLSX de
falhas (`CAMPOS_FALHAS`, `_aba_falhas`, dicionário de dados).

## Fora de escopo (D2/D3/D4, próximos incrementos)

- Captura de GPS no preenchimento (Geolocation API do navegador — não
  existe nenhuma captura de geolocalização na interface de campo hoje).
- Upload de foto (Supabase Storage — credenciais já em mãos do
  responsável pelo produto, mas a integração fica para quando entrarmos
  nesse pedaço).
- Botão "Falha não Concluída" / transferência de atendimento entre
  colaboradores.

## Validação de qualidade realizada

- `tests/test_atendimento_falha.py`: atualizado para a nova regra (9
  testes, incluindo um novo confirmando que `causa`/`acao` são opcionais).
- `tests/test_serializacao_catalogo.py`, `tests/test_consolidacao.py`,
  `tests/test_exportacoes.py`, `tests/test_integracao_sgo.py`,
  `painel/dados.py::gerar_jornadas_exemplo`: todos os call sites de
  `registrar_dados_falha` atualizados para a nova assinatura.
- `tests/test_workforce_api.py`: 2 novos testes de `/catalogo-rasf`
  (token obrigatório, retorno com os 53 sintomas e 148 componentes reais).
- `tests/js/motorJornada.test.mjs`: 9 novos casos espelhando
  `test_atendimento_falha.py`.
- `tests/js/catalogoRasf.test.mjs` (novo, 5 casos): mesmo padrão de
  `catalogoMotivos.test.mjs`.
- `pytest` completo: 200/200. `node --test tests/js`: 49/49.
- Backend local (`uvicorn`, sem Postgres): `GET /catalogo-rasf` testado
  manualmente contra os CSVs reais (53 sintomas, 148 componentes).

## Validação NÃO realizada

Mesma limitação de sempre: teste manual em navegador do fluxo completo
(selecionar atendimento de falha, ver o aviso, preencher os campos,
tentar concluir sem preencher tudo, preencher tudo e concluir) não foi
feito neste ambiente (sem navegador disponível). Fica pendente antes de
qualquer piloto real.

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), que decidiu explicitamente a simplificação de
  campos obrigatórios (causa/ação → observações unificadas) antes da
  implementação.
- Revisão pendente: teste manual em navegador/celular real.
