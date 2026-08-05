# ADR-0049 | Mapa operacional: camadas sempre visíveis e fluidez (menos rerun)

## Contexto

Feedback do responsável pelo produto em 2026-08-04, testando o mapa
operacional depois do ADR-0046/0047/0048: o controle de camadas do
Folium (`cartodbpositron`, "Malha ferrea MRS", "Início e fim", "Pulsos
brutos", "Trajetória simplificada", todos como checkboxes) estava "pouco
interativo" - a maioria das opções não representava uma escolha real:

- A malha férrea é referência fixa - não faz sentido esconder.
- Início/fim da jornada é âncora fixa - idem.
- Pulsos brutos já são filtráveis por atividade/data/horário nos widgets
  da própria tela (ADR-0047) - um segundo toggle no mapa para a mesma
  coisa é redundante.
- O item "cartodbpositron" no controle é o tile base sendo listado como
  se fosse uma "escolha" de mapa, quando só existe um tile - zero valor.
- A única camada que faz sentido continuar opcional é a trajetória
  traçada (uma linha conectando os pontos pode poluir visualmente quando
  já há muitos pulsos/marcadores desenhados).

Pedido em paralelo, mesma mensagem: "pense em como deixar a aplicação
fluida sem ter excesso de rerun visto a lentidão de processamento do
Streamlit" - o Streamlit reexecuta o script inteiro a cada interação de
widget; a tela tinha 7 widgets (atividade, data, 2 horários, 3 sliders)
mais o próprio mapa (`st_folium`, que por padrão também dispara rerun a
cada pan/zoom/clique) sem nenhum cache nas 2 chamadas de rede
(`carregar_jornadas_via_api`/`carregar_pulsos_via_api`, timeout de 60s
por causa do cold start do Render free tier) - cada ajuste de slider
refazia as duas chamadas de API do zero.

## Decisão

### 1. `painel/mapa.py` - camadas sempre visíveis, sem `FeatureGroup`/toggle

Malha férrea, marcos de início/fim, pulsos brutos e clusters de
permanência agora são desenhados **direto no mapa** (`.add_to(mapa)`),
não mais dentro de um `folium.FeatureGroup` nomeado - não aparecem mais
no `LayerControl`. Só a trajetória simplificada continua num
`FeatureGroup` com controle (renomeada de "Trajetoria simplificada" para
"Traçar trajetória", texto pedido pelo responsável pelo produto) -
`LayerControl` só é adicionado ao mapa quando essa camada existe (2+
pontos simplificáveis), já que é a única coisa que ele lista.

O tile base (`cartodbpositron`) deixou de ser passado via
`folium.Map(tiles=...)` (que sempre aparece no controle como
"base layer", mesmo sendo a única opção) - agora é
`folium.Map(tiles=None)` + `folium.TileLayer(tiles=..., control=False)`
explícito, removendo esse item vazio do controle.

`mostrar_pulsos_brutos` continua existindo como parâmetro de
`construir_mapa` (flexibilidade programática), só deixou de estar
amarrado a um checkbox visível no mapa.

### 2. `painel/telas/mapa_operacional.py` - cache das chamadas de API

Duas funções pequenas decoradas com `st.cache_data(ttl=60, show_spinner=False)`
(`_carregar_jornadas_cache`/`_carregar_pulsos_cache`), envolvendo
`dados.carregar_jornadas_via_api`/`carregar_pulsos_via_api` sem alterá-las -
`painel/dados.py` continua deliberadamente livre de Streamlit (testável
com pytest puro, ver docstring do módulo), então os wrappers cacheados
ficam na tela, não no módulo de dados. TTL de 60s (mesmo número do
timeout de rede - o dado não muda mais rápido que isso na prática).
Ajustar qualquer um dos 7 widgets da tela agora reaproveita os dados já
carregados em vez de rebater no backend a cada interação.

O botão "🔄 Sincronizar dados" (que antes só mostrava um toast, sem
nenhum efeito real) agora limpa esse cache explicitamente
(`_carregar_jornadas_cache.clear()`/`_carregar_pulsos_cache.clear()`)
antes do toast - um pedido explícito de sincronização nunca fica preso
atrás do TTL de 60s.

`st_folium(..., returned_objects=[])` - o retorno de `st_folium` (bounds,
último clique, etc.) nunca era lido em nenhum lugar da tela; por padrão,
`st_folium` reexecuta o script Streamlit inteiro a cada interação com o
mapa (pan, zoom, clique). `returned_objects=[]` documentado
explicitamente pela biblioteca como "para quando você só quer que o app
rode de novo em certas condições, não toda vez que o usuário interage
com o mapa" - provavelmente a maior causa isolada de lentidão percebida,
já que reexecutar o script reconstrói o mapa inteiro do zero a cada
movimento.

## Validação de qualidade realizada

- `python -m py_compile` nos 2 módulos tocados: OK.
- `pytest` completo: 352 passed, sem regressão.
- Bug real de teste encontrado e corrigido durante a validação: o cache
  do `st.cache_data` é por processo, não por instância de `AppTest` - os
  testes de ponta a ponta reutilizam a mesma URL/token fake
  (`_preparar_secrets_de_teste`), então sem limpar o cache entre testes
  um teste vazava jornada/pulso em cache pro próximo (2 testes passavam
  "por acidente" com dado errado, silenciosamente, até a asserção
  específica falhar). Corrigido com uma fixture `autouse` que chama
  `st.cache_data.clear()` antes de cada teste.
- Inspeção direta do HTML gerado (`mapa.get_root().render()`) confirmando
  que o `LayerControl` só lista "Traçar trajetória" (`base_layers` vazio,
  `overlays` com uma entrada só) - não foi só suposição sobre o
  comportamento do Folium, foi conferido byte a byte.
- Achado colateral durante a validação: nomes de camada com acento
  (“Traçar trajetória”) são serializados pelo Folium via `json.dumps`
  (`ensure_ascii=True` por padrão) dentro do `<script>` - aparecem como
  `ç`/`ó` literais no HTML, não o caractere acentuado em si.
  Testes que verificam esse texto usam um helper `_contido()` (mesmo
  padrão já usado em `test_painel.py` para o pyecharts) que checa as duas
  formas.

## Validação NÃO realizada

- Sensação real de fluidez num navegador de verdade (sandbox sem
  Chromium/Playwright, mesma limitação de sempre) - pedir ao responsável
  pelo produto para confirmar se a diferença é perceptível no painel
  publicado.

## Arquivos afetados

- `painel/mapa.py` (camadas sempre visíveis, tile base sem controle,
  renomeação da trajetória).
- `painel/telas/mapa_operacional.py` (cache das chamadas de API, botão
  "Sincronizar dados" limpa cache de verdade, `st_folium` sem
  `returned_objects`).
- `tests/test_mapa.py` (asserções atualizadas para as camadas sempre
  visíveis, helper `_contido` para nomes acentuados).
- `tests/test_mapa_operacional_painel.py` (fixture `autouse` limpando o
  cache do Streamlit entre testes).
