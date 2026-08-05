# ADR-0060 | Pausa aninhada numa atividade/atendimento de falha aceita qualquer código solto (não só os 5 de "pausa")

## Contexto

Testando a tela de navegação por blocos (ADR-0059), o responsável do
produto reportou: "tanto durante a execução de atividade quanto no
atendimento da Falha, só está vindo as opções de Pausas, os outros
blocos também precisam vir porque ele também pode ter outros eventos
durante a execução da atividade ou durante o atendimento de falha."

Isso esbarrava numa regra real do motor: `EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError`
proíbe iniciar Deslocamento/Espera/Apoio (`EventoSecundario`) enquanto
há uma Atividade principal ativa - só `Pausa` pode ser aninhada dentro
de uma atividade em andamento. Perguntado diretamente
(`AskUserQuestion`) se o pedido era mudar essa regra (permitir dois
eventos simultâneos) ou manter como estava, o responsável do produto
confirmou: mudar a regra. Perguntado o que acontece com o HH nesse
caso, respondeu: "isso tem que ser descontado do HH" - mesmo
comportamento que `Pausa` já tem hoje.

## Investigação antes de codificar

Antes de desenhar uma mudança de motor (Python + JS espelhado, maior
risco), confirmei por leitura direta de código que **nada no motor de
domínio nem na consolidação de HH restringe o `motivo` de uma `Pausa`
por `tipo_registro`**:

- `engine.py::iniciar_pausa`/`motorJornada.js::iniciarPausa`: `motivo` é
  só uma string não-vazia, sem nenhuma validação de catálogo.
- `calculo.py::duracao_pausas_atividade`/`calculo.js::duracaoPausasAtividade`:
  soma **todas** as pausas de `atividade.pausas`, sem filtrar por
  `motivo` - `duracao_atividade_liquida` já descontava o tempo de
  qualquer pausa, sempre.
- `consolidacao.py` (categoria, classificação HH, `LinhaEvento`): toda
  vez que processa uma pausa, faz `catalogo.obter(pausa.motivo)` - a
  classificação vem do **código específico**, nunca de "é do tipo
  pausa". Um código de Deslocamento usado como motivo de uma pausa já
  seria classificado corretamente (`PRODUTIVA_NAO_RENTAVEL`, sua
  categoria própria) sem nenhuma mudança.

Conclusão: `tipo_registro` no catálogo é **só uma dica de UI** (que
seletor oferece qual código) - nunca foi uma restrição do domínio. A
tela restringia a lista de pausa aos 5 códigos `tipo_registro="pausa"`
por escolha de apresentação (ADR-0004/ADR-0050), não por regra de
negócio. Isso significa que atender o pedido não exige tocar em
`engine.py`, `motorJornada.js`, `consolidacao.py` nem seus espelhos de
teste - só ampliar a lista de códigos oferecida na tela.

## Decisão

`interface_campo/js/app.js`: o seletor "Iniciar pausa" (dentro de uma
atividade ou atendimento de falha em andamento) passa a oferecer
`[...motivosPausa, ...eventosSecundarios]` (os mesmos 20 códigos soltos
do seletor de "jornada aberta, sem nada em andamento") em vez de só
`motivosPausa` (5 códigos). Continua chamando sempre `motor.iniciarPausa`
- **é sempre uma `Pausa`, tecnicamente**, aninhada na atividade, mesmo
quando o código escolhido é `tipo_registro="evento_secundario"` no
catálogo. `EE17`/`EE21` (iniciam uma atividade/atendimento **nova**) e
`EE23` (só desfecho de encerramento) continuam de fora - não fazem
sentido aninhados dentro de uma atividade já em andamento.

Rótulo mudou de "Iniciar pausa:" para "Iniciar pausa ou evento:" -
reflete que agora cobre mais que uma pausa literal.

Status "Em pausa." (mostrado enquanto a pausa está ativa) virou
código-consciente: `${descricaoParaCodigo(pausa.motivo)} em andamento.`
- reaproveita a mesma função já usada pro status de `EventoSecundario`
(mesmo padrão, "Aguardando CCO em andamento." em vez de "Em pausa."
genérico quando o código escolhido não é uma pausa de fato).

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 126 passed, sem regressão (nenhum arquivo do
  motor JS tocado, só `app.js`).
- `pytest` completo: 399 passed, sem regressão (nenhum arquivo `.py`
  tocado - confirma a conclusão da investigação de que o motor já
  suportava isso).
- Leitura completa de `catalogoMotivos.js` confirmando que
  `motivosPausa`/`eventosSecundarios` são partições disjuntas do
  catálogo (nenhum código aparece nas duas listas) - `[...motivosPausa,
  ...eventosSecundarios]` nunca duplica uma opção no seletor.

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre).

## Arquivos afetados

- `interface_campo/js/app.js` (lista oferecida, rótulo, status
  código-consciente).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v24).
- `interface_campo/index.html` (rodapé "Versão v24").

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com) - confirmado explicitamente via `AskUserQuestion`
  antes de implementar, por ser mudança de regra de negócio.
