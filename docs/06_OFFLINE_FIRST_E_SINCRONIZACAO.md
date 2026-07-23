# Offline first e sincronização

## Requisitos
- iniciar/encerrar eventos sem internet;
- registrar falha e catálogos em cache;
- capturar pulsos GPS;
- visualizar fila pendente;
- sincronizar automaticamente quando a rede voltar;
- permitir reenvio seguro;
- impedir duplicidade.

## Estratégia local
IndexedDB com stores: `jornadas`, `eventos`, `falhas`, `gps_pulsos`, `sync_queue`, `catalogos` e `metadados`.

## Identidade idempotente
Cada registro recebe UUID no cliente. A API usa `client_event_id`/`client_pulse_id` como chave única. Reenvio retorna sucesso sem duplicar.

## Estados de sync
- local;
- pendente;
- enviando;
- sincronizado;
- erro_retry;
- conflito;
- rejeitado.

## Ordem
1. usuário e catálogos;
2. jornada;
3. eventos;
4. falhas vinculadas;
5. pulsos em lote;
6. anexos.

## Conflitos
Conflitos nunca são resolvidos silenciosamente. O servidor registra a tentativa, conserva o original e encaminha para auditoria quando necessário.

## Lotes GPS
Enviar em lote comprimido, com limite configurável e resposta por item. Após confirmação do servidor, marcar como sincronizado; não apagar imediatamente o histórico local até a política de retenção.
