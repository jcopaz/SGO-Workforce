# ADR-0022 | GPS, foto e transferência do atendimento de falha (D2/D3/D4)

## Contexto

O ADR-0021 entregou o núcleo do atendimento de falha na interface de
campo (nota, ativo, sintoma, objeto, observações/causa) e deixou
explicitamente fora de escopo três pedaços do pedido original do
responsável pelo produto: captura de GPS no preenchimento (D2), upload de
foto (D3) e a transferência de um atendimento inacabado para outro
colaborador ("Falha não Concluída", D4). Este ADR entrega os três.

Decisão de negócio confirmada pelo responsável pelo produto antes da
implementação: **GPS e foto são best-effort e nunca bloqueiam "Concluir
atendimento"** - só nota/ativo/sintoma/objeto/observação (D1) continuam
obrigatórios. Isso é coerente com a regra de ouro 7/8 do CLAUDE.md (falha
de GPS não pode apagar/travar evento operacional, deve só marcar
qualidade).

## Decisão

### 1. GPS (D2) - captura sob ação explícita, nunca automática

`DadosFalha` (`src/workforce_core/entities.py`) ganha `gps_latitude`,
`gps_longitude`, `gps_precisao_metros`, `gps_capturado_em` - todos
opcionais. `registrar_dados_falha` (Python e o espelho JS em
`motorJornada.js`) aceita esses campos na mesma atualização parcial já
existente.

`interface_campo/js/geolocalizacao.js` (novo) envolve
`navigator.geolocation.getCurrentPosition` numa Promise que **nunca
rejeita** - timeout, permissão negada ou API ausente sempre resolvem para
`null`. A captura acontece só quando o colaborador toca no botão
"Capturar localização" dentro do formulário de atendimento de falha
(`app.js`) - decisão deliberada de não disparar automaticamente, para o
prompt de permissão do navegador só aparecer quando o colaborador sabe
por quê.

### 2. Foto (D3) - Supabase Storage, service_role key só no backend

