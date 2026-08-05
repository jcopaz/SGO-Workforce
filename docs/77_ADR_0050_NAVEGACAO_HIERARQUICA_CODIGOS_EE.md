# ADR-0050 | Navegação hierárquica (drill-down) dos códigos EE na interface de campo

## Contexto

Especificação recebida do responsável pelo produto em 2026-08-04:
substituir a lista linear de códigos EE (23 códigos num `<select>` só,
mesmo agrupados por optgroup) por uma navegação em 3 blocos operacionais
- Apoio e Preparação / Execução / Interrupções -, refletindo o modelo
mental do eletricista em campo ("estou me preparando" / "estou
executando" / "estou impedido") em vez de obrigar a busca numa lista de
23 itens toda vez.

Dois pontos da especificação original não bateram exatamente com o
motor de domínio existente e precisaram de reconciliação (`motorJornada.js`
não foi alterado - CLAUDE.md regra de ouro, requisito explícito do
pedido: "não alterar nenhuma regra de negócio, persistência, cálculos,
enums ou catálogo existente"):

1. **EE17 (Manutenção Programada) e EE21 (Atendimento de Falha) não são
   códigos soltos no motor** - são o resultado de como uma Atividade é
   iniciada (`motor.iniciarAtividade`/`iniciarAtendimentoFalha`), nunca
   uma escolha direta de código. Tratados como itens especiais injetados
   no bloco Execução, mantendo exatamente o mesmo comportamento de
   antes (abrem o fluxo de atividade/atendimento), só com o código
   visível no rótulo agora.
2. **EE23 (Manutenção Não Concluída) não é selecionável para iniciar
   nada** - só existe como desfecho de encerramento de uma atividade já
   em andamento (botão "Atividade não concluída", inalterado). Não
   aparece em bloco nenhum da navegação.
3. **EE22 (Treinamento) não apareceu em nenhum bloco da especificação
   original recebida** - mesma família de EE02/EE11 (`tipo_registro=pausa`),
   adicionado em Interrupções → Pausas.

## Decisão

### 1. `interface_campo/js/estruturaCodigos.js` (novo)

Módulo de dados puros: `ESTRUTURA_BLOCOS` (3 blocos, o terceiro com 2
subgrupos - Esperas/Pausas) mapeando cada código EE (exceto EE17/21/23,
ver reconciliação) para um bloco/subgrupo. **Não é um catálogo** - as
descrições de cada código continuam vindo do catálogo dinâmico (backend
com fallback offline, `catalogoMotivos.js`, inalterado); este módulo só
decide em qual bloco cada código aparece.

`agruparCodigosDisponiveis(motivosDisponiveis, itensExtrasPorBloco)`
filtra a estrutura para conter só os códigos realmente disponíveis no
contexto atual (o motor de domínio decide isso, nunca este módulo -
pausa aninhada numa atividade só pode usar os 5 códigos tipo `pausa`;
jornada solta usa todos os 20 soltos). Blocos/subgrupos vazios não
aparecem. `itensExtrasPorBloco` injeta itens que não vêm do catálogo
(as sentinelas EE17/EE21) no bloco indicado. Código presente no catálogo
mas não classificado em nenhum bloco cai num bloco "Outros" - nunca some
silenciosamente (rede de segurança direta contra o esquecimento do EE22
que quase se repetiu na implementação).

### 2. `interface_campo/js/app.js` - `renderSelecaoHierarquica`

Substitui `criarSeletorMotivoPausa`/`criarSeletorAcaoPrincipal` (dois
`<select>` planos) por um componente único de navegação em blocos,
reutilizado nos dois contextos onde um código é escolhido:

- Selecionando uma ação com a jornada aberta e nada em andamento (antes:
  seletor único + botão "Iniciar").
- Iniciando uma pausa dentro de uma atividade ativa (antes: seletor +
  botão "Iniciar pausa").

Estado (`blocoExpandido`, `null` = mostrando os 3 blocos) compartilhado
entre os dois contextos - nunca aparecem ao mesmo tempo. Tocar num
código folha dispara a ação **diretamente** (sem precisar de um botão de
confirmação separado depois, uma etapa a menos que antes) e passa pela
mesma trava de GPS obrigatório de sempre (`executarComGpsObrigatorio`,
inalterada). Se a transição falhar (sem sinal de GPS), o bloco continua
expandido - o colaborador só precisa tocar de novo, não perde a
navegação.

### 3. `interface_campo/css/estilo.css`

Blocos com um filete lateral colorido (azul/verde/vermelho, mesma
paleta pedida - 🔵🟢🔴) em vez de preencher o botão inteiro, mantendo
consistência visual com o resto do app. Título do bloco expandido em
negrito; subgrupos ("Esperas"/"Pausas") com rótulo em maiúsculas,
separados visualmente dos itens (requisito 4 da especificação).

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 126 passed (118 anteriores + 8 novos em
  `tests/js/estruturaCodigos.test.mjs`) - inclui o teste que teria
  pegado o esquecimento do EE22 automaticamente (`todo codigo solto
  esperado aparece exatamente uma vez na estrutura de blocos`).
- `pytest` completo: 352 passed, sem regressão (nenhum arquivo `.py`
  tocado neste ADR - o motor de domínio não mudou, como exigido).
- Leitura completa do trecho reescrito de `app.js` (ambos os pontos de
  uso de `renderSelecaoHierarquica`) confirmando que a trava de GPS
  obrigatório e o catálogo dinâmico continuam exatamente como antes, só
  a apresentação mudou.

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre) - especialmente
  importante aqui por ser uma mudança de UX grande na tela mais usada do
  app; vale um teste manual dedicado antes de considerar "pronto para
  operação real".
- Nenhuma validação de usabilidade formal (não há como medir "reduziu a
  carga cognitiva" neste ambiente) - só a estrutura de dados e o
  comportamento programático foram verificados.

## Arquivos afetados

- `interface_campo/js/estruturaCodigos.js` (novo).
- `interface_campo/js/app.js` (`renderSelecaoHierarquica`, remove
  `criarSeletorMotivoPausa`/`criarSeletorAcaoPrincipal`).
- `interface_campo/css/estilo.css` (estilo dos blocos/subgrupos).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v20, novo arquivo
  na lista do app shell).
- `interface_campo/index.html` (rodapé "Versão v20").
- `tests/js/estruturaCodigos.test.mjs` (novo).
