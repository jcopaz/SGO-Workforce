# ADR-0047 | Calibração para o horário de Brasília e filtros/marcos do mapa operacional

## Contexto

Pedido do responsável pelo produto em 2026-08-04, depois de testar a
captação real de GPS e o estilo novo do mapa (ADR-0044 a 0046) com dado
real: (1) marcar visualmente onde a jornada começou e terminou, (2)
colorir os pulsos por atividade/pausa/evento e poder filtrar por
atividade, (3) filtrar pulsos por data e faixa de horário, (4) "calibrar
todo o aplicativo para o timezone do Brasil".

O item 4 motivou uma investigação antes de qualquer mudança de código
(nunca se muda tratamento de data/hora de um sistema de apontamento sem
entender o que já existe - CLAUDE.md regra de ouro 3). Achado real,
confirmado com um teste direto do pipeline completo:

- A interface de campo já captura e envia o instante certo:
  `new Date()` captura o relógio do próprio aparelho e `.toISOString()`
  serializa esse instante em UTC (padrão, correto) antes de mandar pro
  backend. O backend (`_str_para_dt`,
  `workforce_storage/serializacao.py::datetime.fromisoformat`) preserva
  esse instante corretamente (Python 3.11+ entende o sufixo "Z", devolve
  um datetime com tzinfo=UTC). **Nada disso mudou neste ADR** - captura e
  armazenamento em UTC continuam sendo a prática certa.
- O bug real estava em dois lugares do **painel**, que exibiam/agrupavam
  esse instante UTC sem converter para o horário de Brasília:
  - `painel/dados.py::formatar_data_hora` mostrava a hora UTC crua - todo
    horário no painel aparecia **3h adiantado** em relação ao horário
    real do colaborador.
  - `workforce_core/consolidacao.py` agrupava eventos por
    `data = inicio.date()` também em UTC - um evento às 22h de Brasília
    (01h UTC do dia seguinte) contava para o **dia errado** em todos os
    agrupamentos por data do painel (evolução diária, contagem por dia).
    Este é o bug mais sério dos dois: não é só exibição, é reclassificação
    de HH para a data errada.
  - O cálculo de **duração** (fim − início) nunca foi afetado - subtração
    de datetimes "aware" no mesmo fuso sempre dá o intervalo real,
    independente de qual fuso está em uso.

## Decisão

### 1. `src/workforce_core/fuso_horario.py` (novo)

`FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")` (stdlib `zoneinfo`, sem
dependência nova para a conversão em si) e `para_horario_brasil(momento)`:
converte um datetime "aware" (com tzinfo) para o horário de Brasília;
devolve `None` para `None`; **devolve um datetime "naive" sem alteração**
- decisão deliberada para não quebrar os testes/dados de exemplo deste
  repositório, que constroem datetimes diretamente em Python
  (`datetime(2026, 1, 1, 8, 0)`) já como "o horário certo", sem passar
  pelo round-trip JS/API que gera datetimes UTC-aware. Reinterpretar um
  naive como UTC teria deslocado esses horários já corretos em 3h.

Adicionada `tzdata` em `requirements.txt` - `zoneinfo` depende do banco
de fusos horários IANA estar disponível no sistema; em containers/imagens
mínimas (Render, Streamlit Cloud) isso nem sempre é garantido, `tzdata`
(pacote PyPI puro-dado, sem compilação) remove essa incerteza.

### 2. Aplicação da conversão - só no limite de apresentação/agrupamento

- `workforce_core/consolidacao.py`: os 4 pontos que faziam
  `algo.inicio.date()` (em `linhas_eventos_classificadas` e
  `linhas_atendimento_falha`) agora fazem
  `para_horario_brasil(algo.inicio).date()` - corrige o bug de
  reclassificação de dia.
- `painel/dados.py::formatar_data_hora`: converte antes de `strftime` -
  corrige o horário 3h adiantado em toda exibição do painel (usa esta
  função como fonte única).
