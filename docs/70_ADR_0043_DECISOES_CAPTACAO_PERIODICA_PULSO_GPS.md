# ADR-0043 | Decisões de negócio - captação periódica de pulso GPS

## Contexto

Sequência direta do ADR-0042 (levantamento de lacunas). O ADR-0042
deliberadamente não decidiu nada - listou o que faltava e disse "isso
é decisão do responsável do produto". Este ADR registra as decisões
tomadas na mesma sessão, via perguntas objetivas.

## Decisões

### 1. Intervalo de captura: 1 pulso por minuto

Durante a jornada ativa, o dispositivo captura um pulso de GPS a cada
1 minuto. Equilíbrio entre trajetória útil e consumo de bateria/dados -
não é adaptativo (não muda a frequência por movimento/parado) para
manter a primeira versão simples.

### 2. Obrigatoriedade: GPS obrigatório para iniciar/encerrar jornada e atividade

Ao contrário da recomendação inicial (não obrigatório, para não travar
o colaborador em área sem sinal), o responsável do produto escolheu
**obrigatório em tudo**: iniciar jornada, encerrar jornada, iniciar
atividade e encerrar atividade exigem uma leitura de GPS bem-sucedida
no momento da ação.

Importante: **isso é uma exigência local, não de rede** - conseguir uma
leitura de GPS do hardware do aparelho não depende de conectividade
(ver decisão 5, captação 100% offline). "Obrigatório" aqui significa
"o `getCurrentPosition`/`watchPosition` do navegador precisa retornar
uma coordenada", não "precisa sincronizar com o servidor primeiro".

### 3. Contingência dos pulsos periódicos: segue sem pulso, marca a lacuna

Diferente da decisão 2 (que é sobre o momento pontual de iniciar/
encerrar), os pulsos periódicos de **background** (a cada 1 minuto,
decisão 1) não bloqueiam nada se falharem - um pulso perdido no meio
da jornada só vira uma lacuna de qualidade, sem impedir o colaborador
de continuar trabalhando. Não há "ação" pontual do usuário pra
bloquear nesse caso.

### 4. Retenção: 90 dias

Pulsos de GPS brutos ficam retidos por 90 dias após a captura. Cobre
um ciclo comum de auditoria/investigação sem acumular dado sensível de
localização indefinidamente. Expurgo automático após esse prazo ainda
não tem mecanismo implementado (ver plano de implementação em
`docs/71_ADR_0044_*`, se/quando escrito).

### 5. Modelo de sincronização: 100% offline durante o dia, sincroniza em lote (não é rastreamento ao vivo)

Esclarecimento importante do responsável do produto, que muda a
arquitetura pretendida: **não é necessário pulso "online"/em tempo
real**. O requisito é auditoria posterior, não acompanhamento ao vivo
de onde cada colaborador está agora. Isso confirma e reforça o desenho
que já existia no domínio desde o ADR-0007
(`SincronizadorPulsos`/`CursorSincronizacaoPulsos` - fila local +
sincronização em lote por cursor) - a lacuna real não é arquitetural
no sentido do algoritmo de sync (que já está pronto e testado), é a
**ausência de um transporte HTTP real** (hoje só existe o cliente fake
em memória, `ClienteSincronizacaoEmMemoria`) e de um **endpoint/tabela
no backend real** pra receber esse lote.

Prático: o painel de mapa não precisa (e não deveria, nesta fase)
tentar mostrar "onde o colaborador está agora" - continua sendo uma
ferramenta de trajetória **retrospectiva**, igual já é hoje (só que
lendo do backend real em vez de arquivo local fabricado).

**Gatilho de sincronização confirmado pelo responsável do produto**: os
pulsos capturados durante o dia (offline, sem rede) só precisam ser
enviados quando o colaborador encerra a jornada **e** aciona a
sincronização - o mesmo momento/botão "Sincronizar agora" que já existe
hoje para jornada/eventos (`interface_campo/js/sincronizacao.js`). Não
é necessário nenhum gatilho novo, nem sincronização em segundo plano
durante o turno - os pulsos ficam na fila local (IndexedDB, a
construir) e saem junto com o próximo envio de sincronização normal.
Isso simplifica a Fase 3 do plano de implementação: reaproveitar o
fluxo de sincronização já existente, só adicionando o lote de pulsos
nele, em vez de construir um mecanismo de envio paralelo.

## Decisões ainda pendentes (fora do escopo desta rodada)

- Limiares numéricos exatos de qualidade (precisão máxima aceitável
  em metros, velocidade máxima plausível entre pulsos consecutivos) -
  ainda não definidos, vão precisar de um valor de partida proposto
  antes da implementação (engenharia propõe, produto aprova).
- Perfis autorizados a ver trajetória de quem - bloqueado por não
  existir autenticação de usuário no sistema ainda (item já adiado
  antes, ver `docs/23_DECISOES_PENDENTES.md`).
- Avaliação LGPD formal específica de captação contínua de localização
  - fora do escopo de uma decisão de produto isolada, precisa de
  revisão jurídica/compliance, não decidida aqui.

## Arquivos afetados

Nenhum - documento de decisão, sem mudança de código. Ver próximo ADR
para o plano de implementação faseado.
