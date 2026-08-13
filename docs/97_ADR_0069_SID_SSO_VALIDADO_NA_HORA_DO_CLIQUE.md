# ADR-0069 | SSO do EE17 passa a validar o sid na hora do clique, não mais em "Iniciar jornada"

## Contexto

O responsável do produto relatou um bug real: ao chegar numa Atividade e
clicar em "Abrir apontamento de OS no SGO" (modo Online), o SGO ainda
mostrava a tela de login normal, mesmo já tendo confirmado a senha na
Etapa 1 do Workforce.

## Causa raiz

O `sid` (token de SSO que autentica o colaborador no SGO via `?sid=...`)
tem TTL curto **de propósito** (5 minutos - `TTL_HORAS_SID_SSO` em
`api.py`, decisão de segurança da ADR-0062: o `sid` viaja na query
string, que fica gravada em histórico do navegador/logs, então o TTL
curto limita a janela de exploração de um link vazado).

Até esta correção, o `sid` era obtido **uma única vez**, no clique de
"Iniciar jornada" (Etapa 2) - `tentarValidarLoginSgo`, disparado em
paralelo, guardava o resultado em `sessaoSgo` (variável em memória) pro
resto da sessão. O problema: entre "Iniciar jornada" e o colaborador de
fato chegar numa Atividade e clicar em "Abrir apontamento" pode passar
mais de 5 minutos com facilidade (caminhar até o local de trabalho,
preparar equipamento, etc.) - o `sid` guardado expirava antes de ser
usado, e o SGO recusava (corretamente, por segurança) o token vencido,
caindo na tela de login normal dele.

## Decisão

**O `sid` passa a ser buscado na hora exata do clique em "Abrir
apontamento de OS no SGO"**, não mais antecipado em "Iniciar jornada":

- Removida a chamada a `tentarValidarLoginSgo` em `aoClicarIniciarJornada`
  (Etapa 2) - não busca mais nada de SGO nesse momento.
- `criarBlocoOrdensServico` (modo Online): o botão "Abrir apontamento de
  OS no SGO" agora tem um handler assíncrono - ao clicar, chama
  `IntegracaoSgo.validarLoginSgo(matricula, els.senhaSgo.value)` **na
  hora**, reaproveitando a senha já digitada na Etapa 1 (nunca apagada
  durante a jornada - o colaborador não digita de novo), espera o
  resultado (botão mostra "Conectando ao SGO..." e fica desabilitado
  durante a chamada), e só então abre a nova aba com o `sid` fresco.
- Variável `sessaoSgo` (guardava o resultado em memória entre um clique
  e outro) e a função `tentarValidarLoginSgo` **removidas** - deixaram
  de ter uso, já que cada clique busca sua própria validação agora.
- O botão de abrir o SGO **sempre aparece** em modo Online (antes só
  aparecia depois de `sessaoSgo` ter sido preenchido com sucesso) - já
  sabemos que a senha está correta desde a validação obrigatória da
  Etapa 1, então não faz sentido esconder o botão esperando uma segunda
  confirmação prévia.

## Consequências

- **Corrige o bug relatado**: o `sid` usado pra abrir o SGO agora tem
  sempre até 5 minutos de vida a partir do clique real, nunca a partir
  de um momento anterior e imprevisível.
- **Pequeno atraso perceptível no clique** (chamada de rede síncrona
  antes de abrir a aba, em vez de instantâneo) - troca aceitável pela
  confiabilidade, com feedback visual ("Conectando ao SGO...") pra não
  parecer travado.
- **TTL de 5 minutos continua sem mudança** - a correção não pediu (nem
  precisou) enfraquecer a decisão de segurança da ADR-0062, só mudou
  QUANDO o token é pedido, não por quanto tempo ele vale.
- Se a validação falhar no clique (senha mudou nesse meio tempo, sem
  conexão momentânea), mostra o erro específico do backend e não abre
  nada - o colaborador pode tentar de novo.

## Validação realizada

- `node --check` em `interface_campo/js/app.js`: OK.
- `node --test tests/js`: 158 passed (nenhuma mudança de contrato
  público testável isoladamente - a lógica alterada é o handler de
  clique do botão, DOM-dependente, mesma limitação de sempre pra testes
  automatizados desta parte do app).
- `CACHE_VERSAO` v34 → v35.

## Validação NÃO realizada

- Teste real em celular confirmando que o SGO abre autenticado mesmo
  com um intervalo real (vários minutos) entre "Iniciar jornada" e
  "Iniciar atividade" - depende do responsável do produto.

## Arquivos afetados

- `interface_campo/js/app.js` (`sessaoSgo`/`tentarValidarLoginSgo`
  removidos; `criarBlocoOrdensServico` reescrito pro modo Online;
  `aoClicarIniciarJornada` não busca mais SSO).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v35).

## Data e responsáveis

- Data de registro: 2026-08-12.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
