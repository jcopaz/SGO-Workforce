# ADR-0003 | Fila offline e sincronização idempotente provisórias

## Contexto

O Incremento 3 exige fila offline e sincronização idempotente
(`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 11), e a seção
3.4 fixa como regra inegociável: cada registro tem UUID de cliente, a
sincronização é idempotente, o reenvio não gera duplicidade, a fila mostra
pendentes/sincronizados/com erro/em conflito, e conflitos nunca são
resolvidos silenciosamente.

A mesma versão do alinhamento lista como pendente, "antes do Incremento 3":
convenção final de UUID do cliente, política de retry e backoff, tamanho
máximo de lote, regras de conflito, retenção local após confirmação do
servidor e autenticação técnica da API. **Nenhuma API real existe ainda** —
FastAPI e Postgres/Neon (seção 4.3/4.4 do alinhamento) não fazem parte de
nenhum incremento numerado até aqui.

## Decisão

1. **Transporte plugável**: `ClienteSincronizacao` é um `Protocol` com um
   único método (`enviar_jornada`). `ClienteSincronizacaoEmMemoria`
   (`src/workforce_sync/cliente.py`) é uma implementação falsa que simula
   um servidor idempotente para desenvolvimento e testes. Quando a API real
   existir, um novo cliente HTTP implementando o mesmo Protocol poderá
   substituí-la sem alterar `Sincronizador` nem `FilaSincronizacao`.
2. **Granularidade de sincronização**: a jornada inteira (com suas
   atividades e pausas aninhadas) é a unidade sincronizada, identificada
   pelo UUID já gerado no cliente na criação da entidade (Incremento 1).
   Não há sincronização de eventos individuais neste incremento — isso
   pode mudar quando o contrato real da API for definido (a arquitetura
   alvo, seção 4.3, prevê endpoints separados para jornadas, eventos e
   falhas).
3. **Fila persistida em arquivo**: um `RegistroFila` por jornada
   (`status`, `tentativas`, `ultimo_erro`, timestamps), no mesmo padrão de
   escrita atômica e não deleção em caso de corrupção usado em
   `workforce_storage` (ADR-0002). A fila precisa sobreviver a
   fechamento/reinício tanto quanto a jornada em si.
4. **Idempotência**: garantida pelo cliente de transporte, que trata
   `enviar_jornada` como upsert por `jornada_id` — reenviar o mesmo
   identificador nunca cria um segundo registro do lado do servidor
   (simulado). O sincronizador também evita trabalho desnecessário: um
   registro já `SINCRONIZADO` não entra no lote seguinte enquanto não for
   reenfileirado (ou seja, enquanto o conteúdo não mudar de novo).
5. **Conflito nunca é automático**: um registro que recebe `CONFLITO` do
   transporte é marcado como tal e **excluído** dos lotes automáticos
   seguintes (`Sincronizador.sincronizar_pendentes` só reconsidera
   `PENDENTE` e `ERRO`). Só volta a ser tentado após alguém chamar
   `FilaSincronizacao.enfileirar` de novo, explicitamente — o que hoje
   representa uma ação deliberada de quem chama, não uma resolução
   automática de qual versão "vence". A regra de negócio de resolução de
   conflito continua **não implementada e não inventada**.
6. **Tamanho de lote**: parâmetro `tamanho_lote` de
   `sincronizar_pendentes`, com padrão `TAMANHO_LOTE_PADRAO = 20`. É um
   valor técnico de partida, não uma decisão de negócio validada.
7. **Retry**: uma falha (`ERRO`) é automaticamente reconsiderada na
   próxima chamada de `sincronizar_pendentes` (sem limite de tentativas
   nem backoff neste incremento). `tentativas` é incrementado a cada
   chamada e fica disponível para uma política de backoff futura.
8. **Isolamento de falhas por item**: uma exceção ao processar um registro
   (por exemplo, arquivo de jornada corrompido) marca aquele registro como
   `ERRO` e não interrompe o processamento dos demais itens do lote.

## Alternativas consideradas

- **Sincronizar eventos individuais em vez da jornada inteira**: mais
  próximo do desenho final da API (seção 4.3), mas exigiria decidir agora
  o contrato de eventos que ainda não existe. Adiado para quando a API
  real for desenhada.
- **Backoff exponencial automático já neste incremento**: rejeitado por
  ser uma política de negócio/operacional ainda não validada (item
  explicitamente pendente na seção 15.3); implementar um valor arbitrário
  criaria falsa sensação de decisão tomada.
- **Deixar o sincronizador decidir automaticamente o "lado vencedor" em
  conflito**: rejeitado por violar diretamente a regra de ouro "conflitos
  não podem ser resolvidos silenciosamente".

## Consequências

- `ClienteSincronizacaoEmMemoria` não deve ser usado em produção — é
  exclusivamente um substituto de desenvolvimento/teste até existir uma
  API real.
- Autenticação técnica do cliente não existe neste incremento; qualquer
  cliente real precisará adicionar essa camada sem alterar o Protocol
  `ClienteSincronizacao` (a assinatura não inclui credenciais hoje — pode
  precisar ser revista quando a autenticação for desenhada).
- Retenção do arquivo local de jornada após confirmação de sincronização
  continua indefinida: hoje o arquivo em `workforce_storage` não é
  removido nem marcado de nenhuma forma após `marcar_sincronizado`. Isso é
  intencional (evita perda de dados por decisão prematura), mas é uma
  lacuna a fechar quando a política de retenção for definida.
- Tamanho de lote e política de retry deverão ser revistos com dados reais
  de campo (volume de eventos por dia, qualidade de rede em área
  operacional) antes de produção.

## Validação operacional

Ainda não realizada. Decisão provisória, sujeita a revisão quando a API
real (FastAPI) e a política de conflito/retenção forem definidas.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto, antes de existir uma API
  real e antes de produção.
