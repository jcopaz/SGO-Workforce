# ADR-0065 | Modo Online/Offline de apontamento no SGO, retorno ao Workforce e fim do número de OS digitado (EE17)

## Contexto

Depois do login integrado (ADR-0062) e do teste real do fluxo em
2026-08-11 (login do painel corrigido para o ambiente dev do SGO, ver
`docs/84_LICOES_OPERACIONAIS_E_INCIDENTES.md`), o responsável do produto
testou o EE17 na prática e trouxe três problemas reais, discutidos e
decididos na mesma sessão:

1. **O SGO ainda pedia matrícula/senha ao abrir via EE17.** Hipótese mais
   provável: o TTL do `sid` (5 minutos, decisão de segurança da ADR-0062)
   expira entre o login no início da jornada e o momento em que o
   colaborador de fato chega numa Atividade, soma-se ao cold start do
   Render gratuito (~50s). Não corrigido nesta rodada (é o TTL de
   segurança, não um bug) - registrado como contexto que motivou o resto
   desta ADR: garantir acesso ao SGO **antes** de precisar dele, não só
   confiar no SSO no momento do clique.
2. **Separação de responsabilidade**: "O SGO é para ele apontar a
   execução de Ordens de Serviço, o Workforce é para apontar a
   produtividade em HH" - decisão explícita do responsável do produto.
   Consequência direta: o formulário manual de "Número da OS" do
   Workforce (ADR-0025) não faz mais sentido como fonte primária - a
   ideia original de usá-lo como fallback também foi descartada depois de
   uma segunda ponderação ("imagina digitar manualmente OS por OS" num
   turno com 50 OS - não escalava).
3. **Acesso ao SGO precisa ser garantido, não best-effort.** Se o
   colaborador não tem conexão, não conseguiu logar no SGO, ou não gerou
   o pacote PWA offline antecipadamente, ele não deveria chegar numa
   Atividade sem ter como apontar a OS. Proposta do próprio responsável do
   produto: perguntar **antes** de "Iniciar jornada" se o apontamento vai
   ser Online ou Offline, e no caso Offline, tornar obrigatória a geração
   do pacote PWA do SGO (mecanismo que já existe: `/publicar_pacote` +
   `/pacote/{id}`, tela "Publicar Rota PWA" dentro de
   `_render_apontamento`/`bloco_roteirizacao_interativo` no `app.py` do
   SGO) antes de liberar o resto da jornada.

