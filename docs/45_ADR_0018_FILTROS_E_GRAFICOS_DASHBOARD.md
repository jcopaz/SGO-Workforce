# ADR-0018 | Filtros, novos gráficos e correção de classificação no painel

## Contexto

Depois do primeiro teste real de ponta a ponta (interface de campo →
backend → painel, ver ADR-0017), o responsável pelo produto revisou o
dashboard e apontou vários problemas/pedidos de uma vez:

1. O gráfico de categoria mostrava uma fatia grande "sem classificação".
2. Faltavam filtros acima dos gráficos: colaborador, período, categoria,
   motivo/justificativa.
3. Faltavam mais gráficos para uma "visão total e classificação" dos
   dados.
4. A tabela "Jornadas carregadas" mostrava o `id` (UUID técnico, sem
   utilidade para o usuário) em vez de só colaborador/início/fim.
5. Data/hora deveriam aparecer em `dd/mm/aaaa hh:mm:ss`, no painel e na
   interface de campo, de forma consistente.

## Decisão

### 1. Causa raiz do "sem classificação" (item 1)

`painel/dados.py::montar_resumo` usava `catalogo_padrao()` (motivos de
teste como `PAUSA_TESTE`) para classificar **qualquer** jornada, inclusive
as sincronizadas de verdade pela interface de campo — que usa os códigos
reais do Relatório 1 (`EE02`, `EE07`, `EE11`, `EE21`, `EE23`, ver
ADR-0014). Esses códigos não existiam em `catalogo_padrao()`, então toda
pausa real caía no bucket `None` ("sem categoria conhecida").

Correção: nova `catalogo_completo()`
(`src/workforce_core/catalogo.py`) — união de `catalogo_padrao()` e
`catalogo_relatorio_1_manutencao()` — usada como padrão em
`montar_resumo()`. Isso classifica corretamente tanto dados de exemplo
(que usam os códigos `*_TESTE`) quanto dados reais (códigos `EE0x`), sem
exigir que quem gera cada tipo de dado saiba do catálogo do outro.

### 2. Filtros e mais gráficos (itens 2 e 3)

Nova estrutura `LinhaEvento` e função `linhas_eventos_classificadas()`
(`src/workforce_core/consolidacao.py`, testada em
`tests/test_consolidacao.py`) — achata as jornadas em uma linha por
atividade/pausa/evento secundário encerrado, cada uma com colaborador,
data, categoria e motivo. É a mesma classificação de `resumo_por_categoria`
(nenhuma regra nova inventada), só que sem agregar, para permitir filtrar
antes de somar.

Dois níveis de filtro no painel (`painel/app.py`):
- **Colaborador + período**: filtram quais **jornadas** entram no
  cálculo — afeta os cards de HH bruto/classificado/não-classificado
  (`ResumoConsolidado`, que só faz sentido por jornada inteira).
- **Categoria + motivo/justificativa**: filtram quais **linhas de
  evento** entram nos gráficos de detalhamento (incluindo o próprio
  gráfico "HH por categoria" — selecionar/deselecionar categorias nele
  também é uma forma válida de filtro, como em ferramentas de BI comuns).

Três gráficos novos em `painel/graficos.py` (grounded em
`docs/12_DASHBOARDS_ECHARTS.md`, aba "Distribuição de HH", que já
recomendava "série temporal" e trocar por comparação de detalhamento —
nenhum indicador foi inventado, só implementado o que a doc já previa):
- `grafico_evolucao_diaria`: linha de HH total por dia.
- `grafico_hh_por_colaborador`: barras empilhadas por colaborador x
  categoria.
- `grafico_motivos_treemap`: treemap de HH por motivo/justificativa.

