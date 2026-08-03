# ADR-0040 | Logo da sidebar - tamanho dobrado e quebra de linha (container pai com altura fixa)

## Contexto

Com o testid certo (ADR-0039), o logo passou a aparecer de verdade -
mas cortado/sobreposto pelo título "Análise de Dados" logo abaixo, sem
respiro. O responsável do produto pediu: dobrar o tamanho e adicionar
uma quebra de linha pra sidebar não sobrepor a logo.

## Decisão

### Causa raiz da sobreposição

Rastreado no bundle JS instalado do Streamlit: o logo (`stSidebarLogo`)
e o botão de recolher a sidebar (`stSidebarCollapseButton`) são os dois
filhos de um mesmo container flex, `stSidebarHeader`:

```js
mo = h(`div`,{target:`eelgd2m4`})(({theme:e}) => ({
  display: `flex`,
  justifyContent: `space-between`,
  alignItems: `center`,
  marginBottom: e.spacing.lg,
  height: e.sizes.headerHeight,   // <- altura FIXA, pensada pro logo de ~24-32px
}))
```

`height` fixa e sem `flex-wrap` (padrão é `nowrap`): quando o logo
(120px, depois do ADR-0038/0039) ficava mais alto que essa altura fixa
do cabeçalho, ele simplesmente **estourava** a caixa do cabeçalho sem
empurrar o conteúdo seguinte pra baixo - o próximo elemento do DOM
("Análise de Dados") continuava renderizando logo depois do cabeçalho
*nominal*, sobrepondo a parte do logo que extrapolava.

### Correção

`painel/estilo.py`:

- `[data-testid="stSidebarLogo"]`: altura dobrada pra `240px`
  (`120px` → `240px`, pedido explícito); `flex: 1 1 100%` faz o logo
  ocupar a linha inteira do container flex.
- `[data-testid="stSidebarHeader"]`: `height: auto` (deixa a linha
  crescer de verdade pro tamanho do conteúdo, em vez da altura fixa do
  tema) + `flex-wrap: wrap` (com o logo em `flex-basis: 100%`, o botão
  de recolher não cabe mais na mesma linha e quebra pra linha de baixo
  sozinho - a "quebra de linha" pedida) + `margin-bottom` maior pra dar
  respiro antes de "Análise de Dados".
- `[data-testid="stSidebarCollapseButton"]`: `margin-left: auto`
  mantém o botão alinhado à direita na sua própria linha (sem isso,
  `justify-content: space-between` com um único item por linha o
  jogaria pra esquerda).

## Validação de qualidade realizada

- Estrutura do container pai (`stSidebarHeader`, `height` fixa via
  token de tema, `display:flex` sem wrap) confirmada lendo o bundle JS
  instalado, mesma técnica das ADRs 0038/0039.
- `python -m py_compile` em `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.

## Validação NÃO realizada

- Teste visual em navegador real - sandbox sem Playwright/Chromium,
  mesma limitação de sempre.

## Arquivos afetados

- `painel/estilo.py` (altura do logo dobrada; CSS do container pai
  `stSidebarHeader` e do botão de recolher ajustados pra quebra de
  linha).
