# ADR-0026 | Reparo retroativo de `tipo_evento_secundario` (bug real de produção)

## Contexto

Teste manual real na interface de campo em produção (`sgoworkforce.netlify.app`
+ backend Render), relatado pelo responsável pelo produto em 2026-07-29:
ao abrir jornada e tentar "Iniciar deslocamento/espera/apoio" com o código
padrão `EE01 - Preparação para jornada`, o app travava permanentemente
com a mensagem "O tipo do evento secundário (DESLOCAMENTO/ESPERA/APOIO) é
obrigatório." — mesmo antes de qualquer outra ação, e sem nenhuma forma
de prosseguir a partir dali (a mensagem só é substituída na próxima
transição bem-sucedida, e nenhuma tentativa de iniciar evento secundário
tinha sucesso).

O leque de opções ao abrir a jornada (Iniciar atividade / Iniciar
atendimento de falha / Iniciar deslocamento-espera-apoio / Encerrar
jornada) já existia desde o ADR-0024, e o mesmo leque já reaparece
automaticamente depois de encerrar uma atividade (o `render()` de
`interface_campo/js/app.js` cai no mesmo ramo `else` sempre que não há
pausa/atividade/evento secundário ativos) — ou seja, o fluxo pedido pelo
responsável do produto ("ao iniciar a jornada deveria aparecer o leque...
e ao finalizar a atividade o leque também deveria aparecer") já estava
implementado. O problema real não era a ausência do leque, era este erro
travando qualquer tentativa de uso do bloco de evento secundário dentro
dele.

### Causa raiz

O ADR-0024 adicionou a coluna `tipo_evento_secundario` à tabela
`motivos_catalogo` via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS
tipo_evento_secundario TEXT NULL` — que cria a coluna mas **nunca
preenche dado retroativo**. O único caminho de código que preenchia essa
coluna era `_semear_se_vazio()`, que só roda quando a tabela está vazia.
Como a tabela `motivos_catalogo` em produção já existia desde o
ADR-0014/0019 (muito antes do ADR-0024), ela nunca esteve vazia depois do
ALTER — então os 15 códigos `evento_secundario` ficaram com
`tipo_evento_secundario = NULL` permanentemente. O próprio ADR-0024 já
registrava isso como risco explícito ("reseed dos 15 códigos via `POST
/catalogo` — ação manual pendente"), mas essa ação manual nunca foi
executada (mesma classe de problema que já tinha acontecido com a
reclassificação do ADR-0023, resolvida na época com 23 chamadas manuais
de `POST /catalogo`).

Do lado do app: `interface_campo/js/app.js::tipoEventoSecundarioParaCodigo`
lê `tipo_evento_secundario` de cada entrada do catálogo buscado do
backend (`catalogoMotivos.js::obterEventosSecundarios`). Com a coluna
NULL em produção, `tipo` chegava `undefined` em
`motor.iniciarEventoSecundario(agora, undefined, codigo)`, que
corretamente lança `EventoSecundarioTipoObrigatorioError` (o motor está
certo — a validação existe por design). O problema não é a validação, é
que nada nunca preenchia o dado que ela exige.

## Decisão

### 1. Backend se repara sozinho a cada boot (correção da causa raiz)

`src/workforce_api/repositorio_catalogo_postgres.py`: novo método
`RepositorioCatalogoPostgres._reparar_tipo_evento_secundario()`, chamado
em `__init__` logo depois de `_garantir_tabela()`/`_semear_se_vazio()`.
Roda um `UPDATE ... SET tipo_evento_secundario = %s WHERE codigo = %s AND
tipo_evento_secundario IS NULL` para cada um dos 15 códigos conhecidos
(mapeamento extraído de `catalogo_relatorio_1_manutencao()`, função pura
`_mapeamento_reparo_tipo_evento_secundario()` testável sem Postgres). A
cláusula `IS NULL` garante que nunca sobrescreve um valor já definido
(inclusive uma reclassificação manual futura via painel). Mesmo espírito
do `_ALTER_TABELA_SQL` já existente: idempotente, roda toda vez que o
repositório inicializa, sem depender de nenhuma ação manual pós-deploy.
Isso significa que o próximo boot do backend no Render (redeploy ou
reinício do processo) já resolve produção sozinho — mas depende desse
boot acontecer, e o histórico documentado (ver `CHANGELOG.md`,
2026-07-27) mostra que o "Auto-Deploy: On Commit" do Render já falhou
silenciosamente antes. **Ação manual pendente**: confirmar que o backend
subiu com o código deste ADR (Manual Deploy no Render se o auto-deploy
não disparar) — ver seção "Validação NÃO realizada".

### 2. Frontend nunca mais depende só do backend estar correto (defesa em profundidade)

`interface_campo/js/catalogoMotivos.js::obterEventosSecundarios` agora
aplica `repararTipoEventoSecundarioAusente` a cada entrada devolvida pelo
catálogo dinâmico (backend, cache local ou fallback offline): se
`tipo_evento_secundario` vier vazio/nulo, preenche a partir de um
mapeamento estático local (`TIPO_EVENTO_SECUNDARIO_CONHECIDO`, espelhando
a mesma tabela do ADR-0024 seção 1) — e nunca sobrescreve um valor que já
veio preenchido. Isso cobre três cenários que o reparo do backend sozinho
não cobre: (a) o backend ainda não foi reiniciado com este ADR quando o
colaborador usa o app; (b) o navegador tem em `localStorage` um cache do
catálogo salvo antes deste ADR (a mesma falha volta a acontecer
localmente até o próximo `GET /catalogo` bem-sucedido); (c) qualquer
ambiente offline no primeiro uso, que já dependia de
`CATALOGO_MINIMO_OFFLINE` — esse fallback já tinha os 15 tipos corretos
desde o ADR-0024 e continua funcionando sem mudança.

## Deliberadamente fora deste incremento

- Corrigir o auto-deploy do Render (causa raiz não identificada, ver
  `CHANGELOG.md` 2026-07-27) — continua fora do controle deste
  repositório.
- Qualquer nova política de migração de schema (ex.: tabela de versões,
  ferramenta de migração dedicada) — o padrão continua sendo `ALTER
  TABLE ... IF NOT EXISTS` + reparo idempotente no boot, mesmo espírito
  já estabelecido no ADR-0023/0024.
- O elapsed time mostrado na tela ("decorrido: Xh") durante os testes
  manuais não bateu exatamente com o relógio da captura de tela — isso é
  esperado quando o "Simulador de tempo" (ADR-0016) está em uso (a faixa
  de aviso "Simulação de tempo ativa" cobre esse caso); não foi tratado
  como bug porque não há evidência de que o simulador estivesse
  desligado nos testes relatados.

## Arquivos afetados

- `src/workforce_api/repositorio_catalogo_postgres.py`.
- `interface_campo/js/catalogoMotivos.js`.
- `tests/test_repositorio_catalogo_postgres.py` (novo).
- `tests/js/catalogoMotivos.test.mjs`.

## Validação de qualidade realizada

- `python -m py_compile` no módulo alterado: OK.
- `pytest`: 252/252 (era 249 antes deste ADR).
- `node --check` em `catalogoMotivos.js`: sintaxe válida.
- `node --test tests/js/*.test.mjs`: 104/104 (era 102 antes deste ADR).
- Reparo do backend testado com conexão/cursor falsos (sem Postgres real,
  mesma limitação já documentada no módulo): confirma que os 15 códigos
  corretos recebem `UPDATE` com a cláusula `IS NULL`, e que nenhum outro
  código é tocado.
- Reparo do frontend testado reproduzindo exatamente o payload que o
  backend não migrado devolvia (`tipo_evento_secundario: null` nos 15
  códigos) e confirmando que `obterEventosSecundarios` nunca mais deixa
  passar um evento sem tipo, sem sobrescrever um tipo que já veio
  preenchido.

## Validação NÃO realizada

- Teste manual em navegador/celular real após o deploy desta correção —
  mesma limitação de sempre (sem acesso a navegador/celular físico neste
  ambiente).
- Confirmar que o backend em produção (Render) efetivamente reiniciou com
  este código e que o reparo rodou de fato contra o Postgres real — não
  verificável deste ambiente (sem acesso à rede de produção). Se o
  auto-deploy do Render não disparar sozinho (histórico conhecido), é
  necessário "Manual Deploy" no painel do Render.

## Data e responsáveis

- Data de registro: 2026-07-30.
- Registrado por: Claude Code, a partir de teste manual relatado por
  j.copaz@hotmail.com em 2026-07-29 (capturas de tela da interface de
  campo em produção mostrando o erro travado).