- `painel/mapa.py`: os popups de pulso/cluster usavam `.isoformat()` cru
  (UTC) - agora usam um helper `_horario_legivel` que também converte,
  no mesmo formato amigável de `formatar_data_hora`.

Nenhuma mudança na interface de campo (JS) nem no backend (API/Postgres)
- a captura e o armazenamento em UTC já estavam corretos.

### 3. Marcos de início e fim da jornada (`painel/mapa.py`)

`construir_mapa` ganha `marco_inicio`/`marco_fim` (parâmetros opcionais,
recebem um `PulsoGps` cada) - desenha um pino verde ("Início da jornada")
e um pino vermelho ("Fim da jornada") nas posições do primeiro e do
último pulso da jornada (por `timestamp_dispositivo`, não pela ordem de
chegada). Passados explicitamente pela tela (`mapa_operacional.py`, via
`min`/`max` sobre a lista **completa e não filtrada** de pulsos) para
continuarem representando o início/fim real da jornada mesmo quando o
mapa está mostrando só uma fatia filtrada por atividade/data/horário -
o marco não deveria sumir só porque o filtro atual não inclui aquele
pulso específico.

### 4. Classificação e cor por atividade (`workforce_core/consolidacao.py` + `painel/mapa.py`)

Nova função pura `classificar_instante(jornada, momento)` em
`consolidacao.py`: dado um instante (o `timestamp_dispositivo` de um
pulso), determina o que estava em andamento na jornada naquele momento -
atividade comum, atendimento de falha, pausa (com precedência sobre a
atividade que a contém), evento secundário (deslocamento/espera/apoio)
ou "sem atividade" (jornada aberta, nada específico em andamento).
Reaproveita o mesmo modelo de dados já usado por `linhas_eventos_classificadas`,
sem inventar um conceito novo.

`painel/mapa.py` ganha `rotulo_classificacao_pulso` (rótulo legível -
"Atividade", "Atendimento de falha", "Sem atividade" ou
`rotulo_motivo(codigo, catalogo)` para pausa/evento, mesmo formato
"código - descrição" já usado no resto do painel) e `cor_por_rotulo`
(cor determinística via hash estável do rótulo - `hashlib.md5`, não
`hash()` nativo do Python, que varia entre execuções por
`PYTHONHASHSEED` aleatório). Mesmo rótulo sempre cai na mesma cor, em
qualquer jornada, sem precisar manter um registro global código→cor.
`construir_mapa` ganha `cor_por_pulso` (dict opcional `id do pulso → cor`)
- quando informado, cada `CircleMarker` de pulso usa essa cor no lugar do
amarelo fixo do ADR-0046.

### 5. Filtros na tela (`painel/telas/mapa_operacional.py`)

Depois de carregar os pulsos da jornada selecionada: calcula a
classificação/rótulo de cada um, monta 4 controles lado a lado -
**Atividade** (`st.selectbox`, opções = "Todas as atividades" + os
rótulos distintos presentes), **Data dos pulsos** (`st.date_input`,
valor inicial = data do primeiro pulso em horário de Brasília),
**Horário inicial** e **Horário final** (`st.time_input`, cobrindo o dia
inteiro por padrão - `00:00` a `23:59:59`, ou seja, nada é filtrado até
o usuário estreitar a faixa). Filtra pulsos por data/horário
(`dados.filtrar_pulsos_por_periodo`, nova função pura) e por atividade
(comparação direta contra o rótulo pré-calculado), com a legenda
"N de M pulso(s) exibido(s)" refletindo o filtro. Filtro sem nenhum
pulso correspondente mostra um aviso, sem quebrar a tela (mapa continua
mostrando marcos/malha férrea normalmente).

