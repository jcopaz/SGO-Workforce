# ADR-0067 | Mapa Operacional e linha do tempo escondiam pulsos de jornadas que atravessam a meia-noite

## Contexto

O responsável do produto relatou um bug real no Mapa Operacional
(2026-08-12), testando com a matrícula fictícia `7777777`: jornada
iniciada em 06/08/2026 19:49:32 e encerrada em 07/08/2026. O mapa e o
gráfico de linha do tempo ao lado só mostravam os pulsos/apontamentos do
dia 06 - pra ver o resto (pulsos depois das 00h01 de Brasília do dia 07),
era preciso trocar manualmente o filtro de data.

## Causa raiz

Dois pontos independentes na mesma tela (`painel/telas/mapa_operacional.py`),
ambos recortando por **um único dia calendário**:

1. **Mapa**: o filtro "Data dos pulsos" era um `st.date_input` de data
   única (não intervalo), default = data do primeiro pulso da jornada.
   `dados.filtrar_pulsos_por_periodo(pulsos, data, hora_inicial, hora_final)`
   comparava `momento_brasil.date() != data` - qualquer pulso de outro
   dia calendário desaparecia do mapa, mesmo pertencendo à mesma jornada
   contínua.
2. **Linha do tempo**: `dados.fatiar_linha_do_tempo_por_dia(...)` já
   devolve um dict com **todos** os dias da jornada (a função existe
   desde o ADR-0051 exatamente para fatiar jornadas que atravessam a
   meia-noite em segmentos por dia), mas a tela só passava
   `.get(data_filtro, [])` para `grafico_linha_do_tempo` - descartava
   todos os outros dias antes mesmo de chegar no gráfico, que já sabia
   desenhar múltiplos dias lado a lado (mesma função usada em
   `dashboard.py` para mostrar todos os dias do colaborador).

Ou seja: a limitação nunca foi da função de fatiamento nem do gráfico -
os dois já suportavam múltiplos dias desde que foram escritos. Era
puramente a tela do mapa recortando artificialmente pra um dia só.

## Decisão

### 1. `dados.filtrar_pulsos_por_periodo` passa a aceitar um intervalo de datas

Assinatura mudou de `(pulsos, data, hora_inicial, hora_final)` para
`(pulsos, data_inicio, data_fim, hora_inicial, hora_final)` -
`data_inicio == data_fim` reproduz o comportamento antigo de dia único.
`hora_inicial`/`hora_final` continuam se aplicando a cada dia do
intervalo (útil para recortar "só o turno da manhã" ao longo de vários
dias). Os 4 testes existentes em `tests/test_mapa.py` atualizados pra
nova assinatura + 1 teste novo reproduzindo o bug relatado (jornada
06/08 22:49 UTC → 07/08 06:00 UTC, ambos os pulsos precisam sobreviver
ao filtro com o intervalo default).

### 2. Filtro do mapa vira intervalo, com default = início/fim reais da jornada

`st.date_input` de data única virou intervalo (`value=(data_inicio_padrao,
data_fim_padrao)`), com `data_inicio_padrao`/`data_fim_padrao` calculados
a partir de `marco_inicio`/`marco_fim` (primeiro e último pulso da
jornada) - por padrão, a jornada inteira aparece no mapa, sem nenhuma
ação do colaborador. O filtro continua disponível pra quem quiser
recortar um trecho específico de uma jornada longa. Mesmo padrão de
sanitização de `session_state` (`_sanitizar_periodo_state`) já usado em
`dashboard.py`, pra não quebrar ao trocar de jornada/colaborador com um
intervalo salvo que não existe mais.

### 3. Linha do tempo sempre mostra a jornada inteira, independente do filtro do mapa

`segmentos_por_dia = fatiar_linha_do_tempo_por_dia(linha_do_tempo(jornada_selecionada))`
passado inteiro pra `grafico_linha_do_tempo`/`legenda_linha_do_tempo`,
sem recorte por dia - o gráfico de barra empilhada já lida com múltiplos
dias nativamente (um dia por coluna no eixo X). A legenda e o gráfico
deixam de depender do filtro "Período dos pulsos" do mapa - são
conceitualmente diferentes (o filtro do mapa é "o que aparece no mapa
agora", a linha do tempo é sempre "o que aconteceu na jornada inteira").

## Consequências

- Jornadas de vários dias (não só 2) já funcionam com a mesma correção -
  o intervalo de datas e o fatiamento por dia não têm limite de quantos
  dias cobrem.
- Sem mudança de comportamento pra jornadas de 1 dia só (o caso mais
  comum) - intervalo com início igual ao fim se comporta exatamente
  como o filtro de data única de antes.
- Nenhuma mudança em `mapa.py`/`construir_mapa` nem no formato de dado
  devolvido pela API - só em como o painel filtra o que já recebeu.

## Validação realizada

- `python -m py_compile` em `painel/dados.py`, `painel/telas/mapa_operacional.py`,
  `tests/test_mapa.py`: OK.
- `pytest tests/test_mapa.py tests/test_mapa_operacional_painel.py`: 40
  passed (1 teste novo reproduzindo o bug relatado).
- `pytest` completo: 436 passed.

## Validação NÃO realizada

- Teste visual real no navegador com o caso relatado (matrícula
  `7777777`, jornada 06/08 19:49:32 → 07/08) - depende do responsável do
  produto confirmar em `sgoworkforce.streamlit.app`.

## Arquivos afetados

- `painel/dados.py` (`filtrar_pulsos_por_periodo`: data única → intervalo).
- `painel/telas/mapa_operacional.py` (filtro de data → intervalo com
  default = jornada inteira; linha do tempo → sempre jornada inteira;
  `_sanitizar_periodo_state` novo).
- `tests/test_mapa.py` (4 testes atualizados + 1 novo).

## Data e responsáveis

- Data de registro: 2026-08-12.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
