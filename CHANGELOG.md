# Changelog

## [2026-08-04] Mapa operacional: camadas sempre visíveis e fluidez (ADR-0049)

Ver `docs/76_ADR_0049_MAPA_CAMADAS_SEMPRE_VISIVEIS_E_FLUIDEZ.md` para a
decisão completa. Feedback do responsável pelo produto: controle de
camadas do mapa "pouco interativo" (a maioria dos toggles não era uma
escolha real) e Streamlit lento por causa de rerun em excesso.

### Alterado
- Malha férrea, marcos de início/fim, pulsos brutos e clusters de
  permanência agora são sempre desenhados no mapa - deixaram de ser
  camadas togglable no `LayerControl`. Só "Traçar trajetória" continua
  opcional.
- Tile base deixou de aparecer no controle de camadas (nunca foi uma
  escolha real, só existe um tile).
- `carregar_jornadas_via_api`/`carregar_pulsos_via_api` agora passam por
  cache (`st.cache_data`, TTL 60s) na tela do mapa - ajustar um slider/
  filtro não rebate mais no backend a cada interação. Botão "Sincronizar
  dados" agora limpa esse cache de verdade (antes só mostrava um toast).
- `st_folium(..., returned_objects=[])` - interagir com o mapa (pan/
  zoom/clique) não reexecuta mais o script inteiro.

### Corrigido
- Bug de teste real encontrado durante a validação: `st.cache_data` tem
  escopo de processo, não por teste - os testes de ponta a ponta do mapa
  vazavam jornada/pulso em cache entre si (mesma URL/token fake em
  todos). Corrigido com uma fixture que limpa o cache antes de cada
  teste.

## [2026-08-04] GPS obrigatório completo (pausa/evento secundário) e captura ao retornar ao primeiro plano (ADR-0048)

Ver `docs/75_ADR_0048_GPS_OBRIGATORIO_COMPLETO_E_CAPTURA_AO_RETORNAR.md`
para a decisão completa. Colaboradores reais relataram o pulso periódico
parando ao minimizar o app - confirmado como limitação de plataforma
(navegador suspende JS fora do primeiro plano), não bug. Pesquisa
completa de alternativas de captação contínua em segundo plano (app
nativo Android, Traccar, orçamento) registrada em memória do projeto,
não implementada ainda - decisão maior em aberto.

### Corrigido
- GPS obrigatório (ADR-0043 "obrigatório em tudo") estava incompleto
  desde o ADR-0045 - só cobria iniciar/encerrar jornada e atividade.
  Estendido para pausa (iniciar/finalizar) e evento secundário
  (iniciar/encerrar) - 10 pontos de transição no total agora.

### Adicionado
- Captura de GPS imediata ao voltar para o app depois de minimizar
  (`visibilitychange`) - aproveita a janela garantida de primeiro plano
  em vez de esperar até 1 minuto pelo próximo ciclo periódico.

### Alterado
- `interface_campo/service-worker.js`: `CACHE_VERSAO` v18 → v19.
- `interface_campo/index.html`: aviso atualizado, rodapé "Versão v19".

## [2026-08-04] Calibração para horário de Brasília e filtros/marcos do mapa operacional (ADR-0047)

Ver `docs/74_ADR_0047_TIMEZONE_BRASIL_E_FILTROS_MAPA_OPERACIONAL.md` para
a decisão completa.

### Corrigido - dois bugs reais de timezone encontrados investigando o pedido "calibre pro horário do Brasil"
- `painel/dados.py::formatar_data_hora` mostrava a hora em UTC crua - todo
  horário exibido no painel aparecia 3h adiantado em relação ao horário
  real do colaborador.
- `workforce_core/consolidacao.py` agrupava eventos por `inicio.date()`
  também em UTC - um evento às 22h de Brasília (01h UTC do dia seguinte)
  contava para o dia ERRADO em todos os agrupamentos por data do painel
  (evolução diária, contagem por dia). Este era o bug mais sério dos
  dois - reclassificação de HH para a data errada, não só exibição.
- Captura/armazenamento (interface de campo, backend, Postgres) já
  estavam corretos (UTC) - a correção é só na conversão pro horário de
  Brasília no limite de apresentação/agrupamento, nunca antes.

### Adicionado
- `src/workforce_core/fuso_horario.py` (novo): `para_horario_brasil`
  (stdlib `zoneinfo`, `tzdata` adicionado a `requirements.txt` para
  portabilidade em containers).
- Pinos de início (verde) e fim (vermelho) da jornada no mapa operacional
  - sempre representam o primeiro/último pulso real, mesmo com filtros
    ativos.
- Cor por atividade/pausa/evento nos pulsos brutos
  (`workforce_core.consolidacao.classificar_instante` + `painel/mapa.py`
  `rotulo_classificacao_pulso`/`cor_por_rotulo`, cor determinística por
  hash estável do rótulo).
- Filtros de Atividade, Data e faixa de Horário na tela do mapa
  operacional (`painel/dados.py::filtrar_pulsos_por_periodo`, nova
  função pura).
- 24 casos de teste novos (`tests/test_fuso_horario.py` novo +
  casos em `test_consolidacao.py`/`test_painel.py`/`test_mapa.py`/
  `test_mapa_operacional_painel.py`) - 352 testes no total, sem
  regressão.

### Validação NÃO realizada
- Renderização visual real num navegador (sandbox sem Chromium/
  Playwright) - pedir ao responsável pelo produto para conferir no
  painel publicado.
- `streamlit.testing.v1.DateInput.set_value()` não propaga corretamente
  neste ambiente/versão do Streamlit (limitação da ferramenta de teste,
  confirmada isolada fora deste app) - o filtro de data em si está
  coberto por teste de função pura, só a interação via widget não é
  testável automaticamente hoje.

## [2026-08-04] Estilo visual do mapa operacional e camada da malha férrea da MRS (ADR-0046)

Ver `docs/73_ADR_0046_ESTILO_MAPA_E_MALHA_FERREA_MRS.md` para a decisão
completa. Pedido do responsável pelo produto após testar a captação real
de GPS: mapa mais bonito, com a malha férrea da MRS sobreposta.

### Adicionado
- `painel/malha_ferrea.py` (novo): lê `malha_mrs.kml` (26 trechos,
  ~15.700 pontos, agora versionado pela primeira vez - necessário em
  runtime no Streamlit Cloud) via `defusedxml` (nova dependência,
  protege contra XXE - nunca `xml.etree.ElementTree` puro), com cache em
  memória por processo (mesmo padrão do JS do ECharts em
  `painel/graficos.py`).
- Nova camada "Malha ferrea MRS" no mapa operacional
  (`painel/mapa.py::construir_mapa`, parâmetro `trilhos_ferrovia`),
  sempre visível, inclusive sem nenhum pulso carregado.
- 7 casos novos em `tests/test_malha_ferrea.py`.

### Alterado
- `painel/mapa.py`: pulsos brutos em amarelo fixo (cor por qualidade
  removida - a qualidade continua no popup), trajetória simplificada em
  vermelho tracejado-pontilhado, basemap trocado para `cartodbpositron`
  (claro, prioriza legibilidade de ruas).
- `tests/test_mapa.py`: teste de cor-por-qualidade substituído por
  testes de cor fixa/trajetória/camada da malha férrea.

### Validação NÃO realizada
- Renderização visual real num navegador (mesma limitação de sempre -
  sandbox sem Chromium/Playwright) - conferido só via preview HTML local
  e testes automatizados; pedir ao responsável pelo produto para validar
  no painel publicado.

## [2026-08-04] Captação periódica de pulso GPS na interface de campo - Fase 2 (ADR-0045)

Ver `docs/72_ADR_0045_CAPTACAO_PERIODICA_PULSO_GPS_FASE_2.md` para a
decisão completa. Fecha o ciclo iniciado no ADR-0042/0043/0044: a
interface de campo agora captura pulsos de GPS de verdade.

### Adicionado
- Captura periódica de GPS (1 pulso/minuto) durante toda a jornada
  `ABERTA`, 100% offline - `iniciarCapturaPeriodica`/`pararCapturaPeriodica`
  em `interface_campo/js/geolocalizacao.js`.
- Fila local de pulsos no IndexedDB (`interface_campo/js/armazenamento.js`,
  `VERSAO_BANCO` v1 → v2, novo object store `pulsos`), sincronizada em
  lote pro backend (`POST /pulsos`, Fase 1) no mesmo gatilho que a
  jornada já usa hoje (`dispararSincronizacao()`).
- Trava de "GPS obrigatório" (ADR-0043) para iniciar/encerrar jornada e
  iniciar/encerrar atividade - a transição só é aplicada se uma leitura
  de GPS local for obtida com sucesso; pulsos periódicos de fundo nunca
  bloqueiam, só deixam uma lacuna visível.
- `novoPulsoGps` em `interface_campo/js/entidades.js`,
  `pulsoParaPayload`/`sincronizarPulsos` em
  `interface_campo/js/sincronizacao.js`.
- `capturarPosicaoAtual` passa a devolver `velocidadeMetrosSegundo`/
  `direcaoGraus` (quando o navegador fornece) - habilita a avaliação de
  qualidade por velocidade reportada pelo aparelho, já pronta do lado do
  domínio desde o Incremento 7.
- 24 casos novos em `tests/js/geolocalizacao.test.mjs` e
  `tests/js/sincronizacao.test.mjs` (118 testes JS no total, sem
  regressão).

### Alterado
- `interface_campo/service-worker.js`: `CACHE_VERSAO` v17 → v18.
- `interface_campo/index.html`: aviso da tela atualizado, rodapé "Versão
  v18".

### Validação NÃO realizada
- Teste em celular real (permissão de geolocalização, comportamento em
  segundo plano com a tela bloqueada, consumo de bateria, upgrade do
  IndexedDB num aparelho que já tinha o app instalado) - necessário antes
  de considerar a Fase 2 pronta para operação real.

## [2026-08-04] Backend real de pulsos GPS - Fase 1 da captação de geolocalização (ADR-0044)

Ver `docs/71_ADR_0044_BACKEND_REAL_PULSOS_GPS_FASE_1.md` para a decisão
completa. Sequência de ADR-0042 (levantamento) e ADR-0043 (decisões de
negócio) - primeira fatia validável rumo à captação real de GPS: backend
+ painel, sem depender de celular real.

### Adicionado
- `src/workforce_api/repositorio_pulsos_postgres.py` (novo): tabela
  `pulsos_gps` (JSONB, mesmo padrão de `jornadas`), upsert em lote numa
  transação só.
- `POST /pulsos` (recebe lote, não pulso único - reflete a decisão de
  sincronizar tudo de uma vez ao encerrar a jornada) e `GET /pulsos`
  (`jornada_id` obrigatório) em `src/workforce_api/app.py`.
- `carregar_pulsos_via_api` em `painel/dados.py`.
- `tests/test_mapa_operacional_painel.py` (novo, `AppTest` end-to-end) -
  confirma que `st_folium` funciona sob teste automatizado, incluindo o
  caminho feliz com pulsos reais.
- 9 casos novos em `tests/test_workforce_api.py`, 1 novo em
  `tests/test_gps.py`.

### Corrigido - dois bugs reais encontrados escrevendo os testes desta ADR
- `RepositorioPulsosGpsArquivo.ler_pulsos` não ordenava por
  `timestamp_dispositivo` (devolvia na ordem de gravação) nem
  deduplicava por `id` (reenvio do mesmo pulso aparecia duplicado) -
  existiam desde o Incremento 7, nunca exercitados por um cenário de
  lote/reenvio até agora. Corrigido na leitura (escrita continua um
  append puro, de propósito).

### Alterado
- `painel/telas/mapa_operacional.py`: fonte de dados fixa em API (mesmo
  padrão do ADR-0041), botão "Sincronizar dados". Botão "Gerar pulsos de
  exemplo" removido (escrevia num diretório que a tela não lê mais) - a
  tela agora mostra "nenhum pulso encontrado" pra toda jornada real até
  a Fase 2 (captação na interface de campo) existir - estado real do
  sistema, não regressão.

### Validação
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: 318 passed (304 + 14 novos), sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Conexão real com Postgres **não realizada** (sem servidor disponível
  neste ambiente, mesma ressalva do ADR-0017). Teste visual em navegador
  real **não realizado** - sandbox sem Playwright/Chromium.

