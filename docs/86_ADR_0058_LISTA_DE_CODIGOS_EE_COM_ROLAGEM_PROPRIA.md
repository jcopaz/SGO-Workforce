# ADR-0058 | Lista de códigos EE de cada bloco com rolagem própria

## Contexto

Depois do ADR-0055 (blocos sempre visíveis, sem acordeão), o responsável
do produto testou ao vivo e reportou: "Cade a lista com barra deslizante
para a seleção, assim fica muito ruim" - com todos os 23 códigos sempre
renderizados como botões de largura cheia, o bloco "Apoio e Preparação"
sozinho (9 códigos) já esticava a tela bem além de uma rolagem
razoável, e a página inteira (3 blocos, 23 códigos) ficava
desproporcionalmente longa para um celular.

## Decisão

Cada bloco ganhou seu próprio container de itens
(`.selecao-hierarquica-itens`, `interface_campo/js/app.js::renderSelecaoHierarquica`)
com `max-height: 15.5rem` (~4 códigos visíveis) e `overflow-y: auto` -
uma lista com rolagem própria, como pedido. O título do bloco (negrito,
filete colorido) fica **fora** desse container, sempre visível - só os
códigos dentro do bloco rolam. Em "Interrupções" (2 subgrupos, Esperas/
Pausas), os dois sub-títulos e seus itens rolam juntos dentro do mesmo
container do bloco - não foi criada rolagem aninhada por subgrupo
(rolagem dentro de rolagem tende a ficar ruim no toque do celular).

Nenhuma mudança em `estruturaCodigos.js` (classificação código→bloco
continua igual) nem no motor de domínio - só a apresentação.

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 126 passed, sem regressão (mesma limitação já
  registrada nos ADRs anteriores desta tela - sem DOM real disponível
  em Node, `renderSelecaoHierarquica` não tem teste automatizado).
- `pytest` completo: sem mudança (nenhum arquivo `.py` tocado).

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre) - terceira rodada de
  ajuste na mesma tela no mesmo dia, reforça a importância de validar
  visualmente assim que possível.

## Arquivos afetados

- `interface_campo/js/app.js` (`renderSelecaoHierarquica`).
- `interface_campo/css/estilo.css` (`.selecao-hierarquica-itens`).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v22).
- `interface_campo/index.html` (rodapé "Versão v22").

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
