# ADR-0051 | Gráfico de linha do tempo da jornada (dia × hora)

## Contexto

Pedido do responsável pelo produto em 2026-08-04, com uma imagem de
referência: um gráfico de barras empilhadas onde o eixo X é o dia e o
eixo Y é o horário (00:00 a 23:59, grade de hora em hora), cada coluna
mostrando a sequência real de apontamentos daquele dia posicionados no
horário exato em que aconteceram - "verificar visualmente o que foi
feito durante a jornada graficamente separado pelos apontamentos
sequenciais". Dois lugares: ao lado do mapa operacional (uma jornada, o
dia já selecionado nos filtros existentes) e na aba Visão Geral
(compilado por vários dias, com base nos filtros de colaborador/período
já existentes).

A Visão Geral já tinha um filtro multi-seleção de colaboradores
(`colaboradores_selecionados`) - perguntado diretamente como esse
gráfico deveria se comportar com mais de um colaborador selecionado (uma
coluna por dia não comporta várias pessoas ao mesmo tempo sem virar
bagunça visual), o responsável pelo produto confirmou: **exige
selecionar 1 colaborador por vez**, com um seletor dedicado, separado do
multiselect que filtra o resto da tela.

## Decisão

### 1. `workforce_core/consolidacao.py` - `linha_do_tempo(jornada)`

Nova função de domínio: decompõe a jornada inteira (do início ao fim, ou
até o último evento encerrado se ainda aberta - nunca extrapola até
"agora") numa sequência de `IntervaloClassificado` consecutivos e sem
sobreposição - Atividade, Atendimento de Falha, Pausa (com precedência
sobre a atividade que a contém, mesma regra de `classificar_instante`,
ADR-0047), Evento Secundário, ou "SEM_ATIVIDADE" preenchendo qualquer
lacuna entre dois intervalos reconhecidos. Só considera eventos com
início E fim gravados.

### 2. `painel/dados.py` - `fatiar_linha_do_tempo_por_dia`

Converte os intervalos (instantes UTC-aware vindos do backend) para o
horário de Brasília e recorta por dia calendário - um intervalo que
atravessa a meia-noite de Brasília vira 2+ segmentos, um por dia, cada
um com `minuto_inicio`/`minuto_fim` (0 a 1440) dentro daquele dia. Nova
dataclass `SegmentoLinhaDoTempo`.

### 3. `painel/graficos.py` - `grafico_linha_do_tempo`

Barra empilhada (pyecharts `Bar`) com uma técnica de **séries genéricas
por posição** (não por código): como cada dia pode ter uma quantidade
diferente de apontamentos sequenciais, não dá para ter uma série fixa
por código EE - a série de posição N contribui, para cada dia, o
N-ésimo apontamento cronológico daquele dia (ou um valor
zero/transparente se aquele dia tiver menos apontamentos que o dia com
mais). Uma série "base" invisível (o tempo antes do primeiro apontamento
do dia) garante que a pilha visível comece na altura certa, já que uma
barra empilhada sempre começa do zero.

Cor por rótulo **reaproveitada de `mapa.py`** (`cor_por_rotulo`/
`rotulo_classificacao_pulso`) - mesmo código = mesma cor do mapa
operacional, sem inventar paleta nova. Eixo Y em horas (0-24, não
minutos) com `axisLabel.formatter="{value}:00"` - **nunca `JsCode`**
(este projeto nunca usou JsCode, ver ADR-0033/Gestão_OS onde parou de
serializar corretamente; aqui foi possível resolver 100% com templates
nativos do ECharts). O tooltip (`{b}`, trigger `"item"`) mostra o nome
pré-composto em Python de cada segmento (código, descrição, horário de
início-fim, minutos totais) - calculado inteiramente no servidor, embutido
como o campo `name` de cada ponto, nunca depende de lógica em JS.

### 4. Integração nas telas

- **Mapa operacional** (`painel/telas/mapa_operacional.py`): duas
  colunas (`st.columns([2, 1])`), mapa à esquerda, linha do tempo à
  direita - sempre do dia já escolhido no filtro "Data dos pulsos"
  existente (nunca recortado pela faixa de horário, que só afeta os
  pulsos/trajetória do mapa - a linha do tempo mostra o dia inteiro para
  manter o contexto de antes/depois).
- **Visão Geral** (`painel/telas/dashboard.py`): novo expander "Linha do
  tempo do colaborador", com um `st.selectbox` dedicado (dentro do
  conjunto já escolhido no multiselect principal - `_sanitizar_selectbox_state`,
  mesmo padrão de `_sanitizar_multiselect_state` já usado nesta tela)
  compilando **todas as jornadas do colaborador dentro do período já
  filtrado** (não aplica os filtros de categoria/motivo, que são por
  evento individual e não fazem sentido recortando uma linha do tempo
  sequencial).

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: **369 passed** (352 anteriores + 17 novos: 6 em
  `test_consolidacao.py` para `linha_do_tempo`, 6+5 em
  `tests/test_linha_do_tempo.py` (novo) para o recorte por dia e o
  gráfico).
- Inspeção direta da opção ECharts gerada (`json.loads(grafico.dump_options())`)
  confirmando eixo Y (`min=0, max=24, interval=1, formatter="{value}:00"`),
  nome/cor/valor corretos por segmento, e o comportamento correto quando
  dias têm quantidades diferentes de segmentos (posições extras ficam
  com valor 0, invisíveis) - não foi só suposição sobre o pyecharts,
  testado com dado real, incluindo o achado de que o pyecharts omite a
  chave `"name"` quando o valor é string vazia (ajustado no teste, não é
  bug).
- `AppTest` das duas telas (`test_mapa_operacional_painel.py`,
  `test_dashboard_painel.py`) sem exceção, incluindo caminhos com dado
  real (`gerar_jornadas_exemplo`, que tem atividades/pausas de verdade).

## Validação NÃO realizada

- Renderização visual real num navegador (mesma limitação de sempre,
  sandbox sem Chromium/Playwright) - é o primeiro tipo de gráfico novo
  deste projeto usando a técnica de séries genéricas por posição +
  filler invisível; vale conferir visualmente no painel publicado antes
  de considerar "pronto".
- Nenhum teste com uma jornada real de várias semanas/volume alto (a
  técnica de N séries, uma por posição-máxima-de-segmentos-num-dia,
  pode gerar bastante série se um dia tiver muitos apontamentos curtos
  seguidos - não testado em escala).

## Arquivos afetados

- `src/workforce_core/consolidacao.py` (`IntervaloClassificado`,
  `linha_do_tempo`).
- `painel/dados.py` (`SegmentoLinhaDoTempo`, `fatiar_linha_do_tempo_por_dia`).
- `painel/graficos.py` (`grafico_linha_do_tempo`, `_minutos_para_hora_texto`).
- `painel/telas/mapa_operacional.py` (coluna com a linha do tempo ao
  lado do mapa).
- `painel/telas/dashboard.py` (expander "Linha do tempo do colaborador").
- `tests/test_consolidacao.py` (casos novos de `linha_do_tempo`).
- `tests/test_linha_do_tempo.py` (novo).
