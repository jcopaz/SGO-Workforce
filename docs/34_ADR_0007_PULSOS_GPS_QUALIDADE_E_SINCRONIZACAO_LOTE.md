# ADR-0007 | Pulsos GPS, qualidade e sincronização em lote (Incremento 7)

## Contexto

`docs/08_GPS_PULSOS_E_PRIVACIDADE.md` já definia, antes desta sessão: os
campos de um pulso, a exigência de nunca descartar a precisão original, a
regra de marcar (não sobrescrever) pontos impossíveis/saltos/velocidade
incompatível, e que permanência inferida por GPS deve sempre ser
distinguida do evento declarado. `docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`
seção 3.6 repete essas mesmas regras como inegociáveis, e a seção 15.3
("Antes do Incremento 7: GPS") lista como pendente: intervalo padrão de
pulsos, política adaptativa por movimento/bateria, obrigatoriedade de GPS,
contingência por indisponibilidade, precisão mínima desejável, retenção,
perfis autorizados a ver trajetórias, e validação de LGPD/segurança da
informação/política corporativa.

## Decisão

1. **`PulsoGps`** (`workforce_core/entities.py`): entidade própria, **não
   aninhada em `Jornada`** (ao contrário de `Atividade`/`EventoSecundario`),
   vinculada por `jornada_id`. Motivo: volume esperado muito maior (um
   pulso a cada 60-120s por horas) e a arquitetura alvo (seção 4.4 do
   alinhamento) já lista "pulsos GPS" como entidade própria, separada da
   jornada. Campos = exatamente os listados em `docs/08` seção "Campos" —
   nenhum foi inventado.
2. **`QualidadePulso`** (`workforce_core/enums.py`): `OK`,
   `PRECISAO_RUIM`, `SALTO_IMPOSSIVEL`, `VELOCIDADE_INCOMPATIVEL`,
   `NAO_AVALIADO`. As três primeiras categorias de defeito são citadas
   literalmente em `docs/08` ("Qualidade"); não são categorias inventadas.
3. **`workforce_core/qualidade_gps.py`**: funções puras de avaliação —
   `distancia_metros` (haversine), `velocidade_implicita_metros_segundo`,
   `avaliar_pulso`. **Nenhum limiar numérico tem valor padrão** —
   `precisao_maxima_aceitavel_metros` e
   `velocidade_maxima_plausivel_metros_segundo` são parâmetros
   obrigatórios de quem chama. Isso é deliberado: "precisão mínima
   desejável" está explicitamente pendente (seção 15.3); embutir um
   número aqui seria inventar a decisão que o alinhamento pede para não
   inventar. A avaliação nunca altera `pulso.precisao_metros` — apenas
   devolve uma classificação para o chamador marcar (`docs/08`: "marcados,
   não sobrescritos").
4. **Armazenamento local append-only** (`RepositorioPulsosGpsArquivo`):
   um arquivo `.jsonl` por jornada (uma linha por pulso), com
   `flush`+`fsync` a cada gravação. Diferente do padrão
   "escrever tudo de novo, atomicamente" usado para `Jornada`
   (`RepositorioJornadaArquivo`) — reescrever um arquivo que cresce a cada
   60-120s degradaria com o tempo. Uma linha corrompida no meio do arquivo
   é ignorada na leitura (`ler_pulsos`) sem apagar nem afetar as demais
   linhas; `ler_pulsos_com_erros` expõe o número da linha para diagnóstico.
5. **Sincronização em lote por cursor**, não por fila de 4 estados: pulsos
   não têm o conceito de "conflito" que uma jornada tem (ninguém mais edita
   um pulso já gravado), então um cursor por jornada
   (`total_sincronizado: int`) é suficiente. `SincronizadorPulsos` lê o
   próximo lote de pulsos ainda não confirmados, envia via
   `ClienteSincronizacao.enviar_lote_pulsos` (extensão do mesmo Protocol do
   Incremento 3) e só avança o cursor se o lote inteiro for aceito.
   `ClienteSincronizacaoEmMemoria.enviar_lote_pulsos` trata cada lote como
   upsert por id de pulso — reenviar o mesmo intervalo (ex.: após um ack
   perdido) nunca duplica.
6. **`TAMANHO_LOTE_PULSOS_PADRAO = 100`**: valor técnico de partida
   (maior que o de jornadas, já que pulsos são registros bem menores),
   não uma decisão de negócio validada — mesmo espírito do
   `TAMANHO_LOTE_PADRAO` do ADR-0003.

## Deliberadamente fora deste incremento

- **Captura real de GPS no navegador** (`navigator.geolocation`,
  `watchPosition`, permissão do usuário): não implementada em
  `interface_campo/js/`. Exige teste em dispositivo real, que este
  ambiente não consegue fazer (mesma limitação registrada no ADR-0004).
  Sem isso, não há também intervalo de captura real para calibrar — a
  sugestão de 60-120s de `docs/08` permanece apenas uma sugestão de
  produto, não um valor codificado em lugar nenhum.
- **Qualquer limiar numérico de qualidade** (precisão mínima, velocidade
  máxima plausível): não definido em código algum — sempre exigido como
  parâmetro explícito (ver item 3).
- **Obrigatoriedade de GPS** para iniciar/encerrar jornada, atividade ou
  atendimento de falha: não implementada — essas transições continuam
  funcionando exatamente como antes, sem qualquer acoplamento a GPS.
- **Política de contingência para GPS indisponível**: não implementada
  (bloquear, sinalizar, ou seguir sem pulso são todas decisões de negócio
  pendentes).
- **Retenção de dados de localização, perfis autorizados a visualizar
  trajetória, e a avaliação de LGPD/segurança da informação/política
  corporativa** exigida antes de produção (`docs/08` "Privacidade"): nada
  disso foi endereçado — este incremento é infraestrutura técnica, não uma
  aprovação de uso em produção.
- **Inferência de permanência/deslocamento** a partir de clusters de
  pulsos (`docs/08` "Permanência"): não implementada; fica para quando o
  mapa operacional (Incremento 10) ou a consolidação de qualidade
  (Incremento 8) precisar dela.

## Alternativas consideradas

- **Aninhar pulsos dentro de `Jornada`**, como `EventoSecundario`:
  rejeitado pelo volume (potencialmente centenas de pulsos por jornada
  reescrevendo o arquivo inteiro a cada gravação) e por contrariar o
  modelo de dados alvo, que já trata pulsos GPS como entidade própria.
- **Reaproveitar a fila de 4 estados (`FilaSincronizacao`) para pulsos**:
  rejeitado — o conceito de "conflito" da fila de jornadas não se aplica a
  um fluxo append-only sem edição concorrente; um cursor é mais simples e
  suficiente.
- **Definir um limiar padrão "razoável"** (ex.: 50m de precisão, 120 km/h
  de velocidade máxima): rejeitado explicitamente por ser exatamente o
  tipo de decisão que a seção 6 do alinhamento oficial proíbe inventar.

## Validação operacional

Ainda não realizada. Toda a parte de qualidade depende de limiares que
são decisão de negócio; toda a parte de captura real depende de teste em
dispositivo/navegador real, que não foi possível neste ambiente.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (limiares de qualidade,
  obrigatoriedade, contingência, retenção, perfis, LGPD) antes de
  qualquer uso real; captura em `interface_campo/js/` antes de qualquer
  piloto com colaboradores.