`src/workforce_api/supabase_storage.py` (novo) fala com a API REST nativa
do Supabase (não o protocolo S3 - o responsável pelo produto forneceu
chaves JWT, não Access Key/Secret): `enviar_foto` faz upload direto para
o bucket `sgo-workforce-piloto` (projeto "Repositório de Evidências do
SGO", decisão de sessão anterior) e `gerar_url_assinada` gera uma URL
temporária sob demanda (a foto fica num bucket privado - nunca pública).

Dois endpoints novos em `app.py`, ambos atrás do mesmo token de
sincronização dos demais: `POST /fotos` (multipart, devolve o `caminho`
permanente do objeto) e `GET /fotos/url?caminho=...` (gera a URL
assinada quando alguém - painel, conferência de RASF - precisar
*ver* a foto depois). A `service_role` key do Supabase fica só em
variável de ambiente do backend (`SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET`) - a interface de campo
nunca a recebe, só fala com esses dois endpoints do próprio backend.
`requirements-api.txt` ganha `requests` (o backend passa a chamar uma API
externa, antes só falava com Postgres).

`DadosFalha.foto_caminho` guarda essa referência permanente (não uma URL
assinada, que expira). `interface_campo/js/fotoFalha.js` (novo) faz o
upload best-effort (nunca lança, mesmo padrão de `sincronizacao.js`); o
formulário ganha um `<input type="file" accept="image/*"
capture="environment">`.

### 3. Transferência entre colaboradores (D4) - "Falha não Concluída"

Novo método `transferir_atendimento_falha(quando)`
(`src/workforce_core/engine.py`, espelhado em `motorJornada.js`): mesmas
pré-condições de `encerrar_atividade` (jornada aberta, sem pausa ativa,
atividade ativa com `dados_falha`), mas **pula deliberadamente**
`_validar_dados_falha_completos`. É o único jeito de uma atividade com
`dados_falha` terminar `ENCERRADA` incompleta - o que serve como marca de
auditoria (`ENCERRADA` + incompleta só pode significar "transferida",
nunca "concluída"). Só encerra a **atividade**, não a jornada: o
colaborador que transfere pode ter mais o que fazer no resto do turno.

Backend ganha uma tabela nova, `continuacoes_falha` (id, matricula_destino,
dados JSONB, criado_em, consumida) e
`src/workforce_api/repositorio_continuacoes_postgres.py`
(`RepositorioContinuacoesFalhaPostgres`, mesmo espirito de
`repositorio_catalogo_postgres.py`). Três endpoints, todos com token:
`POST /continuacoes-falha` (cria), `GET /continuacoes-falha?matricula=X`
(lista pendentes para aquela matrícula) e
`POST /continuacoes-falha/{id}/consumir`.

**Só os 5 campos obrigatórios do D1 viajam entre colaboradores**
(`interface_campo/js/continuacoesFalha.js`, função
`dadosFalhaParaPayload`) - GPS e foto são específicos de quem capturou
(dispositivo e localização de quem estava lá), não fazem sentido
pré-preenchidos para a próxima pessoa.

Fluxo na interface de campo (`app.js`):
- Enquanto há atendimento de falha ativo, aparece o botão **"Falha não
  concluída"** ao lado de "Concluir atendimento". Ao clicar, mostra um
  formulário inline (não `prompt()` do navegador) pedindo a matrícula de
  destino.
- Ao confirmar: `transferirAtendimentoFalha` encerra a atividade
  localmente **primeiro** (nunca depende de rede), só depois
  `ContinuacoesFalha.criarContinuacao` avisa o backend, best-effort - se
  falhar, a atividade já foi encerrada aqui mesmo assim, e a tela avisa
  para avisar o colega manualmente.
- Ao clicar em "Iniciar jornada", a tela busca
  (`ContinuacoesFalha.buscarPendente`) se há uma continuação pendente
  para aquela matrícula; se houver, inicia jornada + atendimento de falha
  + preenche os dados automaticamente numa única transição, avisa o
  colaborador e marca a continuação como consumida no backend.

### 4. Correção de um bug encontrado durante o D2: `dados_falha` nunca era sincronizado

`interface_campo/js/sincronizacao.js::atividadeParaPayload` sempre
mandava `dados_falha: null` para o backend, com um comentário datado de
antes do ADR-0021 ("o motor JS ainda não tem atendimento de falha").
Isso nunca foi corrigido quando o ADR-0021 implementou atendimento de
falha no motor JS - resultado: **nenhum atendimento de falha registrado
na interface de campo jamais chegava ao painel/backend**, silenciosamente.
Corrigido com uma função `dadosFalhaParaPayload` que serializa o objeto
real, no mesmo contrato de `workforce_storage.serializacao.dados_falha_para_dict`.

## Consequências

- GPS e foto continuam funcionando (ou simplesmente não aparecem) mesmo
  sem sinal/permissão/conexão - nunca impedem registrar ou encerrar o
  atendimento de falha, por design.
- A `service_role` key do Supabase nunca trafega até o navegador do
  colaborador - só o backend (Render) a possui.
- Uma atividade `ENCERRADA` com `dados_falha` incompleto agora é
  interpretável sem ambiguidade: foi transferida (D4), nunca "esquecida"
  incompleta por um bug (a validação continua bloqueando
  `encerrar_atividade` normalmente).
- O bug de sincronização corrigido nesta sessão significa que
  atendimentos de falha registrados **antes** deste ADR, na prática,
  nunca chegaram ao backend/painel - não há nada a migrar (não havia dado
  para recuperar, só o registro local no dispositivo de quem preencheu).

## Fora de escopo / pendências

- Confirmar a Project URL do Supabase (`https://ivmmzefzdswmyiwaxzzg.supabase.co`,
  deduzida do JWT fornecido) contra Settings → API antes do deploy, e
  configurar `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`/`SUPABASE_BUCKET`
  no Render.
- Exibir a foto (via `GET /fotos/url`) no painel - hoje só existe o
  endpoint, nenhuma tela consome.
- Teste manual em navegador/celular real de GPS, upload de foto e
  transferência entre duas matrículas diferentes - mesma limitação de
  sempre (sem navegador disponível neste ambiente).

## Validação de qualidade realizada

- `tests/test_atendimento_falha.py`: casos novos de GPS/foto opcionais e
  de `transferir_atendimento_falha` (completo, sem atendimento ativo,
  em atividade comum, bloqueado com pausa aberta).
- `tests/test_integracao_sgo.py`: round-trip de serialização com e sem
  GPS/foto.
- `tests/test_supabase_storage.py` (novo, 7 casos): upload e URL
  assinada, sucesso, erro HTTP, sem configuração, bucket customizado -
  `requests.post` substituído por fake via monkeypatch (sem chamada real
  ao Supabase neste ambiente).
- `tests/test_workforce_api.py`: casos novos de `/fotos`, `/fotos/url` e
  `/continuacoes-falha` (token, sucesso, malformado, filtro por
  matrícula, consumo).
- `tests/js/motorJornada.test.mjs`: casos novos espelhando os de
  `test_atendimento_falha.py` (GPS/foto e `transferirAtendimentoFalha`).
- `tests/js/geolocalizacao.test.mjs`, `tests/js/fotoFalha.test.mjs`,
  `tests/js/continuacoesFalha.test.mjs` (novos): mesmo padrão de
  `fetchImpl`/`geolocationImpl` injetável já usado no projeto.
- `tests/js/sincronizacao.test.mjs`: caso novo comprovando a correção do
  bug de `dados_falha` nunca sincronizado.
- `pytest` completo: 226/226. `node --test tests/js`: 72/72.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada de
  `v9` para `v10` (3 arquivos JS novos no app shell).

## Validação NÃO realizada

Mesma limitação de sempre: teste manual em navegador/celular real (GPS,
foto, transferência entre duas matrículas) não foi feito neste ambiente.
Conexão real com o Supabase e com a tabela `continuacoes_falha` em
Postgres também não foi validada (sem acesso de rede de saída neste
ambiente) - só testada com fakes/monkeypatch.

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), que confirmou explicitamente a decisão
  "GPS/foto best-effort, nunca bloqueiam" antes da implementação.
- Revisão pendente: teste manual em navegador/celular real; configuração
  das variáveis de ambiente do Supabase no Render.
