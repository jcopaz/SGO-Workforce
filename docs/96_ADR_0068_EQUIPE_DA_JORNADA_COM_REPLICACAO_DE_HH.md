# ADR-0068 | Equipe da jornada com replicação de HH pros colegas

## Contexto

O responsável do produto pediu, em 2026-08-12, um campo novo "Equipe
(quem mais participou desta atividade)" logo após a pergunta Online/
Offline (Etapa 2), onde o colaborador escolheria a matrícula de outros
colaboradores **cadastrados** que participaram junto - com o HH
replicado também pra eles.

Isso é diferente da aba "Equipe" já existente desde o ADR-0063: aquela é
por Atividade (dentro da Etapa 3), matrícula digitada em texto livre, e
o próprio ADR é explícito - "não afeta cálculo de HH, é só registro de
quem esteve presente". O pedido de agora muda os três pontos: nível de
jornada (não por atividade), seleção de uma lista real (não texto
livre), e replicação de HH de verdade.

Antes de codificar, levantei dois problemas reais com o responsável do
produto (via pergunta direta, não assumido sozinho):

1. **Não existe hoje nenhum "quadro de colaboradores cadastrados" no
   Workforce** - `matricula` sempre foi texto livre, sem validação
   contra nada. A única fonte real de cadastro é o `usuarios` do SGO, e
   o projeto tem a regra de ouro 1 (não acoplar ao SGO além do já
   decidido).
2. **Replicar HH esbarra na regra de ouro 4** (nunca dois eventos
   ativos incompatíveis pro mesmo colaborador) - se o colega também
   logar por conta própria no mesmo horário, duplica HH; e esbarra
   também na regra de ouro 2/3 (HH vem de evento real, nunca de
   declaração) - sem GPS/timestamp próprio do colega, o HH dele passa a
   existir só porque o dono da jornada apontou.

Perguntado via `AskUserQuestion`, o responsável do produto escolheu,
ciente dos dois riscos: **(1) puxar a lista do cadastro do SGO** (mais
acoplamento, aceito) e **(2) gerar jornada-espelho pro colega** (HH
replicado de verdade, risco de duplicidade/declaração aceito
conscientemente).

## Decisão

### 1. `GET /usuarios` novo no `api.py` do SGO (staged)

Protegido pela mesma `WORKFORCE_API_KEY_SECRET` de `/auth/validar` (sem
exigir senha de ninguém - só a chave de integração). Resposta
**deliberadamente mínima**: só `username`+`nome`, nunca `perfil`/
`escopo`/`governanca` (revelariam cargo/lotação) nem `senha_hash`. Nota
de privacidade registrada no próprio código: a chave é client-embedded
(nunca segredo de verdade, mesmo padrão já documentado em
`configSgo.js`), então qualquer pessoa que leia o JS público do
Workforce consegue listar nome+matrícula de todo colaborador cadastrado
- por isso a resposta minimiza o que é exposto.

### 2. `integracaoSgo.js::listarColaboradoresSgo()`

Mesmo padrão de `validarLoginSgo` (best-effort, `fetchImpl` injetável,
nunca lança). Chamada 1x, fire-and-forget, logo após o login da Etapa 1
validar com sucesso (`carregarEquipeSgo`, `app.js`) - nunca atrasa o
avanço pra Etapa 2. Se falhar (sem sinal, SGO fora do ar), a seção de
Equipe mostra um aviso e fica vazia - sempre opcional, nunca trava
"Iniciar jornada".

### 3. Seção "Equipe (opcional)" na Etapa 2, após a pergunta Online/Offline

Lista de checkboxes (`#listaEquipeJornada`, populada via JS), excluindo
sempre o próprio colaborador logado. Seleção lida em
`obterEquipeJornadaSelecionada()` e passada pra `MotorJornada`/
`novaJornada` como `equipeJornada: {matricula, nome}[]` - campo novo na
Jornada, ao lado de `modoApontamentoSgo`/`pacoteOfflineUrlSgo` (mesmo
padrão: decisão tomada uma vez, no início, nunca alterada depois).

### 4. Jornada-espelho gerada ao encerrar (`entidades.js::gerarJornadaEspelho`)

Só disparada **uma vez**, logo após "Encerrar jornada" aplicar com
sucesso (`motor.jornada.estado === "ENCERRADA"`) - nunca no meio do
turno, a jornada precisa estar completa antes de clonar. Pra cada membro
de `equipeJornada`: clona a jornada inteira (`structuredClone` - seguro
porque cada Jornada é um documento JSONB próprio no backend, sem
unicidade de id entre jornadas diferentes, então reaproveitar os ids
internos de atividade/pausa/evento não colide), troca `id` (novo, senão
colide com a jornada original ao sincronizar), `colaboradorMatricula`
(matrícula do colega), `equipeJornada: []` (uma jornada espelho nunca
gera outro espelho) e `espelhoDe` (matrícula de quem originou - marca de
auditoria local). Cada espelho é sincronizado via o mesmo
`Sincronizacao.sincronizar()` já usado pra jornada normal.