Também ficou definido, depois de checar o código real da tabela `baixas`
do SGO: os campos `data_inicio`/`hora_inicio`/`data_fim`/`hora_fim` de lá
são **digitados manualmente** pelo técnico no formulário do SGO
(`app.py`, campos `iniHHMM`/`fimHHMM`) - nunca timestamps de evento reais.
Por isso o HH produtivo do Workforce **nunca** deve derivar desses campos
(regra de ouro 2/3) - e, por decisão do responsável do produto ("a
agilidade que é de lançar as evidências não destoa do tempo de
produtividade intencional"), o tempo gasto apontando no SGO **conta**
como parte do tempo produtivo da Atividade, sem exigir pausa - o relógio
do Workforce nunca soube (nem precisa saber) que o colaborador saiu da
aba.

## Decisão

### 1. Pergunta obrigatória Online/Offline antes de "Iniciar jornada"

`interface_campo/index.html` ganhou um `<fieldset>` com duas opções
(`modoSgoOnline`/`modoSgoOffline`), entre o campo "Senha do SGO" e o
status da tela. O clique em "Iniciar jornada" (`app.js`) agora:

- Bloqueia com aviso se nenhum modo foi escolhido.
- Modo **Online**: comportamento igual ao já existente (senha do SGO
  opcional, `tentarValidarLoginSgo` best-effort em paralelo, nunca
  bloqueia a jornada) - preserva offline-first.
- Modo **Offline**: exige o campo novo "Link da Rota PWA do SGO"
  preenchido - bloqueia "Iniciar jornada" com aviso até o colaborador
  colar o link. O bloco `#blocoOfflineSgo` (oculto por padrão, mostrado
  via `change` nos radios) traz a instrução ("abra o SGO agora, com
  internet, publique a Rota PWA, abra 1x") e um link direto pra
  `URL_APP_SGO` (sem `?sid=` - o colaborador ainda não tem `sessaoSgo`
  neste momento, login pra gerar o pacote é feito manualmente lá).

Os dois campos ficam travados (`travarCamposModoSgo`) assim que a jornada
está aberta - trocar de modo no meio do turno não faz sentido (o pacote
offline já teria sido gerado com base na escolha inicial).

### 2. Modelo de dados: `modoApontamentoSgo`/`pacoteOfflineUrlSgo` na Jornada

Dois campos novos em `entidades.js::novaJornada` (propagados por
`MotorJornada`), persistidos como qualquer outro campo da Jornada (mesmo
IndexedDB, sem migração de versão - `structured clone` não exige schema).
**Deliberadamente não entram em `sincronizacao.js::paraPayloadSincronizacao`**
- são só a referência de qual link abrir no EE17, nunca alimentam o
cálculo de HH nem o backend (`workforce_api`). Jornadas recuperadas de
antes desta versão (`modoApontamentoSgo` ausente) caem num fallback
defensivo: tenta a sessão online se existir, senão mostra um link puro
pro SGO sem SSO.

### 3. Fim do número de OS digitado no Workforce (EE17)

`criarBlocoOrdensServico` (`app.js`) não tem mais o campo "Número da OS" +
botão "Adicionar OS". Em vez disso, mostra **um botão**, decidido pelo
`modoApontamentoSgo` da jornada:

- **Online**: abre `URL_APP_SGO/?sid=...` (SSO existente, ADR-0062),
  igual a antes.
- **Offline**: abre `motor.jornada.pacoteOfflineUrlSgo` diretamente -
  como já foi aberto 1x online antes de "Iniciar jornada" (passo 1), o
  navegador já cacheou o pacote via service worker e funciona sem rede.

A lista de OS já registradas (`atividade.ordensServico`) continua sendo
exibida/excluível por compatibilidade com jornadas antigas, mas nada novo
entra ali a partir de agora - o registro de execução de OS passa a viver
inteiramente no SGO.

### 4. Botão "Voltar ao Workforce" na tela de apontamento do SGO

`app.py` (staged em `Documents/Integração SGOWorkforce/`, nunca editado
direto no Gestão_OS) ganhou um `st.link_button("↩️ Voltar ao Workforce", ...)`
no topo de `_render_apontamento`, apontando para
`st.secrets.get("URL_APP_WORKFORCE", "https://sgoworkforce.mrslogistica.workers.dev")`.
Link estático, sem nenhum estado compartilhado entre os dois apps -
"voltar" continua sendo só trocar de aba, mas agora com um botão visível
lembrando o caminho de volta, em vez de depender do colaborador lembrar
sozinho.

### 4.1. Correção no mesmo dia: o link de volta também precisa estar no pacote offline

Achado testando ao vivo, no ambiente dev, pelo responsável do produto: o
botão do item 4 só existe na tela **online** do SGO (`_render_apontamento`).
O pacote PWA offline (`gerar_html_offline`) é um artefato HTML
autocontido **separado**, gerado à parte - não herda nada da tela online,
então continuava sem nenhum caminho de volta pro Workforce. Corrigido no
mesmo `app.py` staged: mesmo link (`URL_APP_WORKFORCE`) adicionado também
na `topbar` do HTML gerado por `gerar_html_offline`, ao lado do badge
"📡 Offline" - funciona mesmo sem rede porque aponta pro próprio PWA do
Workforce, que já está cacheado no aparelho (mesmo mecanismo de
service worker do `interface_campo`).

### 5. HH produtivo inclui o tempo no SGO, sem exigir pausa (decisão de negócio, sem código)

Confirmado com o responsável do produto: não há nenhuma trava/aviso pra
sugerir pausa antes de abrir o SGO. O relógio da Atividade no Workforce
segue contando entre o EE17 e o próximo evento que o colaborador registrar
lá - inclui o tempo gasto apontando/anexando evidência no SGO, por
decisão consciente (ver Contexto).

### 6. Fluxo em telas (Login → Pergunta → App) com logo animado, no mesmo dia

Pedido do responsável do produto, ainda em 2026-08-11: a tela inicial
tinha matrícula, senha, a pergunta Online/Offline e o simulador de tempo
todos juntos, numa rolagem só - "cara de formulário de debug, não de
app". Reestruturado em telas exclusivas (nunca duas visíveis ao mesmo
tempo, controladas por `etapaPreJornada` em `app.js`):

1. **Login** (`#etapaLogin`) - logo animado do Workforce, matrícula, senha
   do SGO, botão "Continuar".
2. **Pergunta** (`#etapaPergunta`) - a escolha Online/Offline (item 1
   desta ADR), com botão "Voltar" pra etapa 1.
3. **App** - a tela de jornada/atividade já existente, sem mudança de
   comportamento.

Logo: existiam dois arquivos prontos no repositório
(`Logo - SGO Workforce 1x1.mp4`, 2,87 MB, e o mesmo conteúdo já
convertido pra GIF, 17,4 MB - GIF não tem compressão inter-quadro de
verdade, herda o problema de qualquer conversão nova). Decisão: usar o
MP4 direto via `<video autoplay loop muted playsinline>` em vez de
qualquer GIF - decodificação por hardware (GPU), 6x mais leve que a
versão GIF, alinhado com a filosofia offline-first/dados móveis do
projeto (regra de ouro 7). Arquivo copiado pra
`interface_campo/assets/logo-workforce.mp4`.

O vídeo (2,8 MB) é cacheado no service worker **fora** do `cache.addAll`
do app shell - `cache.addAll` é tudo-ou-nada, e um arquivo desse tamanho
falhando por rede instável não pode derrubar o cache do resto do app
(crítico pro offline-first). Cacheado à parte, best-effort: se falhar, a
tela de login só perde a animação até a próxima visita online, nada mais
quebra. `CACHE_VERSAO` v27 → v28.

### 6.1. Logo definitivo gerado (Nano Banana), cartões Online/Offline e ícone do painel (mesmo dia)

Logo definitivo (`logo_SGO.mp4`, 2,47 MB, mesmo formato/duração do
anterior) gerado pelo responsável do produto via Gemini Nano Banana, a
partir de um prompt desenhado nesta sessão conectando a identidade visual
da MRS Logística (azul-marinho + amarelo, linguagem de triângulo/seta
apontando pra frente, sem reproduzir o wordmark "M R S" literalmente) com
os dois domínios do produto (relógio = tempo/HH do Workforce, seta =
execução de OS do SGO). Substituiu `logo-workforce.mp4` (mesmo caminho,
conteúdo trocado - `CACHE_VERSAO` v28 → v29, senão quem já visitou o app
ficaria com o vídeo antigo em cache).

**Cartões Online/Offline** (`#modoSgoFieldset`): trocados de radio button
simples para cartões clicáveis (`.opcao-cartao`) - alvo de toque maior,
realce visual (borda azul + fundo claro) no cartão selecionado via classe
`.selecionada`, alternada por JS a cada evento `change` dos radios
(`configurarModoSgo`, `app.js`). O `<input>` real continua no DOM, só
visualmente reduzido (nunca `display:none`) - mantém acessível por
teclado/leitor de tela através do `<label for="...">`.

**Ícone da aba do painel Streamlit** (`page_icon`, nunca configurado
antes - painel rodava com o ícone genérico do Streamlit): **limitação
técnica registrada aqui** - `page_icon` do Streamlit e `<link rel="icon">`
exigem imagem estática (PNG/ICO/SVG), nunca vídeo, e este ambiente não
tem `ffmpeg`/biblioteca de vídeo instalada pra extrair um frame do
`logo_SGO.mp4`. Solução provisória: reproduzido programaticamente (Pillow,
`ImageDraw`) o mesmo desenho do ícone de relógio já existente
(`interface_campo/icons/icone.svg`) em `painel/assets/icone_workforce.png`,
usado como `page_icon` novo (`painel/app.py`). **Pendente**: trocar esse
PNG por um frame real do `logo_SGO.mp4` assim que o responsável do
produto exportar uma imagem estática dele (print/frame do vídeo) -
`interface_campo/icons/icone.svg` (favicon/PWA da interface de campo)
segue com o mesmo desenho de relógio por ora, mesma pendência.

### 6.2. Logo definitivo na sidebar do painel + favicon fechado com frame real (mesmo dia)

`logo_SGO.mp4` convertido pra GIF pelo responsável do produto (única
forma de manter animação **acima do menu de navegação** no `st.logo` -
`st.navigation` sempre ancora qualquer outro componente abaixo do menu,
já testado e documentado em `painel/app.py`; `st.logo` só anima GIF, não
vídeo). Resultado: 6,78 MB (100 frames, 480x480) contra os 17,4 MB do GIF
anterior - mesmo caminho de arquivo
(`painel/assets/logo_sgo_workforce.gif`), zero mudança de código.

Isso também resolveu a pendência do item 6.1: extraído um frame do meio
da animação (`Pillow`, `Image.seek`) mostrando o selo completo (bordas
arredondadas fechando nos quatro cantos, triângulos MRS, texto "SGO
Workforce" dentro do mesmo selo - não é um ícone separável do texto, o
lockup é uma peça só) e usado pra substituir o `icone_workforce.png`
provisório (`page_icon` do painel). Ressalva: como o texto faz parte do
mesmo selo, num favicon reduzido a 16-32px o texto vira textura
ilegível - o formato/cor do selo continua reconhecível, mas não dá pra
ler "SGO Workforce" nesse tamanho. `interface_campo/icons/icone.svg`
(favicon/PWA da interface de campo) segue com o desenho de relógio
antigo - não trocado nesta rodada por afetar o ícone instalado na tela
inicial de quem já tem o PWA instalado, mudança mais visível/persistente
que a aba do painel.

### 6.3. Favicon/ícone PWA da interface de campo trocado + fluxo em telas simplificado (mesmo dia)

Pedido explícito de trocar também o ícone da interface de campo (pendência
do item 6.2). Gerados `icons/icone-192.png` e `icons/icone-512.png` (mesmo
frame/recorte do favicon do painel, quadrado, LANCZOS) a partir de
`logo_SGO.gif` - substituem `icons/icone.svg` (removido, sem mais
referência em `manifest.webmanifest`/`index.html`/`service-worker.js`).
`CACHE_VERSAO` v29 → v30.

**Cards de aviso estáticos removidos** das Etapas 1 e 2 (o parágrafo longo
de GPS obrigatório no Login, e o parágrafo dos 23 códigos do Relatório na
Pergunta) - pedido do responsável do produto pra deixar as telas mais
limpas, sem texto explicativo que não muda com o estado. O bloco de
instrução do modo Offline foi mantido (conteúdo necessário pra operar),
mas trocado de parágrafo único pra uma lista curta de 3 passos com ícone
(`.lista-passos`), mais rápida de escanear.

**"Só avança quando colar o link"**: o botão "Iniciar jornada" agora fica
genuinamente desabilitado (`disabled`, com estilo próprio em CSS) até a
escolha estar completa - nenhum modo selecionado, ou modo Offline sem
link ainda preenchido (`atualizarEstadoBotaoIniciar`, recalculada a cada
mudança de modo e a cada tecla/colagem no campo do link). Substitui o
comportamento anterior (clicável, com aviso só depois do clique) por
feedback visual imediato.

### 6.4. Rótulos da Etapa 1 (Login) alinhados com o login real do SGO (mesmo dia)

Pedido do responsável do produto, revisando o resultado ao vivo: a Etapa 1
deveria parecer o mesmo login do SGO, já que valida contra a mesma base
(`/auth/validar`). Conferido o formulário real do SGO
(`app.py`, região 2.3 "Etapa 1 — Login Padrão"): `st.text_input("Matrícula / Usuário")`
+ `st.text_input("Senha")`. Rótulos da interface de campo alinhados
exatamente - "Matricula" → "Matrícula / Usuário", "Senha do SGO
(opcional)" → "Senha" (sem qualificação nem texto de ajuda específico do
SGO). Comportamento não mudou: senha continua opcional de verdade
(offline-first preservado, "Continuar" só exige a matrícula) - só o texto
ficou mais direto. `CACHE_VERSAO` v30 → v31.