Mensagem desatualizada da tela também corrigida ("captação periódica
ainda não existe" - já existe desde o ADR-0045, ficou esquecida).

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: **352 passed** (328 anteriores + 24 novos), sem
  regressão.
- Bug de timezone reproduzido e corrigido com um teste direto do
  pipeline completo (JS `.toISOString()` simulado → `fromisoformat` →
  `formatar_data_hora`) antes de escrever a correção - confirma que o
  bug era real, não hipotético.
- Novos testes: `tests/test_fuso_horario.py` (conversão, incluindo o
  caso do evento perto da meia-noite que muda de dia), casos novos em
  `tests/test_consolidacao.py` (bucketing por dia de Brasília +
  `classificar_instante` nos 5 cenários: evento, atividade, pausa com
  precedência, atendimento de falha, fora de qualquer intervalo, limite
  inclusivo), `tests/test_painel.py` (formatar_data_hora com datetime
  aware), `tests/test_mapa.py` (rótulo/cor por classificação, marcos de
  início/fim, cor por pulso sobrescrevendo o amarelo padrão, filtro de
  período incluindo o caso de virada de dia em Brasília), casos novos em
  `tests/test_mapa_operacional_painel.py` (opções do filtro de
  atividade, seleção de uma atividade específica sem quebrar a tela).
- Preview local (`folium.Map.save()`) com dado de exemplo cobrindo as 4
  classificações (atividade, atendimento de falha, pausa, evento
  secundário) para conferir que a classificação produz rótulos
  distintos de verdade antes de subir.

## Validação NÃO realizada

- **Renderização visual real num navegador** - mesma limitação já
  registrada nos ADRs anteriores deste app (sandbox sem
  Chromium/Playwright): não vi os pinos/cores/filtros de verdade
  renderizados. Pedir ao responsável pelo produto para conferir no
  painel publicado.
- **Limitação de ferramenta encontrada e documentada, não corrigida**:
  `streamlit.testing.v1.DateInput.set_value()` não propaga corretamente
  neste ambiente/versão do Streamlit (reproduzido isolado, num script
  mínimo fora deste app - é uma limitação da própria ferramenta de
  teste, não um bug do app). Por isso não há um teste `AppTest` de ponta
  a ponta exercitando literalmente "escolher uma data no widget e ver o
  filtro aplicar" - a correção do filtro em si está coberta por testes
  de função pura (`filtrar_pulsos_por_periodo`), só a interação via
  widget de data não é testável automaticamente hoje.
- Deploy do backend (Render) e do painel (Streamlit Cloud) não
  confirmado neste ambiente - mesma ressalva de sempre; `tzdata` só
  chega aos ambientes de produção no próximo build a partir de
  `requirements.txt`.

## Deliberadamente fora deste ADR

- Reprocessar/corrigir dados **já persistidos** antes desta correção
  (jornadas cujo HH já foi contado no dia UTC errado) - é uma decisão de
  remediação de dados, não uma decisão técnica; fica para o responsável
  pelo produto decidir se e como isso deve ser corrigido retroativamente.
- Cor fixa/registrada globalmente por código (ex.: "Refeição sempre
  laranja em qualquer relatório do sistema, não só no mapa") - a
  atribuição por hash é estável por rótulo mas não foi comparada com
  nenhuma paleta pré-definida em outro lugar do painel.

## Arquivos afetados

- `src/workforce_core/fuso_horario.py` (novo).
- `src/workforce_core/__init__.py` (exporta `fuso_horario`).
- `src/workforce_core/consolidacao.py` (correção de bucketing por dia +
  `classificar_instante`/`ClassificacaoInstante`).
- `painel/dados.py` (`formatar_data_hora` corrigida,
  `filtrar_pulsos_por_periodo` novo).
- `painel/mapa.py` (`_horario_legivel`, marcos de início/fim,
  `rotulo_classificacao_pulso`, `cor_por_rotulo`, `cor_por_pulso` em
  `construir_mapa`).
- `painel/telas/mapa_operacional.py` (filtros de atividade/data/horário,
  mensagem desatualizada corrigida).
- `requirements.txt` (`tzdata`).
- `tests/test_fuso_horario.py` (novo), `tests/test_consolidacao.py`,
  `tests/test_painel.py`, `tests/test_mapa.py`,
  `tests/test_mapa_operacional_painel.py` (casos novos).
