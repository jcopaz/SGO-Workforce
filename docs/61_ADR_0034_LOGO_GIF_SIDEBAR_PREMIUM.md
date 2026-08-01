# ADR-0034 | Logo animado (GIF) na sidebar, substituindo vídeo e logo estático da MRS

## Contexto

No mesmo dia do ADR-0033 (que introduziu o vídeo `Logo - SGO Workforce
1x1.mp4` na sidebar, abaixo do logo estático da MRS), o responsável do
produto viu o resultado publicado e considerou a estética "muito pobre":
o logo da MRS (`st.logo`) aparece pequeno e genérico, e o vídeo mostra a
barra de controles nativa do navegador (play, mudo, volume, menu de
3 pontos) por baixo da animação - o `st.video` do Streamlit não tem
parâmetro pra esconder isso nesta versão. Pedido: usar o arquivo
`Logo - SGO Workforce 1x1.gif` (fornecido na raiz do repositório,
mesma animação do mp4, mas em formato GIF) no lugar do logo da MRS, e
tirar o vídeo.

## Decisão

### 1. GIF em vez de vídeo - resolve o problema dos controles de graça

Um GIF anima nativamente dentro de uma tag `<img>` comum - todo
navegador moderno já faz isso sem precisar de `autoplay`/`loop`/`muted`
nem exibir nenhuma barra de controles. Isso explica por que o
responsável do produto forneceu especificamente uma versão GIF do mesmo
logo: resolve exatamente o problema visual relatado, sem precisar de
nenhum parâmetro extra do lado do código.

### 2. `st.logo(..., size="large")` no lugar do `st.video` na sidebar

`painel/app.py`: o bloco inteiro de `st.sidebar.video(...)` (ADR-0033)
foi removido. `st.logo(str(caminho_gif))` (antes apontando pra
`logo_mrs.png`) passou a apontar pra
`painel/assets/logo_sgo_workforce.gif`, com `size="large"` pra dar mais
presença visual ao logo animado. Preferido a um `st.sidebar.image(...)`
solto: `st.logo` é a API oficial do Streamlit pra logo de produto -
mantém o comportamento de aparecer também no canto superior quando a
sidebar está recolhida, que um `st.sidebar.image` comum não replica sem
gambiarra.

`painel/estilo.py` ganhou uma moldura discreta pro slot do logo
(`[data-testid="stLogo"]`: `border-radius` + `box-shadow`) - acabamento
"premium" sem mexer no tamanho/posição que o próprio Streamlit já
controla via `size="large"`.

### 3. Arquivos

- `painel/assets/logo_sgo_workforce.gif` (novo, copiado da raiz do
  repositório - arquivo original mantido intacto lá, mesmo padrão do
  ADR-0033 pro mp4).
- `painel/assets/logo_sgo_workforce.mp4` **removido** do repositório -
  não é mais referenciado em lugar nenhum, sem motivo pra manter 2.8MB
  de asset morto.
- `logo_mrs.png` **mantido** em `painel/assets/` (não apagado, só
  parou de ser referenciado em `app.py`) - o responsável do produto não
  pediu pra excluir o arquivo, só pra trocar o que aparece no slot do
  logo.

### 4. Peso do arquivo - ressalva conhecida, não bloqueante

O GIF (17.4MB) é bem mais pesado que o mp4 que substituiu (2.8MB) -
GIF é um formato ineficiente pra conteúdo tipo vídeo comparado a mp4/
H.264. Isso é uma troca aceita deliberadamente (o pedido foi explícito
e a vantagem de animar sem controles nativos é real), mas vale registrar:
carregamento inicial da sidebar fica mais lento numa conexão ruim. Não
bloqueante - decisão do responsável do produto, documentada aqui pra
não ser esquecida caso vire reclamação de performance depois.

## Validação de qualidade realizada

- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão (nenhum teste toca
  `app.py`/`estilo.py` diretamente - cobertura é smoke test, ver
  abaixo).
- Smoke test real: `streamlit run painel/app.py` em background, `curl`
  na porta local devolveu HTTP 200, log do processo sem traceback -
  confirma que `st.logo(..., size="large")` aceita o GIF e o launcher
  roda sem erro em runtime.

## Validação NÃO realizada

- Teste visual em navegador real (a animação do GIF renderizando de
  verdade dentro do slot `st.logo`, a moldura CSS aplicada
  corretamente, comportamento com a sidebar recolhida) - sandbox sem
  Playwright/Chromium, mesma limitação de sempre. Vale conferir no
  primeiro deploy.

## Arquivos afetados

- `painel/app.py` (logo GIF em vez de vídeo/MRS estático).
- `painel/estilo.py` (moldura CSS do slot do logo).
- `painel/assets/logo_sgo_workforce.gif` (novo).
- `painel/assets/logo_sgo_workforce.mp4` (removido).
