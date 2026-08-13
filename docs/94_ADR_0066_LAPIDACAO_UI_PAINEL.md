# ADR-0066 | Lapidação de UI do painel: hierarquia, telas quebradas e tema visual

## Contexto

O responsável do produto pediu, em 2026-08-12, uma revisão completa da
interface do painel Streamlit ("dê uma boa lapidada... algumas abas as
informações estão poluídas e os gráficos um pouco bizarros"), pedindo
para eu pensar como especialista de UI Design. Perguntado quais telas,
respondeu "todas" (Visão Geral, Falhas, Mapa Operacional, Capacidade
PCM/outras) - ou seja, o painel inteiro.

Uma primeira tentativa de auditoria via agente em segundo plano falhou
por limite de uso da conta (não foi contornado - a auditoria foi refeita
lendo o código diretamente, sem subagente). Não há navegador disponível
neste ambiente de desenvolvimento para validar visualmente o resultado -
o diagnóstico e a correção são baseados em leitura de código (estrutura
de `st.expander`/`st.tabs`, fonte de dados, CSS), não em captura de tela
real do app rodando.

## Diagnóstico (lendo as 6 telas + `estilo.py` por completo)

1. **Toda tela de gráficos usava `st.expander(..., expanded=True)`** -
   ou seja, os expansores nunca escondiam nada. Dashboard tinha 9 seções
   sempre abertas (340 a 620px de altura cada); Falhas tinha 5. Resultado:
   uma rolagem enorme sem hierarquia nenhuma, tudo "igualmente
   importante" porque tudo ficava visível ao mesmo tempo.
2. **Duas telas (Capacidade PCM, Exportações) pediam um caminho de pasta
   no disco** (`st.text_input("Diretório de jornadas persistidas")`) -
   nunca funcionou no Streamlit Cloud (sem disco persistente lá). Ficaram
   pra trás quando as outras 3 telas migraram pra buscar dados da API
   (ADR-0041) - bug real, não só estética.
3. **A tela de Configurações mostrava a URL e o token do backend em
   campos de texto editáveis**, pré-preenchidos mas visíveis - contradiz
   a decisão de segurança já tomada nas outras telas ("credenciais vêm
   só de `st.secrets`, nunca digitadas na tela").
4. **Cartões de KPI escuros (`#1A202C`) boiando num fundo branco.** O CSS
   escureceu só a sidebar (identidade visual copiada do SGO,
   deliberadamente), mas os cartões de KPI do conteúdo principal
   herdaram o estilo escuro do Gestão_OS original, criando duas telas
   com "temperatura" visual diferente coladas uma na outra.
5. **Mapa Operacional expunha 3 sliders de calibração interna** com o
   próprio rótulo avisando "não é valor oficial" - parâmetro de afinação
   sem lugar numa tela pensada pra gestor.
6. Boilerplate repetido (filtros, cartão de KPI, tratamento de erro) nas
   6 telas - sem lib de componente compartilhada, mas fora de escopo
   desta rodada (risco maior, mexe em todas as telas de uma vez por
   motivo estrutural, não visual).

## Decisão

### 1. Capacidade PCM e Exportações migradas pra API (mesmo padrão das outras 3 telas)

`carregar_jornadas`/`carregar_pulsos` (arquivo local) trocados por
`carregar_jornadas_via_api`/`carregar_pulsos_via_api`, com o mesmo bloco
de `st.secrets`/`st.error`/`st.stop()` já usado em `dashboard.py`. Em
Exportações, os pulsos agora são buscados por jornada num laço (a API só
devolve pulsos de uma jornada por vez) e agregados tanto na lista plana
(CSV/XLSX) quanto no dicionário por jornada (GeoJSON de trajetórias) -
uma falha de rede buscando pulsos de UMA jornada não trava a exportação
inteira (best-effort, mesmo espírito do resto do painel).

### 2. Configurações não expõe mais URL/token editáveis

Mesmo padrão `st.secrets` + `st.error`/`st.stop()` das outras telas -
sem campo de texto pra credencial nenhuma.

### 3. Cartões de KPI reestilizados pra combinar com o conteúdo principal claro

`painel/estilo.py`: fundo branco, sombra suave, texto escuro - mantendo
a borda lateral colorida (único elemento que já funcionava bem como
codificação visual por categoria/status).

### 4. Dashboard e Falhas: expanders sempre abertos viram abas agrupadas por tema

- **Dashboard**: 9 seções → 4 abas (Visão geral, Por colaborador,
  Tendências, Fluxo).
- **Falhas**: 5 seções → 2 abas (Panorama, Evolução e reincidência).

Só uma aba renderiza gráficos por vez - a mesma informação continua
disponível, só não fica toda entregue de uma vez na primeira rolagem.

### 5. Mapa Operacional: sliders técnicos movidos pra expander recolhido

"Distância mínima de simplificação", "Raio de cluster" e "Tempo mínimo
de permanência" saem da área principal de filtros e entram num
`st.expander("⚙️ Configurações avançadas do mapa...")`, recolhido por
padrão - continuam ajustáveis pra quem precisar, sem competir com os
filtros de uso comum (colaborador/jornada/atividade/data/horário).

## Consequências e riscos aceitos

- **Nenhuma validação visual real** - sem navegador neste ambiente, a
  correção é inferida da estrutura do código (menos seções sempre
  abertas, fonte de dados corrigida, cor recalculada), não confirmada
  visualmente. Pendente o responsável do produto testar ao vivo e
  reportar o que ainda incomoda.
- **Boilerplate repetido entre as 6 telas não foi extraído pra
  componente compartilhado** - risco maior (mexe em todas as telas por
  um motivo estrutural, não visual), fora do escopo desta rodada.
- **Testes automatizados (`AppTest`) existentes para
  Dashboard/Falhas/Mapa/Configurações passaram sem alteração** - nenhum
  deles verifica rótulo exato de expander/aba, então a reestruturação de
  `st.expander` pra `st.tabs` não quebrou nenhuma asserção existente
  (bom sinal, mas também significa que esses testes não cobrem a
  hierarquia visual em si).
- **Capacidade PCM e Exportações não têm teste `AppTest` cobrindo a tela**
  (só os módulos de domínio `workforce_core.pcm`/`workforce_export`) -
  a correção da fonte de dados nessas duas telas foi validada só por
  `py_compile` e revisão manual do código, sem teste automatizado
  específico da tela.

## Validação realizada

- `python -m py_compile` em todas as 6 telas + `estilo.py`: OK.
- `pytest` completo: 435 passed (nenhum teste novo - reestruturação de
  UI sem mudança de contrato/dado, cobertura existente já validava as
  funções de domínio/dados por trás de cada tela).

## Validação NÃO realizada

- Teste visual real do painel num navegador - depende do responsável do
  produto abrir `sgoworkforce.streamlit.app` (ou rodar local) e conferir
  se a hierarquia/tema ficou como esperado.

## Arquivos afetados

- `painel/telas/dashboard.py` (9 expanders → 4 abas).
- `painel/telas/falhas.py` (5 expanders → 2 abas).
- `painel/telas/mapa_operacional.py` (sliders técnicos → expander
  recolhido).
- `painel/telas/capacidade_pcm.py` (fonte de dados: pasta local → API).
- `painel/telas/dados_exportacoes.py` (fonte de dados: pasta local →
  API; slider de simplificação → expander recolhido).
- `painel/telas/configuracoes_catalogo.py` (credenciais: campos visíveis
  → `st.secrets`).
- `painel/estilo.py` (cartões de KPI: escuro → claro).

## Data e responsáveis

- Data de registro: 2026-08-12.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
