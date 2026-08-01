# ADR-0035 | Logo da sidebar - tamanho e centralização (st.logo → st.sidebar.image)

## Contexto

No mesmo dia do ADR-0034 (logo GIF no lugar do vídeo/MRS via
`st.logo(..., size="large")`), o responsável do produto viu o
resultado publicado (captura de tela real) e reportou: o logo continua
minúsculo, encostado no canto superior junto do botão de recolher a
sidebar - `size="large"` não resolveu. Pedido: aumentar e centralizar
o logo na sidebar.

## Decisão

`st.logo` é a API do Streamlit pensada especificamente pra um slot
fixo pequeno no topo (o mesmo que também aparece quando a sidebar está
recolhida) - não é feita pra ser um elemento grande/centralizado no
corpo da sidebar, e o parâmetro `size` só tem 3 valores fixos
(`small`/`medium`/`large`) sem controle de largura real nem de
alinhamento.

Trocado por `st.sidebar.image(caminho, width=260)` - um elemento comum
do corpo da sidebar, com controle de largura de verdade. Renderiza
abaixo do menu de navegação (`st.navigation`/`st.Page`), que o
Streamlit sempre ancora no topo da sidebar independente da ordem do
código - mesmo comportamento que o vídeo do ADR-0033 já tinha (a
captura de tela daquele ADR mostrava o vídeo abaixo de todas as seções
de navegação).

Centralização e moldura (cantos arredondados, sombra) via CSS em
`painel/estilo.py`, escopado a `[data-testid="stSidebar"]
[data-testid="stImage"]` - `stImage` é o testid estável do elemento de
imagem do Streamlit (ao contrário dos testids de `st.navigation`, que
o próprio código já documenta como potencialmente instáveis entre
versões). O escopo por `stSidebar` garante que a regra não afete
nenhum outro `st.image` usado em outras telas do painel.

`painel/app.py` agora procura primeiro um `logo_sgo_workforce.webp`
(conversão mais leve, ver próxima seção/commit) e cai para o `.gif` se
o webp ainda não existir - nenhuma quebra enquanto a conversão não
termina.

## Validação de qualidade realizada

- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real (`streamlit run` + `curl` HTTP 200, log sem
  traceback) - confirma que `st.sidebar.image(...)` com o `.gif`
  (fallback, enquanto o `.webp` não estava pronto) roda sem erro.

## Validação NÃO realizada

- Teste visual em navegador real (tamanho/centralização/moldura
  aplicados de fato) - sandbox sem Playwright/Chromium, mesma
  limitação de sempre. Vale conferir no próximo deploy.

## Arquivos afetados

- `painel/app.py` (`st.sidebar.image` no lugar de `st.logo`).
- `painel/estilo.py` (CSS de centralização/moldura escopado a
  `stSidebar` + `stImage`).
