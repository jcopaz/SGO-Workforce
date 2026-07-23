# ADR-0009 | Dashboard ECharts via pyecharts em vez de streamlit-echarts (Incremento 9)

## Contexto

`CLAUDE.md` fixa como regra de ouro: "Use ECharts para dashboards e
Folium/Leaflet para mapa operacional, salvo decisão arquitetural posterior
documentada." `Requirements.txt` já listava `streamlit-echarts` como o
pacote previsto para essa integração. `docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`
seção 15.3 ("Antes do Incremento 9: dashboards") lista como pendente:
indicadores obrigatórios por perfil, filtros padrão, metas e referências,
limites de detalhamento individual, periodicidade de atualização.

Ao tentar instalar as dependências neste ambiente
(`python -m pip install streamlit streamlit-echarts pandas`), o Streamlit
instalado foi a versão 1.57.0 (a mais recente compatível disponível — não
é possível fixar em versões mais antigas como `1.38` porque elas dependem
de uma versão do Pillow sem wheel pré-compilado para Python 3.14, que é a
versão de Python deste ambiente, e a compilação a partir do código-fonte
falha por falta de cabeçalhos de zlib no Windows). Nessa versão do
Streamlit, `streamlit_echarts` (testado nas versões 0.6.0 e 0.7.0, a mais
recente publicada) falha ao ser importado com:

```text
streamlit.errors.StreamlitAPIException: Component 'streamlit-echarts.streamlit_echarts'
must be declared in pyproject.toml with asset_dir to use file-backed js.
```

Isso indica que o Streamlit introduziu um novo sistema de componentes
(`st.components.v2`) que exige configuração adicional não suportada por
nenhuma versão publicada de `streamlit-echarts` até a data desta sessão —
uma incompatibilidade real de ecossistema, não uma escolha de design.

## Decisão

Substituir `streamlit-echarts` por **pyecharts** (`>=2,<3`), que gera a
`option` JSON do Apache ECharts em Python puro, sem depender de nenhum
componente customizado do Streamlit. O gráfico é renderizado para HTML
autocontido (`grafico.render_embed()`) e exibido via
`streamlit.components.v1.html()` — a API clássica de embutir HTML/iframe,
que não tem relação com o sistema de componentes quebrado.

Isso continua sendo, literalmente, "usar ECharts para dashboards" — é o
mesmo Apache ECharts renderizado no navegador, apenas com um caminho de
integração diferente do que o `Requirements.txt` prescrevia originalmente.
Conforme a própria regra do CLAUDE.md permite ("salvo decisão
arquitetural posterior documentada"), esta troca está documentada aqui.

### JS do ECharts embutido localmente, sem CDN

`pyecharts.render_embed()` gera, por padrão, uma tag
`<script src="https://assets.pyecharts.org/assets/v6/echarts.min.js">`
apontando para um CDN público, sem `integrity`/`crossorigin` — um risco de
supply chain (comprometimento do CDN) sinalizado durante esta sessão.
`painel/graficos.py:renderizar_embutido` baixa o `echarts.min.js` uma
única vez para `painel/assets/echarts.min.js` (versão 5.x, via
`cdn.jsdelivr.net`, usada apenas para obter o arquivo nesta sessão de
desenvolvimento) e o embute inline no HTML, substituindo a tag de CDN.
Se o arquivo local não existir, ou se o HTML gerado pelo pyecharts não
contiver a tag esperada (ex.: após uma atualização de versão do
pyecharts), a função falha explicitamente (`FileNotFoundError`/
`RuntimeError`) em vez de deixar passar uma dependência de CDN sem
integridade sem ninguém perceber — fail closed, `CLAUDE.md` regra de ouro
9.

## Escopo entregue

- `painel/dados.py`: `carregar_jornadas` (usa
  `workforce_storage.RepositorioJornadaArquivo`, nunca apaga arquivo
  corrompido — reporta), `montar_resumo` (usa
  `workforce_core.consolidacao.resumo_consolidado`, mesma fonte de cálculo
  de todo o resto do sistema), `formatar_horas`, e
  `gerar_jornadas_exemplo` (dados fabricados, exclusivamente para
  demonstração/teste do painel sem depender de dados reais).
- `painel/graficos.py`: `grafico_hh_por_categoria` (barras),
  `grafico_distribuicao_pizza` (pizza), `renderizar_embutido`.
- `painel/app.py`: entrypoint Streamlit. Widget de diretório usa
  `st.session_state` via `key=` (CLAUDE.md regra de ouro 10: não esconder
  widget stateful entre reruns). Mostra aviso de piloto técnico de forma
  permanente na tela.

## Validação realizada

- `tests/test_painel.py` (9 testes): `dados.py` e `graficos.py` são
  puros o suficiente para testar com pytest, sem depender do runtime do
  Streamlit — cobrem formatação, carregamento com/sem erro de arquivo,
  geração de dados de exemplo, resumo consolidado, e renderização de
  gráfico autocontida (sem CDN), incluindo a falha explícita quando o
  asset local está ausente.
- **Smoke test real do servidor**: `streamlit run painel/app.py
  --server.headless true` iniciado de fato, com `curl` confirmando HTTP
  200 tanto na página raiz quanto em `/_stcore/health`, primeiro com o
  diretório de dados vazio (caminho "sem dados") e depois com dados de
  exemplo pré-gerados no diretório padrão (exercitando o caminho completo:
  métricas, os dois gráficos ECharts, e a tabela) — em ambos os casos sem
  nenhum traceback no log do servidor.

## Validação NÃO realizada

**Não foi possível abrir o painel em um navegador real** para confirmar
visualmente que os gráficos renderizam corretamente — mesma limitação de
ambiente já registrada no ADR-0004 (sem `chromium-cli`/Playwright
disponíveis, sem conseguir instalá-los). O smoke test confirma que o
servidor Python executa sem exceção e entrega HTML; não confirma a
renderização client-side do ECharts embutido. Isso precisa ser validado
manualmente por alguém com acesso a um navegador antes de qualquer
demonstração real.

## Deliberadamente fora deste incremento

- **Quais indicadores são obrigatórios**, filtros padrão, metas/referências,
  limites de detalhamento individual e periodicidade de atualização:
  todos explicitamente pendentes (seção 15.3) — o painel mostra apenas o
  que já é calculável (HH bruto/classificado/não classificado e por
  categoria), não uma lista validada de indicadores de produto.
  `dados_locais/jornadas` é só um caminho padrão de conveniência — não há
  fonte de dados oficial definida.
- **Autenticação e perfis de acesso**: o painel não tem login; qualquer
  pessoa com acesso ao processo Streamlit vê todos os dados carregados.
- **Filtro por colaborador, equipe, período, coordenação**: não
  implementado — o painel carrega tudo que encontra no diretório indicado.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (indicadores oficiais,
  filtros, metas) e teste manual em navegador real antes de qualquer
  demonstração.
