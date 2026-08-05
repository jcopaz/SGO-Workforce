# ADR-0055 | Blocos de códigos EE sempre visíveis (sem acordeão)

## Contexto

Testando o ADR-0050 (navegação hierárquica dos códigos EE) na interface
de campo, o responsável pelo produto reportou: "Não está vindo separado
nesses blocos. A ideia é ter um Bloco em negrito e as opções abaixo,
outro bloco em negrito e as opções abaixo, tudo no mesmo Drill."

O ADR-0050 tinha implementado um **acordeão de 2 telas**: primeiro
mostrava os 3 blocos como botões com contagem (`"🔵 Apoio e Preparação
(10)"`), e só depois de tocar num bloco é que os códigos daquele bloco
apareciam - escondendo os outros 2 blocos e exigindo um botão "← Voltar"
para trocar de bloco. Isso não era o que a especificação original
pedia: os 3 blocos deveriam aparecer **todos juntos**, cada um com o
título em negrito seguido diretamente da lista de códigos daquele bloco,
numa única tela/scroll - "drill" se referia à organização em seções, não
a uma navegação passo a passo que esconde as outras opções.

## Decisão

`interface_campo/js/app.js::renderSelecaoHierarquica` reescrita: itera
todos os blocos de `agruparCodigosDisponiveis` (inalterada -
`estruturaCodigos.js` não muda, a classificação código→bloco já estava
certa) e renderiza, para cada um, o título em negrito (com o filete
lateral colorido 🔵🟢🔴) seguido imediatamente dos seus códigos (ou dos
subgrupos "Esperas"/"Pausas" dentro de Interrupções). Removidos: o
estado `blocoExpandido`, os botões de bloco com contagem, e o botão "←
Voltar" - não existe mais estado de navegação nenhum, a lista inteira
está sempre visível.

`interface_campo/css/estilo.css`: `.bloco-operacional` deixa de estilizar
um botão inteiro (era aplicado a um `<button>`) e passa a estilizar o
título em negrito (`<p><strong>`) com o mesmo filete lateral colorido,
mais `padding-left` para o texto não colar na borda.

Nenhuma mudança em `estruturaCodigos.js`, `motorJornada.js`, catálogo ou
regra de negócio - só a apresentação.

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 126 passed, sem regressão (nenhum teste
  automatizado cobre `renderSelecaoHierarquica`/DOM - mesma limitação já
  registrada no ADR-0050, app.js não é testável sem um DOM real neste
  projeto).
- `pytest` completo: 391 passed (nenhum arquivo `.py` tocado).
- Leitura completa do trecho reescrito confirmando que não sobrou
  nenhuma referência a `blocoExpandido`.

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre) - especialmente
  relevante aqui, é a segunda tentativa da mesma tela depois de já ter
  saído errada uma vez.

## Arquivos afetados

- `interface_campo/js/app.js` (`renderSelecaoHierarquica`, remove
  `blocoExpandido`).
- `interface_campo/css/estilo.css` (`.bloco-operacional` e
  `.selecao-hierarquica-titulo` ajustados para título estático, não
  botão).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v21).
- `interface_campo/index.html` (rodapé "Versão v21").

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), corrigindo uma interpretação errada da
  especificação original do ADR-0050.