**Fora de escopo desta sessão** (docs/12 continua com pendências): cards
de "HH produtivo/improdutivo" (Resumo), Sankey da jornada, heatmap dia x
hora e sunburst sistema>ativo>sintoma. Os cards de produtivo/improdutivo
em especial continuam bloqueados por decisão de negócio pendente —
`ClassificacaoHH` é `NAO_DEFINIDO` para todo o catálogo (nenhuma entrada
foi validada como produtiva/improdutiva ainda, ver `catalogo.py` e
`docs/23_DECISOES_PENDENTES.md`).

### 3. Tabela sem `id` (item 4)

`painel/app.py`, tabela "Jornadas carregadas": colunas reduzidas a
Colaborador/Estado/Início/Fim.

### 4. Formato de data/hora (item 5)

`formatar_data_hora()` nova em `painel/dados.py` (`dd/mm/aaaa hh:mm:ss`,
`strftime`, nunca fonte de cálculo) usada em `painel/app.py` e
`painel/pages/1_Mapa_Operacional.py`. Do lado da interface de campo,
`interface_campo/js/app.js::formatoHora` foi reescrita para o mesmo
formato (construído manualmente com `padStart`, não
`toLocaleString`, para não variar por navegador/locale) — mostrar a data
completa (não só a hora) importa desde que o simulador de tempo permite
testar jornadas que atravessam dias (ADR-0016).

**Decisão consciente de não uniformizar**: as exportações CSV/XLSX
(`src/workforce_export/`) continuam em ISO 8601. Formato de interoperabilidade
de dados (para quem consome o arquivo programaticamente) é uma decisão
diferente de formato de exibição em tela — mudar isso silenciosamente
poderia quebrar reconciliação com quem já processa essas exportações, e
"layout oficial de colunas" já é uma decisão pendente explícita do
ADR-0011. Se o responsável pelo produto quiser esse formato também nas
exportações, é uma decisão separada a confirmar.

## Login (decisão relacionada, não implementada nesta sessão)

O responsável pelo produto também pediu login compartilhado com o SGO
(Gestão_OS). Investigação encontrada: o SGO usa login próprio (hash
SHA-256 sem salt, sem OAuth/SSO), embutido no `app.py` monolítico, contra
uma tabela `usuarios` num Postgres (Neon) com `perfil`/`escopo`/`governanca`
já funcionando em produção — mas sem nenhum serviço de identidade
separado reutilizável, e sem módulo de login isolado (copiável). Reusar a
mesma tabela de usuários já hoje criaria uma dependência técnica do
Workforce num banco de produção de terceiros, adiantando a Fase 5
(Integração SGO) do roadmap e contrariando a regra de ouro "não acople o
Workforce ao SGO durante o MVP" — `docs/17_SEGURANCA_GOVERNANCA.md` já
previa "API key/token no MVP" e "SSO/AD" como item futuro. **Decisão do
responsável pelo produto: adiar login por enquanto**, mantendo só o token
de sincronização já existente.

## Validação de qualidade realizada

- `tests/test_consolidacao.py`: 3 novos testes de `linhas_eventos_classificadas`.
- `tests/test_painel.py`: novos testes de `formatar_data_hora`,
  `montar_linhas_eventos`/`agrupar_duracao_por_categoria` e dos 3 gráficos
  novos (HTML autocontido, sem CDN).
- `pytest` completo: 187/187 testes.
- `node --test tests/js`: 30/30 testes (sem regressão no formato de data
  do app de campo).

## Validação NÃO realizada

Mesma limitação já registrada nos ADRs anteriores: os filtros e gráficos
novos não foram clicados num navegador real (Streamlit não é testável por
pytest fora do próprio runtime, ver ADR-0009) — só validados pelos testes
unitários das funções de agregação/gráfico. Pendente smoke test manual
(`streamlit run painel/app.py`) antes de considerar esta tela pronta para
uso operacional.

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
- Revisão pendente: smoke test manual do painel; decisões de negócio já
  citadas em `docs/23_DECISOES_PENDENTES.md` (catálogo oficial,
  classificação produtiva/improdutiva) continuam bloqueando os
  indicadores de "HH produtivo" do `docs/12_DASHBOARDS_ECHARTS.md`.
