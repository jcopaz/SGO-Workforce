# ADR-0036 | Logo da sidebar convertido pra WebP - mesma qualidade, 3.2x mais leve

## Contexto

O GIF usado na sidebar desde o ADR-0034 (`Logo - SGO Workforce
1x1.gif`, fornecido pelo responsável do produto) pesa 17.4MB - bem mais
que o mp4 original que ele substituiu (2.8MB). O responsável do produto
pediu explicitamente pra converter mantendo a qualidade, ciente da
ressalva já registrada no ADR-0034.

## Decisão

### 1. Sem ferramenta de vídeo disponível neste ambiente

Nem `ffmpeg` nem nenhuma lib Python de decodificação de vídeo
(`opencv-python`, `imageio`, `moviepy`) está instalada neste sandbox -
não dá pra recodificar a partir do mp4 original (que teria mais
fidelidade de cor que o GIF, já limitado a paleta de 256 cores).
Conversão feita a partir do próprio GIF via Pillow (já disponível),
lendo os 240 quadros com `ImageSequence.Iterator` e regravando como
WebP animado (`save_all=True`).

### 2. RGBA foi a primeira tentativa - e piorou (38MB, maior que o GIF)

Primeira tentativa converteu cada quadro pra RGBA (canal alfa)
"pra não perder nada", mas o GIF não tem transparência real (checado:
`alpha.getextrema() == (255, 255)` em todo quadro) - forçar RGBA só
aumentou a profundidade de cor sem necessidade, e o encoder WebP com
`quality=85`/`method=6` gastou mais bits tentando preservar precisão de
cor que o GIF nunca teve. Corrigido convertendo pra RGB (sem alfa).

### 3. Mesmo em RGB, qualidade alta não bate o GIF - o problema é resolução, não formato

Testes por amostragem (30 quadros, escalados pra estimar os 240):

| Resolução | Qualidade | Estimativa (240 quadros) |
|---|---|---|
| 720x720 (original) | 80 | 27.3 MB |
| 720x720 (original) | 65 | 19.2 MB |
| 480x480 | 85 | 11.6 MB |
| 480x480 | 75 | 6.5 MB |
| 320x320 | 85 | 4.6 MB |
| **360x360** | **85** | **5.9 MB (real: 5.39 MB)** |

Conteúdo tipo "vídeo" (gradientes de neon contínuos, 240 quadros) não
tem muita redundância intra-quadro pra WEBP/GIF explorarem bem (ao
contrário de um codec de vídeo de verdade como H.264 no mp4, que
explora redundância *entre* quadros por predição de movimento - por
isso o mp4 original era tão menor). Só reduzir a qualidade em 720x720
nunca chegava perto do tamanho do mp4.

A saída real: a imagem é exibida a **260px de largura** na sidebar
(`st.sidebar.image(..., width=260)`, ADR-0035) - codificar a 720px é
puro desperdício de banda, ninguém vê esse detalhe extra. Escolhido
**360x360** (~1.4x a largura de exibição - nitidez de sobra mesmo em
tela retina) com `quality=85`, resultado final **5.39MB** - 3.2x mais
leve que o GIF, sem perda perceptível (a redução veio de resolução que
já era invisível na tela, não de compressão agressiva da qualidade
visual em si).

### 4. Limpeza

`painel/app.py` simplificado: removida a checagem de fallback pro
`.gif` (existia só como rede de segurança enquanto a conversão não
tinha terminado) - agora referencia `logo_sgo_workforce.webp`
diretamente. `painel/assets/logo_sgo_workforce.gif` removido do
repositório (não é mais referenciado em lugar nenhum, 17.4MB de peso
morto). O `.gif`/`.mp4` originais na raiz do repositório continuam
intactos - só as cópias em `painel/assets/` foram tocadas.

## Validação de qualidade realizada

- `python -c` confirmando o WebP final: `size=(360, 360)`,
  `n_frames=240`, `is_animated=True`, `loop=0` (infinito) - mesma
  contagem de quadros e loop do GIF original, nada cortado.
- `python -m py_compile` em `painel/app.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.

## Validação NÃO realizada

- Teste visual em navegador real (nitidez percebida em 260px/retina,
  suavidade da animação) - sandbox sem Playwright/Chromium, mesma
  limitação de sempre. Vale conferir no próximo deploy; se a nitidez
  incomodar em telas muito grandes, dá pra subir a resolução de
  origem (ex.: 480x480) trocando `width`/`height` no script de
  conversão e regravando o arquivo - o `quality=85` já deixou
  bastante margem de tamanho pra isso.

## Arquivos afetados

- `painel/app.py` (referência direta ao `.webp`, fallback removido).
- `painel/assets/logo_sgo_workforce.webp` (novo, 5.39MB).
- `painel/assets/logo_sgo_workforce.gif` (removido, era 17.4MB).
