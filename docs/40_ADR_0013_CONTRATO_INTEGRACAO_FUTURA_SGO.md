# ADR-0013 | Contrato de integração futura com o SGO (Incremento 13)

## Contexto

Este é o último incremento do roadmap
(`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 11). A regra
de ouro do `CLAUDE.md` e a seção 3.1 do alinhamento oficial são
explícitas: **"Não acople o Workforce ao código do SGO durante o MVP"** —
"Não inserir o Workforce diretamente no código do SGO... A integração
futura deverá ocorrer por contratos definidos e versionados." Não existe
nenhum sistema SGO real neste repositório ou ambiente para integrar.

`docs/16_INTEGRACAO_FUTURA_SGO.md` e `docs/27` seção 10 já documentavam,
antes desta sessão: os alvos da integração (autenticação/SSO, usuários,
OS programadas, ativos/pátios, retorno de HH real, dashboard unificado),
contratos sugeridos (`GET /integracao/os`, `/ativos`, `/usuarios`,
`POST /integracao/hh-real`, eventos com versão e timestamp), a estratégia
(leitura/snapshot primeiro, escrita controlada depois) e a regra de
chave: **"OS pode ser reaproveitada em ciclos SAP. Toda associação futura
deve carregar ciclo/plano/data de importação, não apenas o número da
OS."** Seção 15.3 ("Antes do Incremento 13") deixa pendente: contrato de
usuários, contrato de ativos e pátios, contrato de OS e ciclo de
programação, regra de devolução do HH real, autenticação entre
aplicações, estratégia de SSO, experiência visual unificada,
responsabilidade de cada sistema sobre os dados mestres.

## Decisão

Este incremento **não integra com nada** — prepara apenas a **forma** do
contrato futuro, exatamente como já documentado, para que uma integração
real (quando acontecer) não exija redesenhar as chaves usadas em todo o
resto do sistema.

1. **`workforce_core/integracao_sgo.py`**: value objects carregando
   exatamente as chaves já citadas em `docs/16`/`docs/27` seção 10.3 —
   `UsuarioAutorizado` (matrícula, nome, coordenação), `Coordenacao`,
   `Especialidade`, `Patio`, `Ativo` (identificador, pátio), `OsProgramada`
   (usa `ReferenciaOS`, nunca um número solto). Nenhum campo além do que
   já estava documentado foi adicionado.
2. **`ReferenciaOS(numero, ciclo_ou_plano, data_importacao)`**: implementa
   literalmente a regra de chave de `docs/16` — a igualdade/hash usam
   `numero` + `ciclo_ou_plano` (duas OS com o mesmo número em ciclos
   diferentes **nunca** são iguais); `data_importacao` fica fora da
   identidade (`compare=False`) porque é metadado de auditoria de quando o
   snapshot foi lido, não parte de quem a OS *é*.
3. **`ContratoSGO`** (`Protocol`, `@runtime_checkable`): somente métodos
   de **leitura** (`listar_usuarios_autorizados`, `listar_coordenacoes`,
   `listar_especialidades`, `listar_patios`, `listar_ativos`,
   `listar_os_programadas`, `metadados_snapshot`) — "primeiro integração
   por leitura/snapshot. Depois escrita controlada" (`docs/16`). A
   devolução de HH real (`POST /integracao/hh-real` sugerido) é a
   "segunda integração" (`docs/27` seção 10.5) e **não está neste
   contrato** — ficaria para quando a primeira estiver validada em
   produção, o que está muito além do escopo desta sessão.
4. **`ContratoSGOEmMemoria`**: implementação falsa, só para
   desenvolvimento/teste — mesmo papel que
   `ClienteSincronizacaoEmMemoria` cumpriu para o Incremento 3. Não
   representa nenhum dado real do SGO.
5. **`DadosFalha.os_referencia: Optional[ReferenciaOS] = None`**: campo
   **recomendado** (não obrigatório — seção 3.5 já listava "OS
   relacionada" como recomendado, não obrigatório, desde o Incremento 6).
   Adicionado agora usando `ReferenciaOS` desde o início, em vez de um
   número de OS solto que precisaria ser migrado depois. Serialização
   (`workforce_storage`) atualizada, `FORMATO_VERSAO` 3 → 4, com
   compatibilidade retroativa total (`.get("os_referencia")`).

## Deliberadamente fora deste incremento (permanece pendente)

- **Qualquer implementação real de `ContratoSGO`** (chamada HTTP, leitura
  de banco do SGO, etc.): não existe, nem poderia existir de forma
  responsável sem um sistema SGO real para conversar e sem validar o
  contrato com quem mantém esse sistema.
- **Autenticação entre aplicações e estratégia de SSO**: não abordadas —
  o Workforce continua sem nenhuma autenticação própria em nenhuma
  camada (interface de campo, painel, ou este contrato).
- **Experiência visual unificada**: fora de escopo técnico deste
  incremento — é uma decisão de produto/design.
- **Responsabilidade de cada sistema sobre os dados mestres** (quem é
  "dono" de usuários, ativos, pátios): não decidido.
- **Regra de devolução do HH real** ("segunda integração"): não
  implementada — nem a regra de negócio, nem o contrato de escrita.
- **Contratos de usuários/ativos/pátios/OS "oficiais"**: os value objects
  aqui carregam as chaves já documentadas, mas o **schema completo**
  (quais campos além dessas chaves, formatos exatos, paginação, etc.) só
  pode ser definido junto com o time responsável pelo SGO real.

## Encerramento do roadmap de 13 incrementos

Com este ADR, os 13 incrementos de
`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção 11 estão
implementados nesta sessão, cada um com testes automatizados e um ADR
registrando decisões provisórias, alternativas consideradas e o que
ficou deliberadamente fora de escopo. Nenhum incremento inventou uma
decisão de negócio marcada como pendente pelo alinhamento oficial — onde
uma decisão real era necessária para o código funcionar, a escolha foi
sempre a menor possível, documentada como provisória, e sujeita a
revisão do responsável pelo produto.

O que **não** foi feito, e continua precisando de atenção humana antes de
qualquer uso com colaboradores reais:

- Teste manual em navegador/celular real (nenhuma tela deste projeto foi
  clicada por um humano ou por automação de navegador nesta sessão —
  registrado em cada ADR de interface).
- Validação de LGPD, segurança da informação e política corporativa para
  captura de GPS (`docs/08`).
- Definição de catálogos oficiais (pausas, RASF, buckets de capacidade).
- Qualquer decisão de negócio explicitamente listada como pendente em
  cada ADR (0001 a 0013).

## Validação realizada

- `tests/test_integracao_sgo.py` (10 testes): identidade de `ReferenciaOS`
  (mesmo número, ciclos diferentes ≠ iguais; mesma OS, data de importação
  diferente = iguais; uso como chave de dict), `DadosFalha.os_referencia`
  opcional e funcionando dentro do fluxo normal de atendimento de falha,
  round-trip de serialização com e sem `os_referencia` (retrocompatível
  com arquivos v3), conformidade estrutural de `ContratoSGOEmMemoria` com
  o `Protocol` `ContratoSGO`, carregamento/listagem, e comportamento vazio
  sem quebrar.
- `python -m pytest`: 158 passed (suíte completa do projeto).

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto e time do SGO, quando a
  integração real for priorizada — nenhuma parte deste ADR deve ser
  tratada como contrato definitivo sem essa validação.
