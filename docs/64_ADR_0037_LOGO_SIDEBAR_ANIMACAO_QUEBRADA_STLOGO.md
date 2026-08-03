# ADR-0037 | Logo da sidebar - animação quebrada por limitação real do Streamlit, corrigida voltando pra st.logo + GIF

## Contexto

O responsável do produto reportou (captura de tela real) que o logo
WebP do ADR-0036 aparece **estático** na sidebar, e pediu pra
reposicionar acima do título "Análise de Dados", centralizado -
oferecendo voltar pro mp4 se necessário.

## Decisão

### 1. Causa raiz real (lida direto no código-fonte instalado do Streamlit, não suposição)

`streamlit/elements/lib/image_utils.py`, função `image_to_url` (usada
tanto por `st.image` quanto por `st.logo`): depois de ler os bytes da
imagem, SEMPRE chama `_ensure_image_size_and_format`, que:

1. Detecta o formato de saída via `_validate_image_format_string` -
   mas `ImageFormat` só tem três valores possíveis: `"JPEG"`, `"PNG"`,
   `"GIF"`. WebP **não existe** como formato de saída reconhecido -
   cai no fallback e vira `"JPEG"`.
2. Se o formato de entrada for diferente do formato de saída
   detectado, ou se a imagem precisar ser redimensionada, reabre a
   imagem via `PIL.Image.open()` (que sem `.seek()`/
   `ImageSequence.Iterator` só enxerga o **primeiro quadro**) e regrava
   com `image.save(tmp, format=format, quality=quality)` **sem**
   `save_all=True` - todos os outros quadros são descartados.

Testado direto contra o código instalado (`_validate_image_format_string`
+ `_ensure_image_size_and_format` chamados manualmente com o arquivo
real): confirma que o WebP do ADR-0036 sempre seria achatado - não foi
erro na conversão do ADR-0036, é uma limitação real do Streamlit com
esse formato. `st.sidebar.image(..., width=260)` piorava ainda mais:
o WebP (360px) é maior que o `width=260` pedido, então o
redimensionamento também seria acionado, mesmo se o formato fosse
preservável.

GIF é o único formato animado que o pipeline preserva intacto - **mas
só quando o formato de saída detectado também é GIF (o que já
acontece pra qualquer GIF de entrada) e nenhum redimensionamento é
necessário**. Testado e confirmado (bytes de saída idênticos aos de
entrada, 240 quadros preservados) usando o arquivo real deste projeto.

### 2. `st.navigation` sempre ancora o menu no topo - só `st.logo` fica acima dele

Confirmado nesta sessão (ADR-0033 em diante): tanto `st.sidebar.video`
quanto `st.sidebar.image`, chamados no código **antes** de
`pagina.run()`, sempre renderizaram **abaixo** do menu de navegação
("Análise de Dados"/"Dados"/"Configurações") nas capturas de tela
reais - a ordem do código não importa, o menu de `st.navigation` é
ancorado no topo da sidebar de forma fixa. O único slot documentado
que fica genuinamente acima desse menu é o do próprio `st.logo`
(reservado também pro cabeçalho do app quando a sidebar está
recolhida). Não há como cumprir "acima do título Análise de Dados"
com nenhum outro widget de sidebar.

### 3. Correção: `st.logo` de volta, com GIF (não WebP), tamanho e centralização via CSS

- `painel/app.py`: `st.sidebar.image(webp)` → `st.logo(gif,
  size="large")`. `painel/assets/logo_sgo_workforce.webp` removido;
  `logo_sgo_workforce.gif` restaurado (cópia do arquivo original
  fornecido, sem reprocessar).
- Tentativa de reduzir a resolução do GIF pra economizar banda (320x320
  via Pillow) **não ajudou** - o tamanho do arquivo caiu menos de 2%
  (17.2MB vs 17.4MB original). Esse tipo de conteúdo (gradiente de
  neon contínuo, 240 quadros) comprime mal em GIF **em qualquer
  resolução** - mesma conclusão já registrada no ADR-0036 pra WebP, GIF
  é ainda pior nesse quesito. Decisão: manter o arquivo original sem
  reprocessar, priorizando "mantendo a qualidade" (pedido explícito)
  sobre o ganho marginal de banda.
- `painel/estilo.py`: `st.logo` limita a altura renderizada a 32px
  mesmo com `size="large"` (documentado no próprio docstring do
  Streamlit: `small`=20px, `medium`=24px, `large`=32px de altura
  máxima) - por isso o logo continuava minúsculo mesmo depois do
  ADR-0035 tentar aumentar via esse parâmetro. CSS escopado a
  `[data-testid="stSidebar"] [data-testid="stLogo"]` sobrescreve pra
  `height: 120px`, centraliza com `display:flex; justify-content:
  center`, e mantém a moldura (cantos arredondados, sombra). Escopado a
  `stSidebar` de propósito - não altera o logo pequeno que o Streamlit
  mostra no canto superior quando a sidebar está recolhida (mesmo
  componente, contexto diferente, onde o tamanho pequeno faz sentido).

### 4. Por que não foi pro mp4 (a alternativa que o responsável do produto ofereceu)

`st.logo` só aceita imagem (`AtomicImage | str`) - não aceita vídeo.
Como só o slot do `st.logo` fica acima do menu de navegação (seção 2),
usar mp4 exigiria abrir mão do posicionamento pedido. Como o GIF
restaurado (arquivo original, sem reprocessar) resolve tanto a
animação quanto o posicionamento ao mesmo tempo, não foi necessário
usar essa saída.

## Validação de qualidade realizada

- Pipeline real do Streamlit testado diretamente (não simulado): bytes
  de entrada e saída idênticos, 240 quadros preservados no resultado.
- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.

## Validação NÃO realizada

- Teste visual em navegador real (animação de fato tocando, tamanho
  120px aplicado, centralização, posição acima do menu) - sandbox sem
  Playwright/Chromium, mesma limitação de sempre. A leitura direta do
  código-fonte do Streamlit dá confiança bem maior que as tentativas
  anteriores (que eram best-effort sem essa verificação), mas o
  CSS especificamente (seletor `stLogo`, altura 120px) continua sem
  confirmação visual.

## Arquivos afetados

- `painel/app.py` (`st.logo` com GIF, no lugar de
  `st.sidebar.image` com WebP).
- `painel/estilo.py` (CSS de tamanho/centralização escopado a
  `stLogo`, no lugar do CSS de `stImage`).
- `painel/assets/logo_sgo_workforce.gif` (restaurado, cópia do arquivo
  original).
- `painel/assets/logo_sgo_workforce.webp` (removido - confirmado que
  `st.image`/`st.logo` não conseguem exibir esse formato animado).
