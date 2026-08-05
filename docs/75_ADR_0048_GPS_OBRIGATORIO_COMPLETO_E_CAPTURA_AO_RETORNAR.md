# ADR-0048 | GPS obrigatório completo (pausa/evento secundário) e captura ao retornar ao primeiro plano

## Contexto

Depois de testar a captação real de GPS com colaboradores (ADR-0044 a
0047), o responsável pelo produto relatou em 2026-08-04: o pulso
periódico para de ser capturado quando o app é minimizado ou o
colaborador troca de aba/aplicativo. Investigação confirmou que **não é
bug** - é limitação de plataforma (navegador mobile suspende JavaScript,
incluindo `navigator.geolocation`, fora do primeiro plano; ainda mais
restrito em segundo plano real e absoluto com a tela travada). Pesquisa
em inglês confirmou que não existe nenhuma API nova em 2026 que resolva
isso só com PWA - captação contínua de verdade em segundo plano exige um
app nativo (Capacitor + plugin de geolocalização em segundo plano,
orçamento e caminhos técnicos registrados em memória, não implementado
neste ADR - decisão maior, ainda em aberto).

Este ADR cobre o que dá para melhorar **hoje, dentro do PWA atual**, sem
depender dessa decisão maior: aproveitar melhor as janelas em que o app
já está garantidamente em primeiro plano.

O responsável pelo produto identificou dois pontos concretos:

1. Toda vez que o colaborador interage com **qualquer** botão do app
   (não só iniciar/encerrar jornada e atividade), o app está
   obrigatoriamente em primeiro plano naquele instante - uma janela
   garantida de captura que hoje não estava sendo aproveitada em pausa e
   evento secundário (deslocamento, refeição, documentação etc.).
2. Quando o colaborador volta para a aba depois de minimizar, é outra
   janela garantida - hoje o app só recomeça a capturar no próximo tick
   do intervalo de 1 minuto, podendo perder vários minutos de atraso
   desnecessário.

Revisitando a decisão original do ADR-0043 ("Obrigatório em tudo" foi a
resposta escolhida para o escopo do GPS obrigatório) confirmou que a
implementação da Fase 2 (ADR-0045) tinha ficado **incompleta**: só cobria
iniciar/encerrar jornada e atividade, não pausa nem evento secundário.
Perguntado diretamente se os 4 pontos novos deveriam travar a ação (como
jornada/atividade) ou ser best-effort, o responsável pelo produto
confirmou: **travar, igual jornada/atividade** - mantém a regra
"obrigatório em tudo" ao pé da letra.

## Decisão

### 1. GPS obrigatório estendido a pausa e evento secundário (`interface_campo/js/app.js`)

Os 4 pontos que faltavam agora usam `executarComGpsObrigatorio` (a mesma
trava já usada em jornada/atividade desde o ADR-0045) em vez de
`executar` direto:

- `iniciarPausa` (botão "Iniciar pausa", dentro de uma atividade).
- `finalizarPausa` (botão "Finalizar pausa").
- `iniciarEventoSecundario` (botão "Iniciar" quando a lista única
  resolve para um código de pausa avulsa ou deslocamento/espera/apoio -
  ramo que ficou de fora deliberadamente no ADR-0045, agora corrigido).
- `encerrarEventoSecundario` (botão "Encerrar evento").

Total agora: 10 pontos de transição com GPS obrigatório (jornada
iniciar/encerrar, atividade iniciar/encerrar/não-concluída/atendimento
de falha, pausa iniciar/encerrar, evento secundário iniciar/encerrar) -
cobre literalmente todo iniciar/encerrar de evento do motor de domínio,
como o ADR-0043 pedia desde o início.

### 2. Captura ao retornar ao primeiro plano (`interface_campo/js/app.js`)

Nova função `configurarCapturaAoVoltarParaPrimeiroPlano()`, registrada
uma vez na inicialização do app (junto de `configurarSimulador()`):
escuta o evento `visibilitychange` do navegador e, quando a aba volta a
ficar visível **e** existe uma jornada `ABERTA`, dispara uma captura de
GPS imediata (reaproveitando `capturarPosicaoAtual()`/`registrarPulsoCapturado`,
os mesmos usados pela captura periódica). Best-effort, igual à captura
periódica de fundo - nunca mostra erro nem bloqueia nada se a captura
falhar (diferente da trava de GPS obrigatório, que é intencionalmente
bloqueante).

Isso não resolve a limitação de segundo plano (o app continua sem captar
nada enquanto estiver minimizado) - só garante que o retorno ao app seja
aproveitado imediatamente, em vez de esperar até um minuto pelo próximo
tick do intervalo periódico.

### 3. Versão do app shell

`CACHE_VERSAO` "v18" → "v19" (`interface_campo/service-worker.js`),
rodapé "Versão v19" (`interface_campo/index.html`) - toda mudança em
`interface_campo/js/` exige isso (lição já registrada nesta sessão).
Aviso fixo da tela também atualizado para descrever o escopo completo do
GPS obrigatório e o comportamento de captura ao retornar.

## O que fica registrado em memória, não implementado aqui

Pesquisa completa de alternativas para captação contínua em segundo
plano de verdade (limitações reais do Android, orçamento em R$/US$ de
app nativo com/sem serviço em primeiro plano, comparação de plugins
pagos e gratuitos, Traccar como alternativa) foi salva na memória do
projeto (`project-gps-segundo-plano-alternativas`) - decisão maior,
ainda em aberto, fora do escopo deste ADR.

## Validação de qualidade realizada

- `node --check interface_campo/js/app.js`: OK.
- `node --test tests/js`: 118 passed, sem regressão (nenhum módulo
  puro/testável foi tocado - as duas mudanças são orquestração de DOM em
  `app.js`, mesma categoria de código já sem cobertura automatizada nesse
  arquivo, ver ADR-0045).
- `pytest` completo: 352 passed, sem regressão (nenhum arquivo `.py`
  tocado neste ADR).
- Leitura completa dos 10 pontos de `executarComGpsObrigatorio` em
  `app.js` para confirmar que os 4 novos foram cobertos corretamente e
  que o handler do botão "Iniciar" (que já era `async` desde o
  ADR-0045) recebeu o `await` certo no ramo de evento secundário.

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre) - inclusive para
  confirmar que `visibilitychange` dispara de forma confiável no
  navegador/PWA real do colaborador ao voltar de outro app, não só ao
  trocar de aba dentro do mesmo navegador (comportamento pode variar
  entre Android/Chrome e outros navegadores).
- Nenhuma mudança de captação contínua em segundo plano - ver seção
  acima, decisão maior registrada em memória, não decidida ainda.

## Arquivos afetados

- `interface_campo/js/app.js` (GPS obrigatório em 4 pontos novos,
  captura ao retornar ao primeiro plano).
- `interface_campo/index.html` (aviso atualizado, versão v19).
- `interface_campo/service-worker.js` (`CACHE_VERSAO` v19).
