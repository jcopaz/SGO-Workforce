# ADR-0059 | Seleção de códigos EE volta a ser `<select>` nativo, agora com `<optgroup>` por bloco

## Contexto

Terceiro ajuste no mesmo dia na mesma tela. Depois do ADR-0058 (lista de
itens de cada bloco com rolagem própria via `overflow-y: auto`), o
responsável do produto testou e pediu, mostrando um print de uma lista
suspensa nativa do celular: "Quero que fique nessa lista suspensa porém
separados pelos blocos" - ou seja, voltar ao paradigma de `<select>`
nativo (o que existia antes do ADR-0050), mas agora com os códigos
separados por `<optgroup>` de bloco em vez de um único grupo sem
distinção.

## Decisão

`renderSelecaoHierarquica` (`interface_campo/js/app.js`) reescrita pela
terceira vez no dia: em vez de construir uma árvore de `<div>`/`<p>`/
`<button>` customizada, monta um único `<select>` nativo com um
`<optgroup>` por bloco:

- `🔵 Apoio e Preparação`
- `🟢 Execução` (inclui os itens especiais EE17/EE21, mesma reconciliação
  do ADR-0050 - não são códigos soltos no motor)
- `🔴 Interrupções - Esperas`
- `🔴 Interrupções - Pausas`

`<optgroup>` nativo não suporta aninhamento - por isso "Interrupções"
virou **dois** optgroups de primeiro nível (Esperas e Pausas
separados), em vez de um "Interrupções" com dois subgrupos dentro. A
classificação código→bloco em si (`estruturaCodigos.js`) não mudou -
só como ela é renderizada.

Selecionar uma opção dispara `aoEscolherCodigo` diretamente (mesmo
comportamento "sem botão de confirmar depois" dos ADRs anteriores). O
`select.value` é resetado pra `""` (placeholder "Selecione...")
imediatamente ao ler o valor escolhido, antes de chamar `aoEscolherCodigo`
(que é assíncrona) - dois motivos: (1) o seletor não fica "preso"
mostrando o último código escolhido, e (2) `executarComGpsObrigatorio`
**não** re-renderiza a tela quando o GPS falha (só mostra a mensagem de
erro) - sem esse reset, tentar o mesmo código de novo não dispararia um
evento `change` de verdade, porque o `<select>` já estaria com esse
valor selecionado (`change` só dispara quando o valor muda).

CSS (`interface_campo/css/estilo.css`): removidas as classes que só
existiam para os dois formatos anteriores (`.selecao-hierarquica`,
`.selecao-hierarquica-titulo`, `.selecao-hierarquica-subgrupo`,
`.selecao-hierarquica-itens`, `.bloco-operacional*`) - confirmado por
`grep` que nenhuma sobrou referenciada em `interface_campo/`. O
`<select>` reaproveita `.seletor-motivo` (mesmo estilo dos demais
`<select>` do app) mais uma classe nova só pra largura cheia.

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 126 passed, sem regressão (mesma limitação já
  registrada nos 2 ADRs anteriores desta tela - sem DOM real disponível
  em Node, `renderSelecaoHierarquica` nunca teve teste automatizado
  direto).
- `grep` confirmando que nenhuma classe CSS removida ficou órfã
  referenciada em `interface_campo/js/` ou `tests/`.
- `pytest` completo: sem mudança (nenhum arquivo `.py` tocado).

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre) - quarta versão
  desta tela no mesmo dia (ADR-0050 → 0055 → 0058 → 0059), reforça que
  esta tela específica precisa de validação visual assim que possível
  antes de mexer de novo.

## Arquivos afetados

- `interface_campo/js/app.js` (`renderSelecaoHierarquica`).
- `interface_campo/css/estilo.css` (remove CSS dos 2 formatos
  anteriores, adiciona `.selecao-hierarquica-select`).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v23).
- `interface_campo/index.html` (rodapé "Versão v23").

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