### 5. `espelhoDe`/`equipeJornada` NÃO entram no payload de sincronização

Mesmo motivo de `modoApontamentoSgo`: `workforce_storage.serializacao.jornada_de_dict`
(Python) só reconhece campos fixos do dataclass `Jornada` - enviar esses
dois campos extras seria inofensivo (a função ignora chaves
desconhecidas, confirmado lendo o código, não travaria nada), mas
**não persistiria** nada, porque o dataclass Python não tem onde
guardar. Ou seja: a marca de auditoria (`espelhoDe`) sobrevive só
**localmente**, no IndexedDB do aparelho de quem originou - uma vez
sincronizada, a jornada espelho fica **indistinguível de uma jornada
real** no backend/painel. Persistir essa marca de verdade no servidor
exigiria mudança no domínio Python também (`workforce_core.entities.Jornada`
+ serialização + repositório) - fora do escopo desta rodada, registrado
como pendência abaixo.

## Consequências e riscos aceitos (registrados, não resolvidos)

- **Risco de HH duplicado**: se o colega também logar por conta própria
  no Workforce no mesmo período, ele acumula o HH duplicado (o dele +
  o espelho). Não há verificação de sobreposição - decisão consciente do
  responsável do produto.
- **HH "por declaração"**: o HH do colega não vem de nenhum evento/GPS
  capturado por ele - vem inteiramente do que o dono da jornada
  declarou. Contraria a regra de ouro 2/3 em espírito, aceito
  conscientemente pelo responsável do produto pra este caso específico.
- **Sem fila de reenvio pro espelho**: diferente da jornada do próprio
  dono (tenta sincronizar de novo a cada trigger futuro) e dos pulsos
  GPS (fila local dedicada), a sincronização do espelho é **uma
  tentativa só**, no momento do encerramento - se não houver conexão
  nesse instante, o espelho se perde e não há retry automático depois.
- **Marca de auditoria (`espelhoDe`) não chega no backend/painel** - ver
  decisão 5 acima. Pendência: estender `workforce_core.entities.Jornada`
  + `workforce_storage.serializacao` + o repositório Postgres pra
  persistir `espelho_de`/`equipe_jornada` de verdade, se o responsável
  do produto quiser essa visibilidade no painel no futuro.
- **Exposição de PII via `GET /usuarios`**: qualquer pessoa com a chave
  client-embedded (não é segredo de verdade) consegue listar nome +
  matrícula de todo colaborador cadastrado no SGO. Minimizado (só
  `username`+`nome`, nunca perfil/escopo/governança), mas não eliminado.

## Validação realizada

- `python -m py_compile` no `api.py` staged
  (`Documents/Integração SGOWorkforce/api.py`): OK.
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js`: 158 passed (8 testes novos: 4 em
  `listarColaboradoresSgo`, 4 em `equipeJornada`/`gerarJornadaEspelho`).
- `pytest` completo (repositório SGO Workforce, sem mudança Python
  nesta rodada): 436 passed.
- `CACHE_VERSAO` v33 → v34.

## Validação NÃO realizada

- Teste ponta a ponta real (login → Etapa 2 → lista de colaboradores
  carregada do SGO → seleção de equipe → jornada completa → encerrar →
  confirmar que a jornada-espelho chegou no backend do Workforce pro
  colega selecionado) - depende do responsável do produto, usando o
  ambiente dev do SGO, e de promover o `api.py` staged (`GET /usuarios`
  novo) pro branch `dev` do Gestão_OS antes disso funcionar de verdade.

## Arquivos afetados

- `interface_campo/js/entidades.js` (`equipeJornada`/`espelhoDe` em
  `novaJornada`; `gerarJornadaEspelho` novo).
- `interface_campo/js/motorJornada.js` (`MotorJornada` propaga os campos
  novos).
- `interface_campo/js/integracaoSgo.js` (`listarColaboradoresSgo` novo).
- `interface_campo/js/app.js` (`carregarEquipeSgo`,
  `renderizarListaEquipe`, `obterEquipeJornadaSelecionada`,
  `gerarESincronizarEspelhosDeEquipe`, wiring no clique de "Iniciar
  jornada"/"Encerrar jornada"/"Iniciar nova jornada").
- `interface_campo/index.html` (seção "Equipe (opcional)" na Etapa 2).
- `interface_campo/css/estilo.css` (`.lista-equipe`, `.opcao-checkbox`).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v34).
- `tests/js/motorJornada.test.mjs` (4 testes novos).
- `tests/js/integracaoSgo.test.mjs` (4 testes novos).
- Fora deste repositório: `api.py` do SGO
  (`Documents/Integração SGOWorkforce/api.py`, `GET /usuarios` novo),
  `LEIA-ME.md` da mesma pasta atualizado.

## Data e responsáveis

- Data de registro: 2026-08-12.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