### Fora de escopo (Fase 2, sessão futura)
Captação periódica na interface de campo, fila offline (IndexedDB), "GPS
obrigatório" pra iniciar/encerrar jornada/atividade - precisa de teste em
celular real.

## [2026-08-03] Fonte de dados fixa em API (nuvem) - sem seleção visível, botão de sincronizar (ADR-0041)

Ver `docs/68_ADR_0041_FONTE_DE_DADOS_FIXA_EM_API.md` para a decisão
completa. Pedido do responsável do produto: "os arquivos sempre virão
da API (Nuvem)" - esconder o seletor Fonte de Dados/URL/token,
substituir por um botão de sincronizar no canto superior direito.

### Alterado
- `painel/telas/dashboard.py`, `painel/telas/falhas.py`: removido o
  seletor "Arquivo local"/"API (nuvem)" e os campos de URL/token -
  credenciais agora vêm exclusivamente de `st.secrets`. Sem secrets
  configurados, mostra `st.error` orientando a configurar (Streamlit
  Cloud → Settings → Secrets) em vez de pedir pra digitar. Botão
  "🔄 Sincronizar dados" adicionado ao lado do título - mais uma
  reafirmação visual que uma necessidade técnica, já que
  `carregar_jornadas_via_api` não tem cache e todo rerun do Streamlit
  já busca os dados de novo automaticamente.
- Efeito colateral: o botão "Gerar dados de exemplo" e o expander
  "Simulador de dados (ETL)" (ADR-0033) só existiam no modo "Arquivo
  local" - saíram da UI publicada junto com esse modo. As funções
  continuam em `painel/dados.py`, testadas, disponíveis pra uso local
  durante desenvolvimento.

### Adicionado
- `tests/test_dashboard_painel.py` (novo, `AppTest` end-to-end,
  mesmo padrão de `test_falhas_painel.py`) - a "Visão geral" não tinha
  essa camada de teste de ponta a ponta antes.

### Corrigido
- `tests/test_falhas_painel.py` dependia do fluxo "Arquivo local"
  removido - reescrito pra simular a API via `AppTest.secrets` +
  `monkeypatch` em `dados.carregar_jornadas_via_api`, com um teste novo
  cobrindo secrets ausentes.

### Validação
- `python -m py_compile` nos módulos e testes tocados: OK.
- `pytest` completo: 304 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** (alinhamento do
  botão, toast) - sandbox sem Playwright/Chromium; o comportamento
  funcional, porém, foi validado de ponta a ponta via `AppTest`.

## [2026-08-03] Logo da sidebar - tamanho dobrado e quebra de linha (ADR-0040)

Ver `docs/67_ADR_0040_LOGO_SIDEBAR_TAMANHO_DOBRADO_QUEBRA_LINHA.md`
para a decisão completa. Com o testid certo (ADR-0039), o logo passou
a aparecer - mas cortado/sobreposto pelo título "Análise de Dados"
logo abaixo. Pedido: dobrar o tamanho e quebrar linha pra não sobrepor.

### Corrigido - causa raiz da sobreposição
- `stSidebarHeader` (container pai do logo e do botão de recolher a
  sidebar) tem `height` **fixa** (token de tema pensado pra um logo de
  ~24-32px) e `flex-wrap` desligado - confirmado no bundle JS
  instalado. O logo maior estourava essa altura fixa sem empurrar o
  conteúdo seguinte pra baixo, causando a sobreposição.

### Alterado
- `painel/estilo.py`: `[data-testid="stSidebarLogo"]` com
  `height: 240px` (dobrado de 120px) e `flex: 1 1 100%` (ocupa a linha
  inteira). `[data-testid="stSidebarHeader"]` com `height: auto` +
  `flex-wrap: wrap` - o botão de recolher agora quebra pra linha de
  baixo em vez de disputar espaço/sobrepor. Botão com
  `margin-left: auto` pra continuar alinhado à direita na própria
  linha.

### Validação
- Estrutura do container pai confirmada no bundle JS instalado.
- `python -m py_compile` em `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0040).

## [2026-08-03] Logo da sidebar continuava pequeno - testid errado corrigido (ADR-0039)

Ver `docs/66_ADR_0039_LOGO_SIDEBAR_TESTID_ERRADO.md` para a decisão
completa. Terceiro relato do responsável do produto: nenhuma mudança
de tamanho mesmo depois do ADR-0038.

### Corrigido
- `painel/estilo.py`: o CSS testava `[data-testid="stLogo"]` - testid
  que existe de verdade no DOM, mas é o do logo do **cabeçalho
  principal** (mostrado quando a sidebar está recolhida), não o de
  dentro da sidebar. Rastreado no bundle JS instalado do Streamlit até
  o ponto exato de uso: o componente da sidebar chama o mesmo
  `LogoComponent` passando `dataTestId="stSidebarLogo"` explicitamente,
  sobrescrevendo o default `stLogo`. Seletor corrigido pra
  `[data-testid="stSidebarLogo"]`.

### Validação
- Testid rastreado até o ponto exato de uso no bundle JS (não só
  confirmado que existe em algum lugar do arquivo).
- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0039).

## [2026-08-03] Logo da sidebar continuava pequeno - seletor CSS corrigido (ADR-0038)

Ver `docs/65_ADR_0038_LOGO_SIDEBAR_CSS_SELETOR_ERRADO.md` para a
decisão completa. Pedido do responsável do produto: logo continuava
pequeno mesmo depois do CSS do ADR-0037.

### Corrigido
- `painel/estilo.py`: a regra CSS que definia `height: 120px` buscava
  um `<img>` **dentro** de `[data-testid="stLogo"]` - inspecionado o
  bundle JS minificado instalado do Streamlit
  (`streamlit/static/static/js/index.*.js`, componente
  `LogoComponent`), confirmado que `data-testid="stLogo"` fica na
  própria tag `<img>`, não num container - a regra nunca casava com
  nada. Corrigida pra uma única regra direta no elemento; centralização
  via `margin: auto` em vez de `display: flex` (que não tem efeito
  visual num elemento `<img>` sem filhos).

### Validação
- Estrutura do componente confirmada lendo o bundle JS instalado
  diretamente (não suposição).
- `python -m py_compile` em `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0038).

## [2026-08-03] Logo da sidebar - animação quebrada corrigida, volta pra st.logo + GIF (ADR-0037)

Ver `docs/64_ADR_0037_LOGO_SIDEBAR_ANIMACAO_QUEBRADA_STLOGO.md` para a
decisão completa. Pedido do responsável do produto: o WebP do ADR-0036
apareceu estático; reposicionar acima do título "Análise de Dados",
centralizado; mp4 como alternativa se necessário.

### Corrigido - causa raiz real (lida no código-fonte do Streamlit)
- `st.image`/`st.logo` **sempre** achatam imagem animada pra 1 quadro
  quando o formato de saída não bate com o de entrada ou é preciso
  redimensionar - e WebP nunca é reconhecido como formato de saída
  (só JPEG/PNG/GIF existem em `ImageFormat`), então sempre vira JPEG
  estático. Não foi erro na conversão do ADR-0036 - é uma limitação
  real do Streamlit com esse formato, confirmada testando a lógica
  real da lib instalada contra o arquivo deste projeto.
- GIF é o único formato que o pipeline preserva intacto, e só quando
  cabe no layout sem redimensionar - confirmado (bytes de saída
  idênticos aos de entrada, 240 quadros) pro arquivo deste projeto.

### Alterado
- `painel/app.py`: `st.sidebar.image(webp)` → `st.logo(gif,
  size="large")`. `st.navigation` sempre ancora o menu no topo da
  sidebar independente da ordem do código (confirmado nesta sessão com
  `st.sidebar.video` e `st.sidebar.image`) - só o slot do `st.logo`
  fica genuinamente acima dele, por isso a volta pra essa API.
- `painel/assets/logo_sgo_workforce.gif` restaurado (arquivo original,
  sem reprocessar - uma tentativa de reduzir pra 320px quase não
  mudou o tamanho do arquivo, esse tipo de gradiente contínuo comprime
  mal em GIF em qualquer resolução). `.webp` removido.
- `painel/estilo.py`: `st.logo` limita a altura a 32px mesmo com
  `size="large"` (limite documentado do próprio Streamlit) - CSS
  escopado a `[data-testid="stSidebar"] [data-testid="stLogo"]`
  sobrescreve pra `height: 120px`, centraliza e mantém a moldura.
  Escopo por `stSidebar` preserva o logo pequeno mostrado no canto
  quando a sidebar está recolhida.

### Por que não foi pro mp4
`st.logo` só aceita imagem, não vídeo - como só esse slot fica acima
do menu de navegação, mp4 exigiria abrir mão do posicionamento pedido.
O GIF restaurado resolve os dois pedidos (animação + posição) ao mesmo
tempo, sem essa troca.

### Validação
- Pipeline real do Streamlit testado diretamente: bytes idênticos,
  240 quadros preservados.
- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0037).

## [2026-08-03] Logo da sidebar convertido pra WebP - mesma qualidade, 3.2x mais leve (ADR-0036)

Ver `docs/63_ADR_0036_LOGO_SIDEBAR_WEBP_LEVE.md` para a decisão
completa. Pedido do responsável do produto: converter o GIF (17.4MB)
mantendo a qualidade.

### Alterado
- `painel/assets/logo_sgo_workforce.gif` (17.4MB) → `.webp` (5.39MB,
  3.2x mais leve) - conversão via Pillow (sem `ffmpeg`/lib de vídeo
  disponível neste ambiente), 360x360/qualidade 85. Mesma contagem de
  quadros (240) e loop infinito do GIF original - nenhuma perda
  perceptível, porque a redução veio de resolução (a imagem é exibida
  a 260px na sidebar, 720px original era desperdício de banda), não de
  compressão agressiva da qualidade visual.
- `painel/app.py`: referência direta ao `.webp` (fallback pro `.gif`,
  que só existia como rede de segurança durante a conversão, removido).
- `painel/assets/logo_sgo_workforce.gif` removido do repositório - não
  é mais referenciado em lugar nenhum.

### Descoberta durante a conversão
- Primeira tentativa converteu os quadros pra RGBA "por segurança" e
  saiu **maior** que o GIF (38MB) - o GIF não tem transparência real
  (confirmado: alpha sempre 255), então RGBA só aumentou a
  profundidade de cor sem necessidade. Corrigido convertendo pra RGB.
- Mesmo em RGB, qualidade alta em 720x720 nunca chegou perto do
  tamanho do mp4 original (2.8MB) - esse tipo de conteúdo (gradientes
  de neon contínuos, 240 quadros) não tem muita redundância
  intra-quadro pra WebP/GIF explorarem, diferente de um codec de vídeo
  de verdade (H.264) que explora redundância *entre* quadros. A saída
  real foi resolução, não formato/qualidade.

### Validação
- WebP final verificado via Pillow: 360x360, 240 quadros, animado,
  loop infinito - igual ao GIF original.