## Consequências e riscos aceitos

- **TTL de 5 minutos do `sid` continua sem solução própria** - o modo
  Offline é o caminho de contorno pra quem sabe que vai demorar, mas o
  modo Online ainda pode expirar entre o login e o clique em EE17. Não
  endereçado nesta rodada (aumentar o TTL reabriria a discussão de
  segurança da ADR-0062).
- **Confirmação do link do pacote offline é manual (1 clique por turno)** -
  tecnicamente não dá pra automatizar: cada publicação gera um `id` novo
  em `/pacote/{id}` e o cache do service worker é do domínio do SGO, fora
  do alcance do Workforce.
- **Pacote PWA é um recorte por raio/GPS no momento da geração** - OS fora
  do raio escolhido na hora de publicar não entram no pacote offline;
  ainda depende do colaborador escolher um raio adequado.
- **Nenhuma mudança na tabela `baixas`/api.py além do botão de link** -
  decisão consciente de não construir consulta de status de OS
  (`GET /baixas/...`) nesta rodada, depois de descartada a ideia de puxar
  número/status de OS de volta pro Workforce (contrariaria a separação de
  responsabilidade decidida no Contexto).
- **Nada testado em celular real** - mesma ressalva de sempre (sandbox sem
  Chromium/Playwright). Em especial: comportamento do link "Abrir SGO
  para gerar a Rota PWA" e do botão "Voltar ao Workforce" quando o
  Workforce está instalado como PWA (pode abrir o navegador do sistema em
  vez de uma aba, mesma ressalva já registrada na ADR-0062).

