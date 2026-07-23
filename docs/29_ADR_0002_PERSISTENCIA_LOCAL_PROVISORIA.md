# ADR-0002 | Persistência local provisória: arquivo JSON por jornada

## Contexto

O Incremento 2 exige persistência local e recuperação de estado
(`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 11). A mesma
seção 15.3 lista como pendente, "antes do Incremento 2": política de
retenção local após gravação, formato definitivo de serialização,
recuperação de estado após fechamento e comportamento perante corrupção da
base local.

O Incremento 4 (interface de campo) trará a implementação real em
PWA/IndexedDB (seção 4.1 do alinhamento). Antes disso, era necessário um
formato de contrato e um algoritmo de recuperação testáveis em Python puro,
sem travar o desenvolvimento à espera de decisões de UI ainda não tomadas.

## Decisão

1. **Armazenamento**: um arquivo JSON por jornada, nomeado pelo UUID da
   jornada (`<uuid>.json`), dentro de um diretório configurável
   (`RepositorioJornadaArquivo`). É um substituto local testável do que
   será IndexedDB no navegador — o contrato de campos (ver item 2) é o que
   deve permanecer estável entre as duas implementações, não o meio físico.
2. **Formato de serialização**: dict JSON com `formato_versao`, timestamps
   em ISO 8601 (`datetime.isoformat()`), UUIDs como string e enums pelo
   `.value`. Implementado em `src/workforce_storage/serializacao.py`.
3. **Escrita atômica**: `salvar()` grava em `<uuid>.json.tmp` e substitui o
   arquivo final com `Path.replace` (que usa `os.replace`, atômico no mesmo
   sistema de arquivos). Isso evita que um processo interrompido no meio da
   gravação deixe um arquivo parcialmente escrito no lugar do anterior.
4. **Comportamento perante corrupção**: um arquivo ilegível (JSON inválido)
   ou estruturalmente inválido nunca é apagado, sobrescrito ou ignorado
   silenciosamente — `carregar()` levanta `ArquivoCorrompidoError` e o
   arquivo original permanece intacto no disco para inspeção ou recuperação
   manual. Espelha a regra de ouro do CLAUDE.md: "falha de GPS não pode
   apagar eventos operacionais já registrados", aplicada aqui a qualquer
   falha de leitura local.
5. **Recuperação de estado**: o "estado ativo" (qual atividade e qual pausa
   estão em andamento) nunca é persistido como campo separado — é sempre
   recalculado a partir dos estados (`ATIVA`/`PAUSADA`/`ENCERRADA`) das
   entidades por `MotorJornada.a_partir_de()`. Isso elimina a possibilidade
   de o ponteiro de "ativo agora" divergir dos estados reais gravados.
   Um estado logicamente impossível (duas atividades ativas, por exemplo)
   é detectado nessa reconstrução e reportado como `EstadoInconsistenteError`
   (dentro de `workforce_core`), propagado pelo repositório como
   `ArquivoCorrompidoError`.

## Alternativas consideradas

- **SQLite local**: mais próximo do que uma futura sincronização exigiria,
  mas adiciona uma dependência de schema/migração antes de o contrato de
  campos estar validado. Adiado — pode substituir o backend de arquivo sem
  mudar `workforce_core` nem o formato de dict, já que a camada de
  serialização está isolada do dominio.
- **Persistir o "ativo agora" como campo redundante**: rejeitado por
  introduzir uma segunda fonte de verdade que poderia divergir dos estados
  das entidades após uma edição manual do arquivo ou um bug de gravação.
- **Ignorar silenciosamente arquivos corrompidos**: rejeitado por violar a
  regra de ouro de não perder/mascarar dados operacionais já registrados.

## Consequências

- O contrato de campos (`jornada_para_dict`/`jornada_de_dict`) é o que
  precisa ser replicado em JavaScript quando o Incremento 4 implementar
  IndexedDB — isso deve ser revisto nessa ocasião, não assumido como
  definitivo.
- Política de retenção após sincronização (quando manter/apagar o arquivo
  local depois de confirmado no servidor) continua em aberto — pertence ao
  Incremento 3, quando a sincronização existir.
- `listar_abertas()` ignora arquivos corrompidos ao montar a lista de
  jornadas para recuperação, mas não os apaga; um operador ou uma rotina de
  diagnóstico futura precisa tratá-los explicitamente.

## Validação operacional

Ainda não realizada. Decisão provisória, sujeita a revisão quando o
Incremento 4 definir o ambiente real (PWA/IndexedDB) e o Incremento 3
definir a fila de sincronização.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto, antes do Incremento 3 (fila
  offline) e do Incremento 4 (interface de campo).
