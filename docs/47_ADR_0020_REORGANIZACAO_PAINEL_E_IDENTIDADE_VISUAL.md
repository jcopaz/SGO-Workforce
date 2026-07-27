# ADR-0020 | Reorganização do painel (IA) e identidade visual do SGO

## Contexto

O responsável pelo produto revisou o painel (depois do ADR-0018/0019) e
apontou dois problemas de usabilidade: (1) 5 páginas soltas sem
agrupamento, sem entender para que servem "Exportações" e "Capacidade
PCM"; (2) pediu que o visual (sidebar, logo) fosse idêntico ao do SGO
(Gestão_OS), para facilitar integração futura.

Regras que ele deu para a reorganização: "tudo que for inserção ou
exportação de dados fica em página separada" e "tudo que for informação
geral aplicada a todos os usuários vira Configurações". Decisão dele
(pergunta feita antes deste ADR): Catálogo → **Configurações**,
Exportações → **Dados**. Por extensão da própria regra, **Capacidade
PCM** — que não é inserção/exportação nem configuração geral, é uma
visão de análise/simulação — entra em **Análise de Dados** junto com o
dashboard principal e o Mapa Operacional.

## Decisão

### 1. `st.navigation`/`st.Page` com seções reais

O Streamlit instalado (1.57.0) suporta `st.navigation(dict)` com seções
nomeadas no menu lateral desde a versão 1.36 — não foi preciso simular
agrupamento com `st.expander`. `painel/app.py` virou um launcher fino
(`st.set_page_config` → `aplicar_estilo_sgo()` → `st.logo(...)` →
`st.navigation({...}).run()`); todo o conteúdo das telas foi movido para
`painel/telas/` (renomeado de `painel/pages/` — esse nome específico
aciona a descoberta automática antiga do Streamlit, que conflita com
`st.navigation` explícito).

Mapeamento:
- **Análise de Dados**: `telas/dashboard.py` (era o conteúdo de
  `app.py`), `telas/mapa_operacional.py`, `telas/capacidade_pcm.py`.
- **Dados**: `telas/dados_exportacoes.py`.
- **Configurações**: `telas/configuracoes_catalogo.py`.

Cada tela perdeu sua própria chamada `st.set_page_config(...)` (só pode
haver uma por app, agora centralizada em `app.py`) — nenhuma outra lógica
mudou. `st.session_state` continua compartilhado normalmente entre todas
as telas (as chaves `painel_api_url`/`painel_api_token` usadas por
Exportações e Catálogo continuam funcionando sem alteração). O
Streamlit Cloud não precisa de nenhuma reconfiguração — o "Main file
path" continua `painel/app.py`.

### 2. Identidade visual copiada do SGO (`painel/estilo.py`, novo)

Pesquisa feita por leitura de código do `Gestão_OS/app.py` (nenhum
código do Gestão_OS foi importado ou executado — só a paleta de cores, os
blocos de CSS e o arquivo de logo foram reaproveitados, que são ativos
visuais da mesma empresa, não lógica de negócio proprietária):
- Sidebar escura (`#0F172A`), texto claro, mesmos gradientes de botão
  (`kind="secondary"` azul, `kind="primary"` vermelho) e mesmas classes
  de card de KPI (`.kpi-header-card`/`.kpi-border-*`/`.badge-*`) do SGO,
  reaproveitadas literalmente nos mesmos seletores CSS.
- `logo_mrs.png` copiado de `Gestão_OS/logo_mrs.png` para
  `painel/assets/logo_mrs.png`, exibido via `st.logo()` (API nativa do
  Streamlit para logo + `st.navigation`, mais robusta que o
  `st.sidebar.image()` que o SGO usa, porque já se posiciona corretamente
  junto com o menu de seções).
- Dashboard (`telas/dashboard.py`): os 4 `st.metric` viraram cards HTML
  no estilo `.kpi-header-card` do SGO (função `_cartao_kpi`), coloridos
  por sentido (azul=jornadas, cinza=bruto, verde=classificado,
  vermelho=não classificado).

**Ressalva registrada, não escondida**: o SGO usa um `st.radio`
customizado (CSS escondendo a bolinha nativa, virando "pill menu") para
o menu lateral, porque foi escrito antes de `st.navigation` existir. O
Workforce usa `st.navigation` nativo — os seletores CSS para estilizar
esse menu (`[data-testid="stSidebarNav"]`, `[data-testid=
"stSidebarNavLink"]`) são uma adaptação best-effort, não uma cópia
literal, porque a estrutura HTML gerada é diferente. Cores machadas, mas
o comportamento exato de hover/seleção precisa de conferência visual
manual.

## Fora de escopo desta sessão

- Hierarquia organizacional (coordenação/gerência/gerência geral) e
  Atendimento de Falha completo (D1-D4 do roteiro combinado) — próximos
  incrementos, por tamanho.
- Réplica da tela de login "glassmorphism" do SGO — não há login no
  Workforce ainda (ADR-0018).

## Validação de qualidade realizada

- `python -m py_compile` em `painel/app.py`, `painel/estilo.py` e todos
  os arquivos de `painel/telas/`.
- `pytest` completo: 197/197 (nenhuma lógica de dados mudou, só
  organização de arquivos e apresentação).
- `streamlit run painel/app.py` localmente: processo sobe, `/_stcore/health`
  responde "ok" (confirma que não há erro fatal de import/sintaxe que
  impeça o processo de subir).

## Validação NÃO realizada

Mesma limitação de sempre (sem navegador neste ambiente): a execução da
página por sessão de navegador (onde o script de cada tela realmente
roda) não foi exercitada. Isso significa que:
- A navegação entre seções, o logo e o CSS do menu lateral **não foram
  vistos visualmente**.
- Não foi confirmado que `st.Page("telas/dashboard.py", ...)` resolve o
  caminho relativo corretamente em tempo de execução real (só validado
  por leitura da documentação do Streamlit sobre `st.navigation`).

Fica pendente `streamlit run painel/app.py` manual, comparando visualmente
com o Gestão_OS, antes de considerar a identidade visual finalizada.

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
- Revisão pendente: conferência visual manual (navegador real).