## Validação realizada

- `node --check` em todos os arquivos de `interface_campo/js/` e
  `service-worker.js`: OK.
- `node --test tests/js`: 150 passed (4 testes novos em
  `motorJornada.test.mjs` cobrindo `modoApontamentoSgo`/
  `pacoteOfflineUrlSgo` - default `null`, propagação via `MotorJornada`,
  e preservação em `MotorJornada.aPartirDe`).
- `python -m py_compile` no `app.py` staged
  (`Documents/Integração SGOWorkforce/app.py`): OK.
- `CACHE_VERSAO` "v26" → "v27" (`interface_campo/service-worker.js`),
  rodapé "Versão v27" (`interface_campo/index.html`).

## Validação NÃO realizada

- Teste ponta a ponta real em celular (escolher modo, gerar/abrir o
  pacote PWA, EE17 abrindo o link certo online e offline, botão "Voltar
  ao Workforce") - depende do responsável do produto, usando o ambiente
  dev do SGO já disponível para teste.
- Promoção de `app.py`/`api.py` para o branch `dev` do Gestão_OS e
  configuração de `URL_APP_WORKFORCE` no Render/Streamlit Cloud - fica a
  critério do responsável do produto, mesmo processo já descrito na
  ADR-0062 e no `LEIA-ME.md` da pasta de staging.

## Arquivos afetados

- `interface_campo/index.html` (fluxo em telas `#etapaLogin`/
  `#etapaPergunta`, vídeo do logo, bloco de confirmação do pacote offline,
  versão v28).
- `interface_campo/js/app.js` (`obterModoSgoSelecionado`,
  `travarCamposModoSgo`, `configurarModoSgo`, `mostrarEtapaPreJornada`,
  `configurarEtapasPreJornada`, `aoClicarIniciarJornada` extraído,
  `criarBlocoOrdensServico` reescrito).
- `interface_campo/js/entidades.js` (`novaJornada` com os dois campos
  novos).
- `interface_campo/js/motorJornada.js` (`MotorJornada` propaga os campos
  novos).
- `interface_campo/css/estilo.css` (`fieldset.campo`, `.opcao-radio`,
  `.etapa-tela`, `.logo-login`, `.botao` agora funciona também como link
  de bloco).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v28, cache
  best-effort do vídeo do logo).
- `interface_campo/assets/logo-workforce.mp4` (novo, 2,87 MB).
- `tests/js/motorJornada.test.mjs` (4 testes novos).
- Fora deste repositório: `app.py` do SGO
  (`Documents/Integração SGOWorkforce/app.py`, novo - cópia de
  `origin/dev` com o botão "Voltar ao Workforce" em `_render_apontamento`
  **e** em `gerar_html_offline`, item 4.1), `LEIA-ME.md` da mesma pasta
  atualizado.

## Data e responsáveis

- Data de registro: 2026-08-11.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
