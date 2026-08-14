# ADR-0071 — Sem conexão nenhuma no login inicial, entrada cai automaticamente em modo Offline

- Status: aceito e implementado
- Data: 2026-08-14

## Contexto

O ADR-0065 tornou o login real contra o SGO obrigatório na Etapa 1 (antes de
avançar para a pergunta Online/Offline), sob a premissa de que "o
colaborador sempre tem sinal no início do turno". O usuário testou o app em
celular real e trouxe de volta uma pergunta que a premissa original não
cobria:

> "ele restabelece em um cenário a onde ele não consiga fazer o login
> inicial online, como podemos validar a entrada dele?"

Ou seja: e se não houver conexão nenhuma bem no momento de iniciar o turno?
Com a regra anterior, o colaborador ficava travado na Etapa 1 sem
alternativa nenhuma - direto contra o golden rule #7 (pulsos/app devem
funcionar offline) aplicado, por extensão, ao próprio início do turno.

Perguntado diretamente (`AskUserQuestion`), o responsável do produto
escolheu: **cair para modo Offline automaticamente** quando a validação
falhar por falta de conexão - não bloquear, e não perguntar caso a caso.

## Decisão

`validarLoginSgo` (`interface_campo/js/integracaoSgo.js`) agora distingue
dois tipos de falha:

- **Sem conexão** (`fetch` nem completou, `catch`): `{ ok: false,
  semConexao: true, mensagem: "..." }`.
- **Credenciais erradas ou acesso negado** (HTTP 401/403 - o backend
  respondeu, só que recusou): `{ ok: false, mensagem: "..." }`, sem a flag.

No handler de `btnContinuarLogin` (`interface_campo/js/app.js`):

- Se a falha **não** tem `semConexao` (senha errada, matrícula errada,
  acesso negado) → continua bloqueando na Etapa 1, como antes. Isso
  continua sendo uma barreira de segurança de verdade, não uma formalidade.
- Se a falha **tem** `semConexao: true` → mostra aviso explicando o
  fallback, avança para a Etapa 2 (pergunta) mesmo assim, e pré-seleciona o
  cartão "Offline" (o colaborador ainda pode trocar pra Online manualmente
  se preferir - nada é travado, só sugerido).

Crucial: isso **não** pula a validação de verdade, só adia. O SSO real (sid)
já era buscado na hora exata do clique em "Abrir apontamento de OS", não na
Etapa 1 (ADR-0069) - então mesmo um colaborador que entrou via este
fallback vai ter o login revalidado contra o SGO no primeiro momento em que
tentar abrir o apontamento online, com conexão de verdade. O fallback só
afeta o *gate de entrada*, nunca o acesso real ao SGO.

## Por que não as outras opções

- **Bloquear e pedir nova tentativa** (manter a regra atual): rejeitada
  pelo responsável do produto - deixaria o colaborador sem conseguir nem
  começar a registrar HH numa área de sinal ruim, contradizendo o próprio
  motivo de o app ser offline-first.
- **Perguntar caso a caso**: mais flexível, mas adiciona uma decisão manual
  extra bem no momento em que o colaborador provavelmente já está com
  pressa/sem sinal - rejeitada em favor do caminho automático.

## Limitação conhecida (aceita por ora)

Não há, ainda, um campo persistido/auditável marcando "esta jornada
começou sem o login inicial confirmado" - o único rastro hoje é o aviso
mostrado na tela e o fato de que o modo ficou Offline. Se o produto
precisar de auditoria formal desse cenário (ex.: relatório de quantas
jornadas começaram sem sinal), será um incremento futuro em
`entidades.js`/`motorJornada.js`/payload de sincronização/modelo Python -
deliberadamente fora do escopo deste ADR (menor incremento validável).

## Validação

- `node --check` em `app.js` e `integracaoSgo.js` - sintaxe ok.
- `node --test tests/js/*.test.mjs` - 158/158 passando, incluindo o teste
  atualizado que confirma `semConexao:true` no fetch-falha e
  `semConexao:undefined` no HTTP 401 (credenciais erradas continuam
  bloqueando).
- `CACHE_VERSAO`/rodapé bumpados pra v37.