- `python -m py_compile` em `painel/app.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0036).

## [2026-07-31] Logo da sidebar - tamanho e centralização (ADR-0035)

Ver `docs/62_ADR_0035_LOGO_SIDEBAR_TAMANHO_CENTRALIZACAO.md` para a
decisão completa. Pedido do responsável do produto após ver o ADR-0034
publicado: logo continuava minúsculo mesmo com `size="large"`.

### Alterado
- `painel/app.py`: `st.logo(...)` trocado por
  `st.sidebar.image(caminho, width=260)` - `st.logo` é um slot fixo
  pequeno do Streamlit sem controle real de largura/alinhamento;
  `st.sidebar.image` é um elemento comum do corpo da sidebar, com
  largura configurável de verdade.
- `painel/estilo.py`: centralização + moldura (cantos arredondados,
  sombra) via CSS escopado a `[data-testid="stSidebar"]
  [data-testid="stImage"]` - não afeta nenhum outro `st.image` do
  painel.
- `app.py` agora procura primeiro `logo_sgo_workforce.webp` (conversão
  mais leve em andamento) e cai pro `.gif` se ainda não existir.

### Validação
- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0035).

## [2026-07-31] Logo animado (GIF) na sidebar, substituindo vídeo e logo estático da MRS (ADR-0034)

Ver `docs/61_ADR_0034_LOGO_GIF_SIDEBAR_PREMIUM.md` para a decisão
completa. Pedido do responsável do produto após ver o resultado do
ADR-0033 publicado: "a estética está muito pobre" - o logo da MRS
pequeno/genérico e o vídeo mostrando a barra de controles nativa do
navegador por baixo. Pediu pra usar `Logo - SGO Workforce 1x1.gif`
(mesma animação do mp4, formato GIF) no lugar da MRS, e tirar o vídeo.

### Alterado
- `painel/app.py`: `st.sidebar.video(...)` (ADR-0033) removido.
  `st.logo(...)` passou a apontar pra
  `painel/assets/logo_sgo_workforce.gif` (antes: `logo_mrs.png`), com
  `size="large"`. GIF anima nativamente numa `<img>` comum, sem
  precisar de `autoplay`/`loop`/`muted` nem mostrar nenhuma barra de
  controles - resolve o problema relatado sem código extra.
- `painel/estilo.py`: moldura discreta (`border-radius` + `box-shadow`)
  pro slot `[data-testid="stLogo"]` - acabamento premium sem mexer no
  tamanho/posição que o Streamlit já controla.

### Removido
- `painel/assets/logo_sgo_workforce.mp4` - não é mais referenciado em
  lugar nenhum.

### Ressalva conhecida
- O GIF (17.4MB) é bem mais pesado que o mp4 substituído (2.8MB) - GIF
  é formato ineficiente pra conteúdo tipo vídeo. Troca aceita
  deliberadamente (pedido explícito); pode deixar o carregamento
  inicial da sidebar mais lento numa conexão ruim.

### Validação
- `python -m py_compile` em `painel/app.py`, `painel/estilo.py`: OK.
- `pytest` completo: 300 passed, sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0034, seção "Validação NÃO realizada").

## [2026-07-31] Reescrita dos gráficos (legenda inferior, sem título interno), logo em vídeo na sidebar e simulador ETL (ADR-0033)

Ver `docs/60_ADR_0033_REESCRITA_GRAFICOS_LEGENDA_INFERIOR_E_LOGO_SIDEBAR.md`
para a decisão completa. Pedido explícito do responsável do produto:
"os gráficos estão estranhos, refaça do zero" - substitui as regras
condicionais do ADR-0032 (título/legenda escondidos caso a caso) por
uma regra única sem exceção, inspirada no padrão já usado em produção
no app.py de Gestão_OS (`streamlit_echarts`, legenda sempre embaixo,
sem título no option).

### Alterado
- `painel/graficos.py` **reescrito por completo**: todo gráfico usa
  `title_opts=_SEM_TITULO` (nunca mostra título interno - quem
  identifica o bloco é o `st.expander` em `painel/telas/*.py`) e
  `legend_opts=_legenda_inferior_opts()` (legenda sempre visível,
  horizontal, embaixo do gráfico, com paginação automática) - única
  exceção é o gauge, que não tem série pra legendar. Todo gráfico
  cartesiano usa `_aplicar_grid()` com margem generosa o bastante pra
  caber rótulo de eixo rotacionado **e** a legenda embaixo, sem cortar
  nenhum dos dois.
- Efeito colateral positivo: mover a legenda do scatter "Duração média
  x frequência por motivo" da lateral pra baixo resolve de graça o bug
  do ADR-0032 (colisão com os pontos de frequência baixa) - uma
  legenda horizontal embaixo nunca disputa espaço com o gráfico. O
  `left="30%"` (correção pontual anterior) foi removido.
- `painel/telas/dashboard.py`, `painel/telas/falhas.py`: alturas dos
  `components.html` ajustadas ao novo layout; `st.caption(...)`
  adicionado acima de cada gráfico nos expanders que dividem o bloco
  entre dois gráficos (ex.: ranking + donut de sintoma) - a forma de
  diferenciar os dois sem usar título interno no ECharts.

### Adicionado
- Logo em vídeo do produto (`Logo - SGO Workforce 1x1.mp4`, fornecido
  pelo responsável do produto) na sidebar do painel
  (`painel/app.py`, `painel/assets/logo_sgo_workforce.mp4`) - abaixo do
  logo corporativo MRS já existente (`st.logo`), via `st.sidebar.video`
  (autoplay, loop, mudo). `st.video` em vez de HTML cru em base64: o
  Streamlit reexecuta o script inteiro a cada interação de filtro, e o
  arquivo de mídia servido pelo endpoint dedicado do Streamlit é
  cacheado pelo navegador - um vídeo embutido em base64 seria reenviado
  por inteiro (~3.8MB) a cada rerun.
- **Simulador ETL de dados em volume** (`painel/dados.py:
  gerar_jornadas_exemplo_volumoso`): gera muitas jornadas
  colaborador×dia (motivo/categoria sorteado entre os ~19 códigos EE
  reais, mesmo motor de domínio da interface de campo real, sem atalho)
  pra ver como os gráficos se comportam com volume real, em vez dos 3
  exemplos fixos de `gerar_jornadas_exemplo`. Novo expander "Simulador
  de dados (ETL)" em `painel/telas/dashboard.py`, com número de
  colaboradores/dias configurável.

### Corrigido (durante a implementação do simulador ETL)
- `gerar_jornadas_exemplo_volumoso` sorteava também motivos legados de
  `catalogo_padrao()` (PAUSA_TESTE, REFEICAO, DDS etc., `tipo_registro`
  "pausa" por padrão), duplicando visualmente o mesmo motivo com dois
  códigos diferentes (ex.: "REFEICAO" e "EE02 - Refeição 1 hora" como
  barras separadas) - filtro `codigo.startswith("EE")` adicionado antes
  de expor a função.
- Primeira versão tentava abrir o atendimento de falha simulado com a
  atividade EE17 ainda ativa (`iniciar_atendimento_falha` abre sua
  própria atividade, não aninha) - disparava `AtividadeJaAtivaError`;
  corrigido encerrando a EE17 antes do bloco de falha.

### Corrigido (dois bugs reais só visíveis com o simulador ETL em volume)
- **Tooltip cortado na borda do iframe**: gráficos com muitas séries
  (ex.: "HH por colaborador") mostram um tooltip alto o bastante pra
  estourar o topo do iframe do Streamlit, cortando as primeiras linhas
  em vez de reposicionar. `is_confine=True` adicionado nos **13**
  `TooltipOpts` do módulo (não só no gráfico relatado - mesmo risco em
  qualquer gráfico com tooltip de várias séries).
- **Sunburst "Falhas por ativo e sintoma" ilegível com volume real**: 10
  ativos x 8 sintomas simulados = 80 fatias finas demais pro texto do
  rótulo, todas se sobrepondo. `label.minAngle=8` esconde rótulo de
  fatia abaixo de 8° (resto continua no tooltip); radius e altura
  também aumentados pra dar mais espaço aos rótulos visíveis.

### Alterado (mesmo dia - pedido direto do responsável do produto)
- **Sunburst substituído por funil**: o ajuste de `minAngle` acima não
  foi suficiente - continuou ilegível com o mesmo dado de volume.
  `grafico_sunburst_ativo_sintoma` (`pyecharts.charts.Sunburst`) virou
  `grafico_funil_duracao_por_sintoma` (`pyecharts.charts.Funnel`) -
  única troca de tipo de gráfico desta ADR (todas as outras correções
  preservaram o tipo). Funil é série única, não hierarquia de 2 níveis:
  a dimensão "ativo" é colapsada (duração somada por sintoma, todos os
  ativos juntos) - "Ativos reincidentes" e a tabela "Ocorrências por
  ativo" (mesma tela) já cobrem a dimensão ativo isoladamente. Expander
  renomeado de "Falhas por ativo e sintoma" para "Duração de falhas por
  sintoma".
- **Rótulo (nome + valor) dentro da área colorida** - funil, pizza
  ("Distribuição de HH") e donut ("Ocorrências por sintoma"/"por
  objeto"): `label_opts` ganhou `position="inside"` (antes: rótulo do
  lado de fora com linha apontando, padrão default do ECharts) e cor
  branca pra contraste sobre a fatia colorida. Pizza/donut também
  ganharam `min_show_label_angle=8` (parâmetro nativo do pyecharts) pra
  esconder rótulo de fatia fina demais pro texto caber - mesmo
  raciocínio do `minAngle` do sunburst, necessário porque esses dois
  gráficos também têm até 19 categorias com o simulador ETL.

### Validação
- `python -m py_compile` nos módulos tocados: OK.
- 16 funções de gráfico renderizadas com dado realista e inspecionadas
  via `dump_options()`: título sempre oculto, legenda sempre visível
  embaixo (exceto gauge), grid com `containLabel=True` sem exceção.
- `gerar_jornadas_exemplo_volumoso` chamado direto (20 colaboradores, 30
  dias): 500+ jornadas, 0 erro ao recarregar, 20 motivos EE distintos,
  ~90 atendimentos de falha - novo teste
  `test_gerar_jornadas_exemplo_volumoso_produz_dado_variado`.
- `pytest` completo: 300 passed, sem regressão (rodado de novo após
  cada correção).
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log (rodado de novo após o simulador ETL).
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log - confirma que o launcher (incluindo o novo vídeo na
  sidebar) executa sem erro em runtime.
- Teste visual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium (ver ADR-0033, seção "Validação NÃO realizada").

## [2026-07-31] Revisão premium dos gráficos e abas recolhíveis (ADR-0032)

Ver `docs/59_ADR_0032_REVISAO_PREMIUM_GRAFICOS_E_ABAS_RECOLHIVEIS.md`
para a decisão completa. Pedido explícito do responsável do produto após
relatar (com captura de tela real) o eixo X cortado e um novo caso de
legenda sobreposta ao título no gráfico "HH por categoria", mais o
pedido de agrupar cada bloco de gráfico numa aba recolhível e revisar o
design de todos os gráficos.

### Corrigido
- **Sobreposição título/legenda (bug real, dado de produção)**: 12
  funções de gráfico de série única (`grafico_hh_por_categoria`,
  `grafico_evolucao_diaria`, `grafico_hh_por_motivo`,
  `grafico_utilizacao_por_colaborador`,
  `grafico_sankey_colaborador_categoria`,
  `grafico_ranking_duracao_falhas`, `grafico_evolucao_diaria_falhas`,
  `grafico_hh_falhas_por_colaborador`,
  `grafico_duracao_media_por_sintoma`, `grafico_reincidencia_ativos`,
  `grafico_sunburst_ativo_sintoma`, `grafico_gauge_percentual`) nunca
  passavam `legend_opts` - o pyecharts registra uma legenda por padrão
  mesmo assim, e sem posição explícita o ECharts centraliza essa legenda
  no topo, exatamente sobre o título. Nova `_legenda_oculta_opts()`
  aplicada em todas.
- **Eixo X cortado na base**: nenhum gráfico usava `containLabel` na
  área de plotagem - rótulo rotacionado com nome longo estourava a
  margem reservada e era cortado na borda do canvas. Nova
  `_aplicar_grid()` (`is_contain_label=True` + margem generosa) aplicada
  em todo gráfico cartesiano.
- **Descoberta de API**: o pyecharts 2.1.0 (versão instalada) removeu o
  parâmetro `grid_opts` de `set_global_opts` - `_aplicar_grid` escreve
  direto em `grafico.options["grid"]`, mesmo mecanismo que o próprio
  pyecharts usa para `xAxis`/`yAxis`.

### Adicionado
- `painel/telas/dashboard.py`, `painel/telas/falhas.py`: cada bloco de
  gráfico agora fica dentro de `st.expander(titulo, expanded=True)` em
  vez de `st.subheader` solto - abas recolhíveis, nada escondido por
  padrão.
- `painel/graficos.py`: paleta unificada (`COR_PRODUTIVIDADE`,
  `COR_FALHA_INFO`, `COR_FALHA_ALERTA`) alinhada às cores de marca dos
  cards KPI, eixos com estilo consistente
  (`_eixo_valor_opts`/`_eixo_categoria_opts`), nome no eixo de valor nos
  gráficos que perderam a legenda, cantos arredondados nas barras, área
  sob a linha nos gráficos de evolução diária.

### Corrigido (mesmo dia, após relato adicional)
- **Legenda lateral do scatter "Duração média x frequência por motivo"
  colidindo com os pontos**: `_aplicar_grid` fixava a margem esquerda em
  2% para todo gráfico, mas esse scatter usa uma série por motivo (até
  ~19) na legenda lateral, que precisa de bem mais espaço horizontal -
  os pontos de frequência baixa ficavam desenhados por baixo da lista de
  nomes. `_aplicar_grid` ganhou parâmetro `left` configurável
  (`left="30%"` nesse gráfico); o gráfico também saiu da coluna de
  metade da tela e ganhou expander próprio em largura cheia.
- **Título do gráfico duplicando o cabeçalho do expander**: agora que
  todo bloco tem `st.expander(titulo, ...)` visível acima (seção
  "Adicionado"), o título interno do ECharts repetia o mesmo texto
  quando o gráfico é o único do bloco (relatado com captura de tela real
  no gráfico "HH por motivo/justificativa"). `_titulo_opts` ganhou
  `mostrar: bool = True`, e 8 funções de gráfico ganharam
  `mostrar_titulo: bool = True` repassado a ela. `painel/telas/
  dashboard.py`/`falhas.py` passam `mostrar_titulo=False` só nos
  expanders com um único gráfico - nos que dividem o bloco entre dois
  gráficos (ex.: ranking + donut de sintoma), o título interno continua
  a única forma de diferenciar os dois.

### Validação
- `python -m py_compile` nos módulos tocados: OK.
- 13 funções de gráfico renderizadas com dado realista (19 categorias,
  nomes longos) e inspecionadas via `dump_options()`: legenda oculta nos
  gráficos de série única, grid com `containLabel=True`, sem exceção;
  grid do scatter confirmado com `left=30%`; toggle `mostrar_titulo`
  confirmado (`title[0].show` False/True conforme esperado) nas 8
  funções que o recebem.
- `pytest` completo: 299 passed, sem regressão (rodado de novo após cada
  correção - scatter e depois título duplicado).
- Teste manual em navegador real **não realizado** - sandbox sem
  Playwright/Chromium instalado (ver ADR-0032, seção "Validação NÃO
  realizada").

## [2026-07-31] Dashboard completo de produtividade/execução e detalhamento de falhas (ADR-0031)

Ver `docs/58_ADR_0031_DASHBOARD_COMPLETO_PRODUTIVIDADE_FALHAS.md` para a
decisão completa. Pedido explícito do responsável do produto após
relatar (com capturas de tela reais) título/legenda sobrepostos em vários
gráficos, o gauge com texto duplicado, o treemap ilegível e rótulos de
categoria em código cru.

### Corrigido
- **Bugs reais de renderização relatados em produção** (só visíveis com
  dado real, 12+ categorias — nunca reproduzidos nos smoke tests
  anteriores, que usavam poucas categorias): título e legenda sobrepostos
  em `grafico_distribuicao_pizza`, `grafico_hh_por_colaborador` e
  `grafico_donut_contagem`; gauge de Utilização HH duplicando o mesmo
  texto (título do gráfico + nome interno da série); treemap "HH por
  motivo/justificativa" cortando rótulos em "EE" ilegível.
- `painel/graficos.py`: `_titulo_opts`/`_legenda_lateral_opts`/
  `_legenda_superior_opts` (posicionamento fixo, nunca sobreposto) usados
  em todo gráfico com título/legenda. Gauge sem título/nome interno
  duplicado. Treemap **substituído** por `grafico_hh_por_motivo` (barra
  horizontal com rótulo completo, mesmo padrão do ranking de falhas).
- **Performance real**: `renderizar_embutido` relia `echarts.min.js`
  (1MB+) do disco a cada gráfico — com o dashboard ampliado (10+ gráficos
  por tela) isso virou um gargalo mensurável (uma bateria de testes que
  deveria durar segundos passou de dez minutos). `_ler_js_echarts_local`
  agora cacheia o conteúdo em memória por processo — mesma correção
  beneficia o Streamlit real, não só os testes.

### Adicionado
- `painel/dados.py`: `ROTULOS_CATEGORIA`/`rotulo_categoria`/`rotulo_motivo`
  — fonte única de rótulos legíveis em português, usada tanto pelos
  filtros das telas quanto pelos gráficos (nunca mais `categoria.value`
  cru num gráfico).
- `src/workforce_core/consolidacao.py`: `resumo_consolidado_por_colaborador`,
  `contagem_por_objeto`, `duracao_media_por_sintoma`, `ativos_reincidentes`,
  `agrupar_ativo_sintoma`.
- **Visão Geral**: Utilização HH por colaborador (bar), duração média x
  frequência por motivo (scatter), fluxo de HH colaborador→categoria
  (sankey).
- **Falhas**: distribuição por objeto/componente causador (donut),
  evolução diária de atendimentos (line), HH por colaborador (bar),
  duração média por sintoma (bar), reincidência de ativos (bar,
  condicional — só aparece se houver algum ativo reincidente), falhas
  por ativo e sintoma (sunburst).
- `tests/test_consolidacao.py`, `tests/test_painel.py`: testes para toda
  agregação e gráfico novos, incluindo verificação de posição de
  título/legenda via inspeção do JSON de opções do ECharts.

### Riscos
- Heatmap dia x hora (recomendado em `docs/12`) não implementado —
  exigiria capturar hora do evento em `LinhaEvento`, extensão de domínio
  maior que ficou fora desta sessão.
- Causa, ação e sistema continuam sem tela em Falhas — não capturados
  por `DadosFalha` hoje.
- Teste manual em navegador real não realizado — a correção de layout
  foi validada por inspeção do JSON de opções gerado (posições
  title/legend), não por renderização visual real; o próprio bug
  relatado nesta sessão só apareceu com uso real em produção.

## [2026-07-31] Número de versão visível no rodapé da interface de campo

### Adicionado
- `interface_campo/index.html`: rodapé agora mostra "Versão vNN",
  sincronizado manualmente com `CACHE_VERSAO` de `service-worker.js` a
  cada mudança. Motivo: dois relatos seguidos de "a correção não
  apareceu" que na verdade eram deploy/cache do navegador ainda não
  atualizado (código já estava correto no repositório nos dois casos,
  confirmado por `git log`/`grep`) — sem um número visível, não dava pra
  distinguir rapidamente "ainda não chegou" de "bug novo". `CACHE_VERSAO`
  incrementada (`v16` → `v17`).

## [2026-07-31] "Sincronizar agora" só aparece com a jornada encerrada

### Alterado
- `interface_campo/js/app.js`: o botão "Sincronizar agora" deixou de
  aparecer em toda tela com jornada aberta (pausa, atividade, evento
  secundário, lista de ações) e passou a aparecer só na tela de jornada
  encerrada — pedido do responsável do produto. A sincronização
  automática best-effort (após cada transição, `persistir()` →
  `dispararSincronizacao()`) continua acontecendo do mesmo jeito; o botão
  manual agora só serve como conferência final antes de fechar o app.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada
  (`v15` → `v16`).

### Testes
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js/*.test.mjs`: 107/107 (inalterado).
- `pytest`: 276/276 (inalterado, mudança só no lado JS).

## [2026-07-31] Lista única de ações na interface de campo (ADR-0030)

Ver `docs/57_ADR_0030_LISTA_UNICA_DE_ACOES.md` para a decisão completa.
Fluxo pedido explicitamente pelo responsável do produto, com confirmação
direta sobre um ponto que mudava regra de negócio (ver abaixo).

### Adicionado
- `src/workforce_core/catalogo.py`: `EE02`, `EE07`, `EE11`, `EE20`, `EE22`
  (Refeição, Reunião/ADM, Consulta à documentação técnica, DDS/APR,
  Treinamento) ganham `tipo_evento_secundario = APOIO`, mantendo
  `tipo_registro = "pausa"` - agora podem ser iniciados soltos (sem
  atividade ativa, mecânica de `EventoSecundario`) **e** continuam
  funcionando como pausa aninhada dentro de uma atividade em andamento,
  sem nenhuma mudança nesse segundo caminho. Confirmado explicitamente
  pelo responsável do produto (o exemplo original usava "DDS/APR" logo
  após "Iniciar Jornada", o que exigia essa mudança).
- `interface_campo/js/app.js`: `criarSeletorAcaoPrincipal` substitui a
  tela de topo (antes: 2 botões + 1 seletor separado) por uma lista
  única com "Iniciar atividade"/"Atendimento de falha" + os 20 códigos
  de pausa/deslocamento/espera/apoio, e um botão "Iniciar" único que vira
  "Encerrar" enquanto algo está em andamento, voltando pra mesma lista ao
  encerrar. "Encerrar jornada" continua separado, fora da lista.
- `interface_campo/js/catalogoMotivos.js`: `obterMotivosPausa` passa a
  aplicar o mesmo reparo defensivo de `tipo_evento_secundario` que
  `obterEventosSecundarios` já tinha (ADR-0026), agora cobrindo os 5
  códigos novos.
- `docs/11_TELAS_E_UX.md` atualizado.
- Testes: `tests/test_catalogo_relatorio_1.py`, `tests/test_repositorio_catalogo_postgres.py`
  (contagem de códigos com tipo 15 → 20), `tests/js/catalogoMotivos.test.mjs`
  (2 testes novos).

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 276/276.
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js/*.test.mjs`: 107/107 (era 105).

### Riscos
- Teste manual em navegador/celular real não realizado (mesma limitação
  de sempre).

## [2026-07-31] Corrige crash ao reabrir jornada antiga (bug real relatado pelo usuário)

### Corrigido
- **Bug real de produção**: `interface_campo/js/motorJornada.js::identificarEstadoAtivo`
  (chamada por `MotorJornada.aPartirDe`, usada na recuperação de estado ao
  reabrir o app) quebrava com `Cannot read properties of undefined
  (reading 'filter')` sempre que a jornada já persistida no IndexedDB do
  navegador tinha sido gravada **antes** de `eventosSecundarios`
  (ADR-0024) ou `ordensServico` (ADR-0025) existirem no formato — o app
  ficava travado em "Carregando..." com o erro cru exibido na tela,
  impossível de usar. O lado Python (`workforce_storage/serializacao.py`)
  já tinha essa retrocompatibilidade desde sempre (`.get(..., [])`); o
  lado JS nunca ganhou o equivalente.
- `normalizarCamposRetrocompativeis` (nova função interna): preenche
  `jornada.eventosSecundarios`/`atividade.ordensServico`/`atividade.pausas`
  ausentes com `[]` antes de qualquer leitura, chamada no início de
  `identificarEstadoAtivo` — mesmo princípio do lado Python.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada
  (`v13` → `v14`) — sem isso a correção não chega ao navegador de quem
  já tem o app instalado/cacheado.
- `tests/js/motorJornada.test.mjs`: novo teste reproduzindo exatamente o
  formato antigo (jornada sem `eventosSecundarios`, atividade sem
  `ordensServico`) e confirmando que `aPartirDe` recupera normalmente em
  vez de lançar exceção.

### Testes
- `node --check` em `motorJornada.js`/`service-worker.js`: OK.
- `node --test tests/js/*.test.mjs`: 105/105 (era 104).
- `pytest`: 275/275 (inalterado, mudança só no lado JS).

## [2026-07-31] Corrige aviso desatualizado na interface de campo

### Corrigido
- `interface_campo/index.html`: o rótulo "Incremento 4" no cabeçalho e o
  aviso de piloto ficaram desatualizados por vários incrementos — o texto
  dizia "GPS, atendimento de falhas e sincronização com servidor ainda
  não existem aqui" e "deslocamento/espera/apoio ainda não tem tela
  própria", quando na verdade os três já existem desde os ADRs 0017/0021/0024.
  Texto corrigido para refletir o estado real (GPS pontual no atendimento
  de falha, sem pulso periódico ainda; os 23 códigos do Relatório 1 já
  têm tela própria e classificação validada).
- `interface_campo/service-worker.js`: `CACHE_VERSAO` incrementada
  (`v12` → `v13`) — o service worker cacheia `index.html`, sem isso a
  correção não chegaria ao navegador do colaborador (mesma lição do
  primeiro bug real deste projeto, ver entrada mais antiga deste
  changelog).

### Testes
- `node --check` em `service-worker.js`: OK.

## [2026-07-31] Aba "Falhas" no painel — tempo de atendimento (ADR-0029)

Ver `docs/56_ADR_0029_ABA_FALHAS_PAINEL.md` para a decisão completa.
Pedido explícito do responsável do produto, com uma captura de tela de
referência de outro painel operacional da MRS.

### Adicionado
- `src/workforce_core/consolidacao.py`: `LinhaAtendimentoFalha`,
  `linhas_atendimento_falha` (duração **bruta**, fim-início, diferente de
  `linhas_eventos_classificadas`; inclui jornadas ainda abertas, desvio
  deliberado do padrão existente), `ResumoAtendimentosFalha`,
  `resumo_atendimentos_falha`, `contagem_por_sintoma`, `contagem_por_ativo`.
- `painel/dados.py`: wrappers finos para a tela; `painel/graficos.py`:
  `grafico_ranking_duracao_falhas` (barra horizontal top 15 por duração),
  `grafico_donut_contagem` (rosca genérica rótulo→contagem).
- `painel/telas/falhas.py` (novo): KPIs (total, tempo médio, maior
  duração, duração total), ranking por duração, donut por sintoma,
  contagem por ativo, tabela completa para drill-down. Registrada em
  `painel/app.py` entre "Visão geral" e "Mapa Operacional".
- `tests/test_falhas_painel.py` (novo): **primeira tela do painel testada
  de ponta a ponta** via `streamlit.testing.v1.AppTest` (script real
  rodando em runtime Streamlit "bare mode", não só `dados.py`/`graficos.py`
  isolados) — confirma zero exceções com dados de exemplo e com
  diretório vazio.
- `tests/test_consolidacao.py` (8 testes novos) cobrindo o novo domínio.
- `docs/12_DASHBOARDS_ECHARTS.md` atualizado.

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 275/275 (era 265).

### Riscos
- Só a dimensão "tempo de atendimento" foi implementada — causa, ação,
  sistemas, componentes, impacto e reincidência (as demais dimensões
  já previstas em `docs/12`) continuam sem tela.
- Nenhuma validação com a operação de que "ranking por duração +
  sintoma + ativo" são as dimensões certas — seguiu a referência
  fornecida, não um indicador oficial validado.

## [2026-07-31] Reintrodução de "Produtiva Não Rentável" (ADR-0028)

Ver `docs/55_ADR_0028_PRODUTIVA_NAO_RENTAVEL.md` para a decisão completa.
Decisão do responsável do produto ("Pode classificar como Produtiva Não
Rentável"), respondendo aos itens 15/16 registrados na sessão anterior.

### Adicionado
- `src/workforce_core/catalogo.py`: novo valor `ClassificacaoHH.PRODUTIVA_NAO_RENTAVEL`.
  `EE11`, `EE12`, `EE13`, `EE14`, `EE15`, `EE16`, `EE18`, `EE19`, `EE20`,
  `EE22` reclassificados de `PRODUTIVA`/`IMPRODUTIVA` para
  `PRODUTIVA_NAO_RENTAVEL` — mesma correspondência da tabela original do
  OptJob (consulta a documentação técnica, deslocamento, preparar/
  desmontar atividade, carregar/descarregar veículo, SMS, treinamento).
  `EE17`/`EE21` continuam `PRODUTIVA` (deliberado, ver ADR-0028 e novo
  item 17 em `docs/23_DECISOES_PENDENTES.md`).
- `painel/dados.py::horas_produtiva_nao_rentavel_do_resumo`: novo card KPI
  "HH produtivo não rentável" em `painel/telas/dashboard.py` (6ª coluna),
  ao lado de Utilização HH — o gestor vê as duas fatias sempre separadas.
- `docs/23_DECISOES_PENDENTES.md`: itens 15/16 marcados resolvidos; novo
  item 17 (se `EE21` deveria virar `PRODUTIVA_NAO_RENTAVEL` também).

### Alterado
- **Comportamento do indicador de Utilização HH muda**: "Horas Produtivas"
  no numerador agora significa só produtivo *rentável* (`EE17`/`EE21`) —
  antes incluía também deslocamento/preparação/etc. O percentual exibido
  no painel tende a cair depois desta mudança; é intencional, não um bug.

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 265/265 (era 264).

## [2026-07-30] Aprendizados dos manuais originais do OptJob

Leitura completa dos 27 PDFs em `Referencias/` (procedimentos
operacionais do OptJob MF/Via Permanente, pedido explícito do
responsável do produto). Só documentação — nenhum código alterado.

### Adicionado
- `docs/21_APRENDIZADOS_HERDADOS_SGO.md`: nova seção com achados
  confirmados por texto real dos manuais — motivação histórica das
  Regras de Ouro nº 2 e nº 5 (o OptJob desktop tinha exclusão real de
  apontamento e digitação manual de HH via "Produção Complementar"),
  sincronização manual/esquecível (já mitigada no Workforce por sync
  automático), a taxonomia original de 5 níveis de "Tipo de Hora" (o
  Workforce tem 4, sem "Produtiva Não Rentável"), a proveniência
  provável (mas não confirmada) dos códigos EE01-EE23, uma ambiguidade
  de sigla "EE" a evitar, e a diferença deliberada de apontar por
  indivíduo (Workforce) vs. por equipe (OptJob).
- `docs/23_DECISOES_PENDENTES.md`: itens 15 e 16 — revisar a
  classificação de `EE16` "Desmontar atividade" (possível mismatch com
  o original) e se vale adotar uma quarta categoria "Produtiva Não
  Rentável" em `ClassificacaoHH`. Nenhuma das duas foi decidida ou
  aplicada no código — são decisões de negócio do responsável do
  produto, não inferência do agente.
- Confirmado nos manuais: **nenhuma fórmula de "Utilização de HH" ou
  "Performance" foi encontrada** nos procedimentos operacionais do
  OptJob — reforça a abordagem já tomada no ADR-0027 (fórmulas puras,
  sem nenhum dado fabricado).

## [2026-07-30] Indicadores de Utilização HH e Performance (ADR-0027)

Ver `docs/54_ADR_0027_INDICADORES_UTILIZACAO_HH_E_PERFORMANCE.md` para a
decisão completa.

### Adicionado
- `src/workforce_core/consolidacao.py`: `resumo_por_classificacao_hh`
  (agrega HH de uma jornada por `ClassificacaoHH`, mesmo padrão de
  `resumo_por_categoria`); `ResumoConsolidado.por_classificacao_hh`
  (agregado multi-jornada, populado em `resumo_consolidado`);
  `utilizacao_hh(horas_produtivas, horas_totais)` = Horas Produtivas /
  Horas Totais; `performance(tempo_planejado, tempo_real)` = Tempo
  Planejado / Tempo Real — ambas funções puras, sem fonte de dado
  embutida, retornam `None` (nunca `ZeroDivisionError`) quando o
  denominador é zero.
- `painel/dados.py::utilizacao_hh_do_resumo(resumo)`: conveniência que
  usa `por_classificacao_hh[PRODUTIVA]` e `jornada_bruta_total` do
  `ResumoConsolidado` já calculado pelo resto do painel.
- `painel/graficos.py::grafico_gauge_percentual`: primeiro gráfico gauge
  do painel (tipo já recomendado em `docs/12_DASHBOARDS_ECHARTS.md` para
  capacidade/utilização, nunca usado até este incremento).
- `painel/telas/dashboard.py`: 5º card KPI "Utilização HH" e uma nova
  seção "Indicadores" com o gauge; ao lado, um aviso explícito de que
  Performance ainda não tem tela (depende de fonte de tempo planejado,
  ver decisão pendente abaixo) em vez de simplesmente omitir o assunto.
- `docs/23_DECISOES_PENDENTES.md`: novo item 14, fonte de tempo
  planejado por atividade/OS para o indicador de Performance — decisão
  de negócio pendente, não inventada.
- `docs/07_MOTOR_EVENTOS_E_HH.md` e `docs/12_DASHBOARDS_ECHARTS.md`
  atualizados com os dois indicadores.
- `tests/test_consolidacao.py` (8 testes novos): classificação real via
  catálogo do Relatório 1 (EE12/EE02/EE17/EE21) reconciliando com a
  jornada bruta, agregação multi-jornada, e as duas fórmulas com guarda
  de divisão por zero.
- `tests/test_painel.py` (4 testes novos): `por_classificacao_hh`/
  `utilizacao_hh_do_resumo` com dados de exemplo, `None` sem HH bruto, e
  o gauge renderizando HTML autocontido sem CDN.

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 264/264 (era 252, ver entrada anterior deste changelog).

### Riscos
- Nenhuma meta/limiar de "boa" Utilização HH foi definida — o card e o
  gauge só mostram o número, sem cor de alerta associada a nenhum
  patamar (evita inventar uma meta que só o responsável do produto pode
  validar).
- Performance continua sem nenhuma tela até a decisão pendente (item 14)
  ser resolvida.

## [2026-07-30] Reparo retroativo de tipo_evento_secundario (ADR-0026) — bug real de produção

Ver `docs/53_ADR_0026_REPARO_TIPO_EVENTO_SECUNDARIO.md` para a decisão
completa.

### Corrigido
- **Bug real de produção** relatado em 2026-07-29: a interface de campo
  travava com "O tipo do evento secundário (DESLOCAMENTO/ESPERA/APOIO) é
  obrigatório." toda vez que o colaborador tentava "Iniciar deslocamento/
  espera/apoio" (ex.: `EE01 - Preparação para jornada`, o código padrão
  logo após abrir a jornada). Causa raiz: o `ALTER TABLE ... ADD COLUMN`
  que criou `tipo_evento_secundario` (ADR-0024) nunca preencheu dado
  retroativo, e o reseed automático só roda com a tabela vazia — em
  produção a tabela já existia desde o ADR-0014/0019, então os 15 códigos
  `evento_secundario` ficaram com `tipo_evento_secundario = NULL`
  permanentemente (o próprio ADR-0024 já registrava isso como ação manual
  pendente, nunca executada).
- `src/workforce_api/repositorio_catalogo_postgres.py`:
  `RepositorioCatalogoPostgres._reparar_tipo_evento_secundario()`, novo
  passo idempotente no `__init__` (mesmo padrão do `ALTER TABLE ... IF
  NOT EXISTS` já existente) que preenche `tipo_evento_secundario` de
  qualquer linha que ainda esteja `NULL`, sem nunca sobrescrever um valor
  já definido. Corrige produção sozinho no próximo boot do backend, sem
  exigir chamadas manuais de `POST /catalogo`.
- `interface_campo/js/catalogoMotivos.js`: `obterEventosSecundarios`
  agora repara `tipo_evento_secundario` ausente no cliente também
  (mapeamento estático local, mesma tabela do ADR-0024), para não
  depender só do backend já ter sido reiniciado com a correção acima —
  cobre também cache antigo em `localStorage` do navegador do
  colaborador.
- Confirmado por leitura de código que o "leque de opções" ao abrir
  jornada (Iniciar atividade / Iniciar atendimento de falha / Iniciar
  deslocamento-espera-apoio / Encerrar jornada) e sua reaparição
  automática após encerrar uma atividade já estavam implementados desde
  o ADR-0024/0025 — o problema reportado era este bug travando o uso do
  bloco de evento secundário, não a ausência do leque.
- `tests/test_repositorio_catalogo_postgres.py` (novo, 3 testes): mapeamento
  puro cobre exatamente os 15 códigos, EE01 mapeado como APOIO, e o reparo
  (com conexão/cursor falsos) só atualiza linhas com `tipo_evento_secundario
  IS NULL`.
- `tests/js/catalogoMotivos.test.mjs`: 2 testes novos reproduzindo o
  payload exato que o backend não migrado devolvia (`tipo_evento_secundario:
  null`) e confirmando que o reparo local nunca sobrescreve um tipo que já
  veio preenchido.

### Testes
- `python -m py_compile` no módulo alterado: OK.
- `pytest`: 252/252 (era 249).
- `node --check` em `catalogoMotivos.js`: OK.
- `node --test tests/js/*.test.mjs`: 104/104 (era 102).

### Riscos
- Depende do backend em produção (Render) efetivamente reiniciar com este
  código — histórico conhecido de auto-deploy do Render falhando
  silenciosamente (ver entrada de 2026-07-27 abaixo). Se não reiniciar
  sozinho, precisa de "Manual Deploy" no painel do Render.

## [Unreleased]

### Adicionado
- Motor de domínio do Incremento 1 (`src/workforce_core/`): entidades
  `Jornada`, `Atividade` e `Pausa`, enums de estado, exceções de domínio,
  motor de transições (`MotorJornada`) e motor de cálculo de HH
  (`calculo.py`).
- Suíte de testes unitários (`tests/test_motor_jornada.py`) cobrindo os 13
  casos obrigatórios da seção 9 do alinhamento oficial v1.2, mais 3 testes
  adicionais de regras estruturais (jornada exigida, atividade ativa
  exigida, motivo obrigatório).
- `docs/28_ADR_0001_MODELAGEM_PROVISORIA_DA_PAUSA.md`: registro da decisão
  provisória de modelar a pausa como evento próprio vinculado à atividade.
- `pyproject.toml` com configuração de `pytest` (`pythonpath = src`).
- Incremento 2 — persistência local e recuperação de estado
  (`src/workforce_storage/`): serialização de entidades para JSON
  (`serializacao.py`), repositório de jornadas em arquivo com escrita
  atômica e tratamento de corrupção (`RepositorioJornadaArquivo`).
- `MotorJornada.a_partir_de()` e `EstadoInconsistenteError` em
  `workforce_core`: reconstrói o motor a partir de uma jornada persistida,
  recalculando atividade/pausa ativas a partir dos estados (nunca de um
  campo redundante) e recusando estados logicamente impossíveis.
- `tests/test_persistencia.py`: 12 testes cobrindo round-trip, preservação
  de UUID, recuperação após fechamento abrupto com pausa/atividade em
  andamento, escrita atômica sem resíduo `.tmp`, arquivo JSON inválido não
  apagado, estrutura inválida não apagada, estado semanticamente
  inconsistente detectado, `listar_abertas` ignorando corrompidos sem
  apagá-los, e exclusão.
- `docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md`: decisão provisória
  de formato de serialização, escrita atômica e política de corrupção.
- Incremento 3 — fila offline e sincronização idempotente
  (`src/workforce_sync/`): `RegistroFila`/`StatusSincronizacao`
  (`PENDENTE`/`SINCRONIZADO`/`ERRO`/`CONFLITO`), `RepositorioFilaArquivo`
  (mesmo padrão de escrita atômica e não deleção em corrupção),
  `FilaSincronizacao` (enfileirar, listar, resumo, marcar_*), contrato
  `ClienteSincronizacao` (Protocol) com implementação falsa idempotente
  `ClienteSincronizacaoEmMemoria` para testes/dev, e `Sincronizador`
  (`sincronizar_pendentes`, isolamento de falha por item, conflito nunca
  automático).
- `tests/test_sincronizacao.py`: 11 testes cobrindo enfileiramento,
  sincronização idempotente (sem reenvio quando nada mudou, upsert sem
  duplicidade em reenvio pós-confirmação-perdida), retry automático de
  erro, conflito nunca resolvido silenciosamente (exclui do lote até
  reenfileiramento explícito), os 4 status simultâneos, limite de tamanho
  de lote, fila sobrevivendo a "reinício do app", e registro de fila
  corrompido não apagado.
- `docs/30_ADR_0003_FILA_OFFLINE_E_SINCRONIZACAO_PROVISORIA.md`: decisão
  provisória de transporte plugável, granularidade por jornada, tamanho de
  lote e política de conflito/retry.
- Incremento 4 — interface operacional simples para celular
  (`interface_campo/`): PWA estático (HTML/CSS/JS, sem framework nem
  build), motor de domínio e motor de cálculo portados para JavaScript
  espelhando `workforce_core` (`js/motorJornada.js`, `js/calculo.js`,
  `js/enums.js`, `js/erros.js`, `js/entidades.js`), armazenamento em
  IndexedDB com recuperação de estado (`js/armazenamento.js`), UI mínima
  com DOM seguro (sem `innerHTML` com conteúdo dinâmico), manifest PWA e
  service worker cache-first para uso offline.
- `tests/js/motorJornada.test.mjs`: 17 testes Node (`node --test`)
  replicando os 13 casos obrigatórios da seção 9 do alinhamento oficial no
  motor JavaScript, mais regras estruturais e recuperação de estado —
  garante paridade com o motor Python já validado.
- `docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md`: decisão provisória
  de duplicação do motor em JS, contrato de IndexedDB, fluxo de botões, e
  registro explícito de que o teste em navegador/celular real **não foi
  realizado** neste ambiente (sem chromium-cli/Playwright disponível e sem
  acesso de rede para instalar — mesma causa do erro `ENOTFOUND` relatado
  nesta sessão).
- Incremento 5 — catálogo de motivos e eventos secundários
  (`src/workforce_core/catalogo.py`): `Categoria` (taxonomia de
  `docs/07_MOTOR_EVENTOS_E_HH.md`), `ClassificacaoHH` (sempre
  `NAO_DEFINIDO` por padrão), `EntradaCatalogo`, `CatalogoMotivos`,
  `catalogo_padrao()` com motivos `*_TESTE`.
- Nova entidade `EventoSecundario` (deslocamento/espera/apoio), vinculada
  diretamente à Jornada e mutuamente exclusiva com a atividade principal
  ("apenas um evento principal ativo", regra já documentada em
  `docs/07_MOTOR_EVENTOS_E_HH.md`). `MotorJornada` ganhou
  `iniciar_evento_secundario`/`encerrar_evento_secundario`, com as mesmas
  garantias de idempotência/consistência da Pausa; `a_partir_de` agora
  também recupera o evento secundário ativo.
- `calculo.py`: `duracao_evento_secundario`, `duracao_eventos_secundarios`;
  duração de eventos secundários agora entra em `tempo_classificado_jornada`;
  `resumo_jornada` inclui `eventos_secundarios`.
- `workforce_storage/serializacao.py`: `FORMATO_VERSAO` 1 → 2, serializa
  `eventos_secundarios`; leitura de arquivos v1 (sem esse campo) continua
  funcionando via `.get("eventos_secundarios", [])`.
- `tests/test_eventos_secundarios.py`: 18 testes cobrindo início/fim dos
  três tipos, tipo/motivo obrigatórios, exclusão mútua nos dois sentidos
  (evento após atividade e atividade após evento), bloqueio de segundo
  evento simultâneo, bloqueio de encerramento de jornada com evento aberto,
  timestamp inválido, entrada no tempo classificado, recuperação de estado,
  detecção de inconsistência (evento e atividade ativos juntos), round-trip
  de persistência, e comportamento do catálogo.
- `docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md`: decisão
  registrando a taxonomia (citada de doc já existente, não inventada), a
  regra de exclusão mútua, e o que continua deliberadamente fora de escopo
  (conteúdo oficial do catálogo, classificação produtiva/improdutiva,
  paridade em JavaScript).
- Incremento 6 — atendimento de falha e catálogo RASF: `Atividade` ganhou
  campo opcional `dados_falha: Optional[DadosFalha]`
  (`nota`/`ativo`/`sintoma`/`causa`/`acao`/`observacao`);
  `MotorJornada.iniciar_atendimento_falha` e
  `MotorJornada.registrar_dados_falha` (atualização parcial); regra
  inegociável da seção 3.5 aplicada em `encerrar_atividade`: não encerra
  atendimento de falha sem os 6 campos preenchidos
  (`AtendimentoFalhaCamposObrigatoriosError`, listando o que falta).
- `workforce_storage/catalogo_rasf.py`: carregador dos catálogos reais em
  `catalogos/` (sintomas, sistemas, tipos de solicitação, impactos,
  componentes causadores, 6M níveis 1-3), preservando código/descrição/
  frequência/status ativo, com `item_por_codigo`, `item_por_valor`,
  `apenas_ativos`.
- `workforce_storage/serializacao.py`: `FORMATO_VERSAO` 2 → 3, serializa
  `dados_falha`; leitura de arquivos v1/v2 continua funcionando.
- `tests/test_atendimento_falha.py` (8 testes) e `tests/test_catalogo_rasf.py`
  (6 testes, lendo os CSVs reais do repositório — não fixtures fabricadas):
  fluxo completo, bloqueio com campos ausentes/parciais (mensagem lista os
  faltantes), preenchimento progressivo, atendimento com pausa, atividade
  comum não exige campos de falha, números do catálogo real batendo com
  `catalogos/README.md` (53 sintomas, 5 sistemas, 10 tipos de solicitação,
  4 impactos, 148 componentes causadores).
- `docs/33_ADR_0006_ATENDIMENTO_FALHA_E_CATALOGO_RASF.md`: decisão de
  reaproveitar `Atividade` em vez de criar entidade paralela, e o que fica
  fora de escopo (campos recomendados, validação cruzada com catálogo,
  governança, paridade em JavaScript).
- Incremento 7 — pulsos GPS, qualidade e sincronização em lote: nova
  entidade `PulsoGps` (`workforce_core/entities.py`, vinculada por
  `jornada_id`, não aninhada) com todos os campos de
  `docs/08_GPS_PULSOS_E_PRIVACIDADE.md`; `QualidadePulso`
  (`OK`/`PRECISAO_RUIM`/`SALTO_IMPOSSIVEL`/`VELOCIDADE_INCOMPATIVEL`/
  `NAO_AVALIADO`).
- `workforce_core/qualidade_gps.py`: `distancia_metros` (haversine),
  `velocidade_implicita_metros_segundo`, `avaliar_pulso` — nenhum limiar
  numérico com valor padrão, sempre exigido explicitamente de quem chama.
- `workforce_storage/repositorio_pulsos_gps.py`: `RepositorioPulsosGpsArquivo`,
  armazenamento local append-only em `.jsonl` (uma linha por pulso, com
  `flush`+`fsync`), com leitura resiliente a linha corrompida
  (`ler_pulsos_com_erros` reporta o número da linha sem apagar nada).
- `workforce_sync`: `ClienteSincronizacao` ganhou `enviar_lote_pulsos`
  (upsert por id de pulso, idempotente); `CursorSincronizacaoPulsos` +
  `RepositorioCursorPulsosArquivo` (cursor por jornada, mais simples que a
  fila de 4 estados usada para jornadas, já que pulsos não têm conflito);
  `SincronizadorPulsos` (`sincronizar_pendentes`, `sincronizar_tudo`).
- `tests/test_gps.py` (18 testes): avaliação de qualidade (distância
  haversine, ok, precisão ruim, salto impossível, velocidade incompatível
  reportada pelo dispositivo, precisão original preservada), round-trip de
  serialização, gravação/leitura append-only em ordem, linha corrompida
  não apaga as demais, sincronização respeitando tamanho de lote,
  `sincronizar_tudo` esvaziando a fila em vários lotes, reenvio após ack
  perdido sem duplicar, erro de rede não avança o cursor.
- `docs/34_ADR_0007_PULSOS_GPS_QUALIDADE_E_SINCRONIZACAO_LOTE.md`: decisão
  de campos/categorias citados dos docs existentes (não inventados),
  nenhum limiar numérico embutido, e lista extensa do que fica
  deliberadamente fora (captura real em navegador, obrigatoriedade,
  contingência, retenção, perfis, LGPD).
- Incremento 8 — consolidação de HH e qualidade dos dados
  (`workforce_core/consolidacao.py`): `resumo_por_categoria` (agrega
  atividade/pausa/evento secundário por `Categoria`, usando o catálogo);
  `resumo_consolidado` (primeira função capaz de agregar HH de várias
  jornadas, ex.: equipe/período); `jornadas_abertas_ha_muito_tempo` e
  `taxa_qualidade_pulsos` (sem limiares embutidos);
  `pulsos_pendentes_de_sincronizacao` (reconciliação enviados x
  recebidos).
- `tests/test_consolidacao.py` (14 testes): classificação de atividade
  comum vs. atendimento de falha, pausa sem categoria/fora do catálogo,
  itens em andamento ignorados, soma multi-jornada com reconciliação
  bruta=classificado+não classificado, jornadas encerradas ignoradas na
  consolidação, jornada aberta há muito tempo detectada/ignorada, taxa de
  qualidade de GPS (incluindo `None` quando nada avaliado), pendências de
  sincronização de pulsos.
- `docs/35_ADR_0008_CONSOLIDACAO_HH_E_QUALIDADE.md`: decisão registrando
  por que a reconciliação de soma já é garantida por construção desde o
  Incremento 1, e o que fica fora (soma por OS, HH de equipe, dashboard x
  exportação — dependem de conceitos ainda não construídos).
- Incremento 9 — dashboard ECharts (`painel/`): `dados.py` (carregamento
  de jornadas via `workforce_storage`, sem apagar arquivo corrompido;
  `montar_resumo` via `workforce_core.consolidacao`; geração de dados de
  exemplo para demonstração); `graficos.py` (gráficos de barra e pizza via
  **pyecharts**, renderizados como HTML autocontido com o JS do ECharts
  embutido localmente — sem CDN, com falha explícita se o asset local
  estiver ausente); `app.py` (entrypoint Streamlit, aviso permanente de
  piloto técnico, estado do diretório preservado via `st.session_state`).
- **Troca arquitetural**: `streamlit-echarts` (previsto em
  `Requirements.txt`) está incompatível com a versão do Streamlit
  disponível neste ambiente (exige `asset_dir` em `pyproject.toml` que o
  pacote não suporta em nenhuma versão publicada). Substituído por
  `pyecharts` + `st.components.v1.html` — continua sendo Apache ECharts,
  só que integrado de outra forma. `Requirements.txt` atualizado.
- `tests/test_painel.py` (9 testes): formatação de horas, carregamento
  com/sem erro, geração e agregação de dados de exemplo, arquivo
  corrompido reportado sem ser apagado, HTML de gráfico autocontido sem
  CDN, falha explícita quando o asset local está ausente.
- **Smoke test real**: `streamlit run painel/app.py --server.headless
  true` iniciado de fato (não apenas import), com HTTP 200 confirmado por
  `curl` em `/` e `/_stcore/health`, sem dados e com dados de exemplo
  (exercitando gráficos e tabela), sem traceback no log.
- `docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md`: decisão completa da
  troca de biblioteca, mitigação de CDN sem integrity, e o que fica fora
  (indicadores oficiais, filtros, autenticação, teste em navegador real).
- Incremento 10 — mapa operacional: `workforce_core/geo.py`
  (`simplificar_trajetoria`, `agrupar_permanencia`/`ClusterPermanencia`,
  sem nenhum limiar padrão embutido); `painel/mapa.py`
  (`construir_mapa` com Folium: pulsos brutos coloridos por qualidade,
  trajetória simplificada, clusters de permanência com popup "inferência,
  não prova", escape de HTML nos popups); `painel/pages/1_Mapa_Operacional.py`
  (segunda página do painel multipage, com `gerar_pulsos_exemplo`
  determinístico para demonstração).
- **Bug real encontrado e corrigido**: `RepositorioJornadaArquivo.listar_ids()`
  quebrava com `ValueError` se o diretório contivesse qualquer `.json`
  cujo nome não fosse um UUID (ex.: `MANIFESTO.json` na raiz do projeto).
  Corrigido para ignorar esses arquivos, mesma disciplina de resiliência
  já usada para arquivos corrompidos. Teste de regressão em
  `tests/test_persistencia.py`. Guardas de diretório vazio adicionados em
  `painel/app.py` e na página do mapa.
- `tests/test_geo.py` (8 testes) e `tests/test_mapa.py` (6 testes):
  simplificação de trajetória, agrupamento de permanência, mapa sem
  quebrar sem dados, camadas geradas corretamente, popup escapando HTML
  de campo controlado pelo usuário, cores por qualidade.
- `docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md`: decisão completa,
  incluindo o relato do bug encontrado/corrigido e o que fica fora
  (camadas dependentes de mais dados, filtros de conceitos ainda não
  modelados, restrição por perfil).
- Incremento 11 — exportações (`src/workforce_export/`):
  `MetadadosExportacao` (usuário responsável obrigatório, sufixo de
  arquivo com período+geração); `csv_exportacao.py` (jornadas, eventos
  unificados, falhas com coluna `completo`, gps + `metadados_*.json`
  companheiro); `xlsx_exportacao.py` (abas Resumo, HH por categoria, HH
  por ativo, Jornadas, Pausas, Falhas, Qualidade, Dicionário de dados —
  totais vêm exatamente de `workforce_core.consolidacao`, mesma fonte do
  painel); `geojson_exportacao.py` (pontos e trajetórias simplificadas,
  matrícula do colaborador omitida por padrão — minimização de dados
  pessoais). `painel/pages/2_Exportacoes.py`: terceira página do painel,
  exige usuário responsável antes de habilitar downloads.
- `tests/test_exportacoes.py` (15 testes): reconciliação exata de totais
  CSV/XLSX com `consolidacao`, metadados obrigatórios, marcação de
  atendimento de falha completo/incompleto, todas as abas do XLSX,
  GeoJSON com minimização de dados pessoais por padrão e coordenadas no
  formato correto.
- `docs/38_ADR_0011_EXPORTACOES_CSV_XLSX_GEOJSON.md`: decisão completa,
  incluindo por que "participantes" e "HH por OS" não são exportados
  (conceitos ainda não modelados) e a decisão de minimização de dados
  pessoais por padrão no GeoJSON.
- Incremento 12 — capacidade PCM (`workforce_core/pcm.py`):
  `capacidade_bruta`/`capacidade_efetiva` (fórmula de
  `docs/15_CAPACIDADE_PCM.md`, todos os termos como parâmetros
  obrigatórios, piso zero); `BucketCapacidade` (citado do doc);
  `agrupar_por_bucket` (mapeamento categoria→bucket sempre explícito,
  única correspondência automática é lacuna não classificada →
  `LACUNA_NAO_APONTADO`); `PremissasCenario`/`ResultadoCenario`/
  `simular_cenario` ("sempre mostrar premissas", literal do doc).
  `painel/pages/3_Capacidade_PCM.py`: quarta página do painel, simulador
  com mapeamento de exemplo rotulado "não oficial".
- `tests/test_pcm.py` (7 testes): fórmula, piso zero, agrupamento por
  bucket com e sem lacuna, premissas sempre devolvidas no resultado.
- `docs/39_ADR_0012_CAPACIDADE_PCM.md`: decisão completa — o incremento
  com mais pendências de negócio até agora; documenta por que o cálculo
  automático fica deliberadamente limitado a descontar só ausências.
- Incremento 13 (último do roadmap) — contrato de integração futura com
  o SGO (`workforce_core/integracao_sgo.py`), sem integrar com nada real:
  `ReferenciaOS` (numero+ciclo_ou_plano na identidade, nunca só o número;
  data_importacao fora da igualdade); value objects `UsuarioAutorizado`,
  `Coordenacao`, `Especialidade`, `Patio`, `Ativo`, `OsProgramada`
  (chaves já documentadas em `docs/16`, nenhuma inventada);
  `ContratoSGO` (`Protocol` somente leitura, `@runtime_checkable`);
  `ContratoSGOEmMemoria` (implementação falsa, mesmo papel de
  `ClienteSincronizacaoEmMemoria`). `DadosFalha.os_referencia` (campo
  recomendado, opcional) usa `ReferenciaOS` desde o início.
  `FORMATO_VERSAO` 3 → 4, retrocompatível.
- `tests/test_integracao_sgo.py` (10 testes): identidade correta de
  `ReferenciaOS`, uso como chave de dict, atendimento de falha com OS
  referenciada opcionalmente, round-trip com/sem `os_referencia`,
  conformidade do contrato falso com o Protocol.
- `docs/40_ADR_0013_CONTRATO_INTEGRACAO_FUTURA_SGO.md`: decisão final e
  fechamento do roadmap de 13 incrementos — resume o que foi entregue e o
  que continua exigindo decisão humana antes de uso real.

### Alterado
- N/A (primeira entrega de código do projeto).

### Corrigido
- `MotorJornada.iniciar_pausa`: a checagem de "já existe pausa ativa"
  estava depois da checagem de "atividade ativa", e como a atividade fica
  `PAUSADA` durante uma pausa em curso, uma segunda tentativa de pausa
  levantava `PausaExigeAtividadeAtivaError` em vez de `PausaJaAtivaError`.
  Ordem invertida para checar `_pausa_ativa` primeiro.
- **Bug real encontrado no primeiro teste manual em navegador**
  (`interface_campo/js/app.js`): o botão "Iniciar jornada" quebrava com
  "Falha inesperada ao registrar o evento" no primeiro uso do app (antes
  de existir qualquer jornada no IndexedDB), porque tentava chamar
  `motor.iniciarJornada(...)` com `motor` ainda `null`. Corrigido com
  `prepararMotorComMatricula()`, chamada no clique do botão para garantir
  que o motor existe antes de iniciar a jornada (unifica o caminho do
  primeiro uso com o de "Iniciar nova jornada", que antes usava a função
  `reiniciar()`, agora removida). `CACHE_VERSAO` do Service Worker
  incrementada (`v1` → `v2`) para que a correção realmente chegue ao
  navegador — o Service Worker cacheia `app.js` e não busca a versão nova
  sozinho sem essa mudança de versão. Detalhes em
  `docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md`.

### Alterado
- A pedido do responsável pelo produto após o primeiro teste manual, o
  seletor de motivo de pausa da interface de campo
  (`interface_campo/js/app.js`) ganhou opções de exemplo — **Refeição,
  DDS, Reunião, Treinamento** (categorias já citadas em
  `docs/07_MOTOR_EVENTOS_E_HH.md`) além de `PAUSA_TESTE`. Mesmos códigos
  adicionados ao `catalogo_padrao()` (`workforce_core/catalogo.py`), com
  `classificacao_hh=NAO_DEFINIDO` (continuam sendo exemplo, não o
  catálogo oficial). "Aguardando material/liberação" propositalmente
  **não** entraram no seletor de pausa — correspondem à categoria de
  Espera (evento secundário), não a uma pausa; ver
  `docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md`, seção
  "Atualização". `CACHE_VERSAO` do Service Worker incrementada de novo
  (`v2` → `v3`).
- **Catálogo real do Relatório de Atividades Diárias de Manutenção**
  (`docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md`): o
  responsável pelo produto forneceu o formulário em papel que a equipe da
  MRS Logística usa hoje (Relatório 1, códigos `EE01`–`EE24`),
  substituindo os motivos de exemplo genéricos. Adicionado
  `catalogo_relatorio_1_manutencao()` e
  `codigos_relatorio_1_por_tipo_registro()` (`workforce_core/catalogo.py`)
  com os 23 códigos catalogáveis (`EE24` "Horas não apontadas" não vira
  entrada — já corresponde ao `tempo_nao_classificado` calculado
  automaticamente), mapeados código a código para `atividade`
  (`EE17`/`EE22`), `pausa` (`EE02`, `EE07`, `EE11`, `EE21`, `EE23`) ou
  `evento_secundario` (os outros 16). Nova categoria `DESLOCAMENTO_A_PE`.
  O seletor de pausa da interface de campo agora usa os 5 códigos reais de
  pausa em vez dos exemplos genéricos; os 16 códigos de evento secundário
  ficam catalogados mas sem tela própria ainda (próximo passo natural,
  não implementado nesta sessão). `CACHE_VERSAO` incrementada de novo
  (`v3` → `v4`). `classificacao_hh` de todos os 23 códigos permanece
  `NAO_DEFINIDO` — o formulário define o código, não a classificação de
  HH.
- **Buckets reais de perda de capacidade PCM**
  (`docs/42_ADR_0015_BUCKETS_REAIS_PCM.md`): o responsável pelo produto
  forneceu a planilha real de cálculo de PCM da MRS Logística com os 4
  buckets efetivamente usados. `BucketCapacidade`
  (`workforce_core/pcm.py`) substituído pelos 4 buckets reais —
  `HORAS_AUSENTES`, `HORAS_PRESENTES_IMPRODUTIVAS`,
  `HORAS_PRESENTES_NAO_APONTADAS`,
  `HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS` — substituindo os buckets
  genéricos do Incremento 12 (mudança que quebra compatibilidade, sem
  problema pois nunca foram usados com dado real). Nova
  `mapeamento_categoria_bucket_relatorio_1_manutencao()` com o de-para
  completo dos 20 códigos do Relatório 1 (ADR-0014) para os buckets reais
  — `EE17`/`EE22` (manutenção em equipamentos/não planejada)
  deliberadamente fora de qualquer bucket por padrão, porque só contam
  como perda quando não vinculadas a uma OS planejada válida, checagem
  que o sistema ainda não faz. Nova
  `simular_cenario_relatorio_1_manutencao()`: deriva automaticamente
  `pausas_nao_computaveis`/`improdutividade`/`atividades_nao_aplicaveis`
  do apontamento real via os buckets — só "ausências externas" (férias/
  motivos legais, sem fonte no sistema) continua manual.
  `painel/pages/3_Capacidade_PCM.py` reescrita para usar o catálogo e o
  mapeamento reais em vez dos exemplos genéricos.

### Testes
- `python -m py_compile src/workforce_core/*.py src/workforce_storage/*.py src/workforce_sync/*.py tests/*.py`: OK.
- `python -m pytest`: 43 passed.
- `node --check` em todos os arquivos de `interface_campo/js/` e
  `interface_campo/service-worker.js`: sintaxe válida.
- `node --test tests/js/motorJornada.test.mjs`: 17 passed.
- Servidor estático real (`python -m http.server`) servindo
  `interface_campo/`: todos os arquivos (HTML, CSS, JS, manifest, service
  worker, ícone) respondem HTTP 200 com `Content-Type` correto.
- **Não realizado**: clique real em navegador/celular (sem
  chromium-cli/Playwright disponíveis neste ambiente). Ver
  ADR-0004, seção "Validação NÃO realizada".
- `python -m pytest`: 60 passed (após Incremento 5); 74 passed (após
  Incremento 6, incluindo leitura dos CSVs reais de `catalogos/`); 88
  passed (após Incremento 7); 102 passed (após Incremento 8); 111 passed
  (após Incremento 9); 126 passed (após Incremento 10); 141 passed (após
  Incremento 11); 148 passed (após Incremento 12); 158 passed (após
  Incremento 13 — roadmap completo); 159 passed (após motivos de pausa de
  exemplo); 167 passed (após catálogo real do Relatório de Atividades);
  172 passed (após buckets reais de PCM). `node --test
  tests/js/motorJornada.test.mjs`: 17 passed (inalterado).
- Caso mínimo obrigatório (seção 7.3) validado com os valores exatos da
  seção 7.4: jornada bruta 4h10, atividade bruta 3h50, pausa 0h20,
  atividade líquida 3h30, tempo não classificado 0h20.

### Riscos
- Toda pausa é 100% descontável neste incremento (decisão provisória, ver
  ADR-0001); catálogo oficial e classificação produtiva/improdutiva ficam
  para o Incremento 5.
- Formato de persistência local (arquivo JSON por jornada) é provisório
  (ADR-0002); o contrato de campos precisará ser replicado em JavaScript
  quando o Incremento 4 implementar IndexedDB no PWA.
- Política de retenção do arquivo local após confirmação de sincronização
  ainda não existe (o arquivo em `workforce_storage` não é removido nem
  marcado após `marcar_sincronizado`).
- `ClienteSincronizacaoEmMemoria` é exclusivamente para desenvolvimento e
  testes; não existe ainda um cliente HTTP real nem uma API para receber os
  dados (FastAPI/Postgres não fazem parte de nenhum incremento numerado até
  aqui).
- Regra de resolução de conflito é intencionalmente inexistente: o sistema
  detecta e sinaliza (`CONFLITO`), mas não decide automaticamente qual
  versão prevalece.
- Motor de domínio duplicado em Python e JavaScript (ADR-0004): qualquer
  mudança de regra de negócio precisa ser replicada manualmente nos dois
  lados até existir uma única fonte de verdade.
- Interface de campo (`interface_campo/`) nunca foi aberta em um navegador
  real nem testada em celular físico neste ambiente — validação manual
  pendente antes de qualquer piloto com colaboradores (ADR-0004).
- `interface_campo/` ainda não está conectada à fila de sincronização
  (`workforce_sync`, Incremento 3): não há API real para ela conversar.
- Catálogo de motivos (Incremento 5) não tem nenhum conteúdo oficial:
  todas as entradas têm `classificacao_hh = NAO_DEFINIDO` e são apenas
  placeholders de teste (`*_TESTE`). `EventoSecundario` (deslocamento,
  espera, apoio) **foi portado para `interface_campo/js/` no ADR-0024**
  (2026-07-28) — este risco não se aplica mais, ver seção mais recente
  no fim deste arquivo.
- Catálogo RASF (`catalogos/`) declaradamente **não é catálogo oficial de
  produção** (ver `catalogos/README.md`) — precisa de governança e
  validação da Eletroeletrônica antes de uso real.
- Nenhuma validação cruzada entre `DadosFalha` (sintoma/causa/ação) e o
  catálogo RASF carregado: o motor aceita qualquer string, igual já
  acontecia com motivo de pausa/evento secundário.
- Campos recomendados de atendimento de falha (sistema, componente
  causador, tipo/impacto, OS relacionada, pendência, evidência, equipe)
  ainda não implementados — só os 7 campos mínimos obrigatórios.
- Atendimento de falha (Incremento 6) não foi portado para
  `interface_campo/js/` — mesma situação de `EventoSecundario`.
- Painel (`painel/`) nunca foi aberto em navegador real — smoke test
  confirma que o servidor Python não quebra, não que os gráficos
  renderizam visualmente corretos (ADR-0009).
- Nenhum indicador do painel foi validado como oficial: filtros, metas,
  perfis de acesso e autenticação não existem.
- Mapa operacional (`painel/pages/1_Mapa_Operacional.py`) também nunca
  foi aberto em navegador real (ADR-0010). Camadas de pinos de
  evento/falha, ativos/pátios e heatmap de HH não implementadas. Filtros
  de coordenação/equipe/pátio/impacto não existem porque esses conceitos
  não estão modelados no sistema. Pulsos brutos não têm restrição por
  perfil (sem autenticação).
- Exportações (`painel/pages/2_Exportacoes.py`) nunca abertas em
  navegador real (ADR-0011). Layout de colunas não é oficial. Sem
  auditoria centralizada de exportações nem controle de acesso — qualquer
  pessoa com acesso ao painel exporta qualquer dado. "Matrícula fora do
  GeoJSON por padrão" é decisão técnica defensiva, não política de LGPD
  validada.
- Capacidade PCM (`painel/pages/3_Capacidade_PCM.py`) nunca aberta em
  navegador real (ADR-0012). Sem fonte real de escala/ausências/férias —
  tudo digitado manualmente. Mapeamento categoria→bucket é só um exemplo.
  Cálculo automático desconta apenas ausências; pausas não computáveis,
  improdutividade e atividades não aplicáveis exigem decisão manual de
  quem lê os buckets observados, porque a classificação
  produtiva/improdutiva do catálogo continua indefinida (ADR-0005).
- `ContratoSGO` (Incremento 13) não tem nenhuma implementação real — só
  `ContratoSGOEmMemoria`, para testes. Não há autenticação entre
  aplicações, SSO, nem definição de responsabilidade sobre dados mestres.
  A "segunda integração" (devolução de HH real ao SGO) não existe.
- Captura real de GPS (`navigator.geolocation`) não foi implementada em
  `interface_campo/js/` — não há como testar em dispositivo real neste
  ambiente. Nenhum limiar de qualidade (precisão mínima, velocidade máxima
  plausível) está definido em lugar nenhum do código — são parâmetros
  obrigatórios sem valor padrão. GPS não é obrigatório para nenhuma
  transição de jornada/atividade. Retenção, perfis autorizados e validação
  de LGPD continuam pendentes antes de qualquer uso real (ADR-0007).
- Catálogo real do Relatório de Atividades (ADR-0014): mapeamento
  código→tipo de registro (pausa/evento secundário/atividade) é
  interpretação de quem implementou, não confirmada linha a linha com o
  responsável pelo produto. Classificação produtiva/improdutiva de todos
  os 23 códigos foi validada no ADR-0023 (2026-07-27). Os 15 códigos de
  deslocamento/espera/apoio **ganharam tela na interface de campo no
  ADR-0024** (2026-07-28).
- Buckets reais de PCM (ADR-0015): os percentuais da planilha fornecida
  são de um período específico, não uma meta validada. `EE17`/`EE22`
  ficam fora de qualquer bucket de perda por padrão porque o sistema não
  verifica se estão vinculadas a uma OS planejada válida — uma
  simplificação, não a distinção rentável/não-rentável real. `FÉRIAS` e
  `MOTIVOS LEGAIS` continuam sem fonte no sistema, exigindo entrada manual
  no simulador (`painel/pages/3_Capacidade_PCM.py`).

## [2026-07-28] Evento Secundário na interface de campo (ADR-0024)

Este changelog não acompanhou as sessões entre o Incremento 13 e esta
data (ADR-0016 a ADR-0023 — simulador de tempo, sincronização real,
filtros de dashboard, catálogo dinâmico, reorganização do painel,
atendimento de falha e sua evolução com GPS/foto/transferência,
reclassificação do catálogo). Esta entrada documenta apenas o incremento
atual; ver `docs/51_ADR_0024_EVENTO_SECUNDARIO_INTERFACE_DE_CAMPO.md`
para a decisão completa e os ADRs 0016-0023 para o que ficou de fora
deste arquivo.

### Adicionado
- `EntradaCatalogo.tipo_evento_secundario` (`src/workforce_core/catalogo.py`):
  mapeia cada um dos 15 códigos `evento_secundario` do Relatório 1 para
  `TipoEventoSecundario.DESLOCAMENTO/ESPERA/APOIO` (mapeamento do
  ADR-0014, exceto `EE01` classificado como `APOIO` nesta sessão).
  Persistido no catálogo dinâmico (`repositorio_catalogo_postgres.py`,
  nova coluna via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` — a tabela já
  existe em produção).
- `EventoSecundario` portado para `interface_campo/js/` com paridade
  completa do motor Python (ADR-0005): `enums.js`, `entidades.js`,
  `erros.js` (7 exceções), `motorJornada.js`
  (`iniciarEventoSecundario`/`encerrarEventoSecundario`, exclusão mútua
  com Atividade nos dois sentidos, recuperação de estado), `calculo.js`
  (duração entra no tempo classificado da jornada).
- `catalogoMotivos.js`: nova `obterEventosSecundarios()` (mesmo
  cache/fallback offline de `obterMotivosPausa()`).
- `app.js`: nova tela "Iniciar deslocamento/espera/apoio" / "Encerrar
  evento", mutuamente exclusiva por construção com as telas de
  atividade/pausa.
- Testes novos: `tests/test_catalogo_relatorio_1.py`,
  `tests/test_serializacao_catalogo.py`,
  `tests/js/motorJornada.test.mjs` (13 casos espelhando
  `tests/test_eventos_secundarios.py`), `tests/js/catalogoMotivos.test.mjs`,
  `tests/js/sincronizacao.test.mjs`.

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 230/230 (era 226).
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js`: 89/89 (era 72).

### Riscos
- Teste manual em navegador/celular real da nova tela não realizado
  (mesma limitação de sempre).
- Migração da coluna `tipo_evento_secundario` e reseed do catálogo em
  produção (Render) ainda não executados — ação manual pendente.
- Associação de OS a EE17/EE23 (decisões já tomadas no ADR-0023) continua
  não desenhada/construída — próximo incremento.

## [2026-07-28] Associação de OS a EE17/EE23 (ADR-0025)

Ver `docs/52_ADR_0025_ORDEM_DE_SERVICO_EE17_EE23.md` para a decisão
completa.

### Adicionado
- `OrdemServico` (`src/workforce_core/entities.py`): numero (texto
  livre), soft-delete (`excluida`, nunca remove da lista — "exclusão
  parcial de OS não concluídas" do ADR-0023). `Atividade` ganha
  `ordens_servico` e `resultado` (`ResultadoAtividade.CONCLUIDA`/
  `NAO_CONCLUIDA`, novo enum).
- `MotorJornada.adicionar_ordem_servico`/`excluir_ordem_servico`/
  `encerrar_atividade_nao_concluida` (Python e JS, paridade completa).
  `consolidacao._categoria_atividade` passa a produzir EE23 quando
  `resultado == NAO_CONCLUIDA` (antes, EE17 era sempre inferido por
  omissão).
- `app.js`: bloco de OS (lista + adicionar + excluir) na tela de
  atividade comum; dois botões de encerramento ("Concluir atividade" /
  "Atividade não concluída") no lugar do único anterior. Atendimento de
  falha não muda.
- `FORMATO_VERSAO` 4 → 5 (`workforce_storage/serializacao.py`),
  retrocompatível.
- `tests/test_ordem_servico.py` (19 casos), extensões em
  `tests/js/motorJornada.test.mjs` e `tests/js/sincronizacao.test.mjs`.

### Testes
- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest`: 249/249 (era 230).
- `node --check` em todos os arquivos de `interface_campo/js/`: OK.
- `node --test tests/js`: 102/102 (era 89).

### Riscos
- Teste manual em navegador/celular real não realizado.
- Exportações (CSV/XLSX/GeoJSON) ainda não mostram OS — fora de escopo
  deste incremento, próximo passo natural se for pedido.
- Nenhuma migração de produção necessária aqui (diferente do ADR-0024):
  `POST /jornadas` já aceita o payload novo sem mudança de schema.
