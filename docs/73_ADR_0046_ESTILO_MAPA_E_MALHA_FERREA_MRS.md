# ADR-0046 | Estilo visual do mapa operacional e camada da malha férrea da MRS

## Contexto

Pedido direto do responsável pelo produto em 2026-08-04, depois de testar
o mapa operacional com a captação real de GPS (ADR-0044/0045) já em
produção: deixar o mapa "visualmente mais bonito", priorizando a leitura
das ruas e do traçado ferroviário, com uma paleta específica para os
pulsos brutos e a trajetória, e sobrepondo a malha férrea da MRS a partir
de um KML já existente na raiz do repositório (`malha_mrs.kml`, exportado
do Google Earth - 26 trechos de linha, ~15.700 pontos, nunca versionado
até este ADR).

## Decisão

### 1. `painel/malha_ferrea.py` (novo) - leitura do KML

Parser mínimo via `defusedxml.ElementTree` (nunca `xml.etree.ElementTree`
puro - vulnerável a XXE/entity expansion mesmo para um arquivo "confiável"
do próprio repositório, ver
https://docs.python.org/3/library/xml.html#xml-vulnerabilities). Nova
dependência `defusedxml` em `requirements.txt` (biblioteca pequena, pura
Python, sem build pesado - ao contrário de `fastkml`/`geopandas`, que
trariam GDAL só para isso).

`parsear_kml(caminho)` é pura (sem cache, testável com fixtures pequenas
em `tmp_path`): busca `<coordinates>` em qualquer profundidade da árvore
(`Element.iter`), não assume a estrutura exata de
`Placemark > MultiGeometry > LineString` - continua funcionando se o KML
for reexportado com Placemarks em pastas ou sem o `MultiGeometry`
envolvente. Cada `<coordinates>` vira um "trilho" (lista de pontos
`(latitude, longitude)` - o KML grava `longitude,latitude,altitude`,
invertido aqui). Nunca lança: arquivo ausente ou XML malformado devolve
lista vazia - a malha é uma camada de referência/decorativa, uma falha
aqui não pode derrubar o mapa operacional.

`carregar_trilhos_malha_mrs()` lê o arquivo uma única vez por processo
(cache em memória via variável de módulo, mesmo padrão já usado em
`painel/graficos.py::_ler_js_echarts_local` para o JS do ECharts de
1MB+ - reler 632KB do disco a cada rerun do Streamlit seria desperdício).

### 2. `painel/mapa.py` - paleta e nova camada

- **Pulsos brutos**: cor fixa amarela (`#FFC107`, borda `#B8860B`) em vez
  da cor por qualidade (`_COR_POR_QUALIDADE`, removida - dead code). A
  qualidade continua no popup (`Qualidade: {...}`), só deixou de ser
  codificada visualmente por cor.
- **Trajetória simplificada**: vermelho (`#E53935`), tracejado-pontilhado
  (`dash_array="10,6,2,6"` - Leaflet `dashArray`).
- **Basemap**: trocado o tile padrão do Folium (OpenStreetMap colorido)
  por `cartodbpositron` (built-in no Folium, sem chave de API) - claro,
  minimalista, prioriza legibilidade de ruas, mais próximo da imagem de
  referência fornecida pelo responsável pelo produto.
- **Nova camada "Malha ferrea MRS"**: novo parâmetro opcional
  `trilhos_ferrovia` em `construir_mapa`, desenhado como uma
  `PolyLine` por trilho, cor quase preta (`#212121`), sempre visível por
  padrão (`show=True`) e sempre desenhada mesmo sem nenhum pulso (é uma
  camada de referência estática, não depende de haver jornada
  selecionada) - único caso em que `construir_mapa([], ...)` desenha algo
  além do mapa vazio.

### 3. `painel/telas/mapa_operacional.py`

Chama `carregar_trilhos_malha_mrs()` e passa para `construir_mapa` -
única mudança na tela, o resto do fluxo (seleção de jornada, sliders de
simplificação/cluster) continua igual.

## Validação de qualidade realizada

- `python -m py_compile` nos 3 módulos tocados: OK.
- `pytest` completo: 328 passed (318 anteriores + 10 novos: 7 em
  `tests/test_malha_ferrea.py` cobrindo `parsear_kml` - múltiplos
  trilhos, inversão lon/lat, arquivo ausente, XML malformado,
  coordinates com um único ponto ignorado, mais 2 contra o arquivo real
  confirmando faixa de coordenadas plausível para o Brasil e o cache por
  processo -, e 3 líquidos em `tests/test_mapa.py` substituindo o teste
  antigo de cor-por-qualidade por cor-amarela-fixa, trajetória
  vermelha/tracejada e a nova camada opcional da malha férrea).
- Parser testado contra o `malha_mrs.kml` real: 26 trilhos, ~15.700
  pontos, todas as coordenadas dentro da faixa do Brasil.
- Preview local gerado com `folium.Map.save()` (dados de exemplo
  reposicionados perto de um ponto real da malha) para conferir a
  composição das camadas antes de subir - prática já validada no projeto
  irmão Gestão_OS ("gerar com dados falsos e olhar o render antes de
  publicar").

## Validação NÃO realizada

- **Renderização visual real num navegador** - mesma limitação já
  registrada em ADR anteriores deste app (sandbox sem Chromium/
  Playwright): não foi possível confirmar visualmente que o basemap
  `cartodbpositron` carrega e que a composição final bate com a imagem
  de referência. O preview local gerado confirma que as camadas existem
  no HTML com as cores/estilos certos (mesma checagem que os testes
  automatizados fazem), mas não substitui olhar o mapa de verdade
  renderizado. Pedir ao responsável pelo produto para conferir no painel
  publicado antes de considerar fechado.
- `defusedxml` instalado e validado localmente, mas o ambiente de deploy
  (Streamlit Cloud) só vai instalá-lo no próximo build a partir de
  `requirements.txt` - mesma ressalva de sempre sobre deploy não ser
  instantâneo.

## Arquivos afetados

- `painel/malha_ferrea.py` (novo).
- `painel/mapa.py` (paleta, basemap, camada da malha férrea).
- `painel/telas/mapa_operacional.py` (passa `trilhos_ferrovia`).
- `requirements.txt` (`defusedxml`).
- `malha_mrs.kml` (versionado pela primeira vez - necessário em runtime
  no Streamlit Cloud, que só enxerga arquivos do repositório).
- `tests/test_malha_ferrea.py` (novo), `tests/test_mapa.py` (casos
  atualizados/novos).
