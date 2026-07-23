# ADR-0010 | Mapa operacional com Folium (Incremento 10)

## Contexto

`docs/13_MAPA_OPERACIONAL.md` já definia, antes desta sessão: objetivos
(não confundir inferência geográfica com declaração operacional),
camadas (pulsos brutos restritos a perfis autorizados, trajetória
simplificada, clusters de permanência, pinos de início/fim, falhas,
ativos/pátios, heatmap de HH), campos do popup, filtros, a definição de
"tempo no local" como inferência (nunca prova automática) e
recomendações de performance (simplificar trajetórias, agrupar pontos,
limitar período). `CLAUDE.md` fixa Folium/Leaflet como padrão para o mapa
operacional.

## Decisão

1. **`workforce_core/geo.py`** (pure, sem I/O): `simplificar_trajetoria`
   (mantém um ponto só se estiver a uma distância mínima do último
   mantido, sempre preservando primeiro/último ponto) e
   `agrupar_permanencia` (agrupa pulsos consecutivos próximos em
   `ClusterPermanencia`, descartando grupos mais curtos que um tempo
   mínimo). Nenhum dos dois limiares (distância mínima, raio de cluster,
   tempo mínimo) tem valor padrão embutido — mesmo padrão já estabelecido
   em `qualidade_gps.py` (ADR-0007): são decisões operacionais ainda não
   validadas.
2. **`painel/mapa.py`**: `construir_mapa` monta um `folium.Map` com as
   camadas que já são possíveis com o que existe hoje — pulsos brutos
   (coloridos por `QualidadePulso`, camada oculta por padrão para não
   sobrecarregar o mapa, conforme a recomendação de performance),
   trajetória simplificada, e clusters de permanência (popup explicita
   "inferência, não prova de presença", citando a regra do doc13
   literalmente). `folium.LayerControl` permite ligar/desligar cada
   camada.
3. **Popups com escape de HTML**: `colaborador_matricula` (texto livre
   digitado pelo usuário na interface de campo) e outros campos são
   passados por `html.escape()` antes de entrar no HTML do popup —
   evita que um valor malicioso digitado num campo de texto vire HTML/JS
   executável dentro do popup do mapa. Coberto por teste dedicado
   (`test_popup_escapa_html_de_campos_controlados_pelo_usuario`).
4. **`painel/pages/1_Mapa_Operacional.py`**: segunda página do painel
   Streamlit multipage (convenção `pages/`), reaproveitando
   `dados.carregar_jornadas` e adicionando `dados.carregar_pulsos` /
   `dados.gerar_pulsos_exemplo` (pulsos fabricados, determinísticos por
   `jornada.id`, para demonstrar o mapa sem depender de captura real de
   GPS — que não existe em `interface_campo/js/`, ADR-0007). Os três
   limiares de `geo.py` são expostos como sliders rotulados "não é valor
   oficial", nunca como configuração validada.

## Bug real encontrado e corrigido durante a validação

Ao tentar executar a página do mapa fora do `streamlit run` (modo "bare",
usado para tentar pegar erros de import/lógica sem precisar de navegador),
`RepositorioJornadaArquivo.listar_ids()` quebrou com
`ValueError: badly formed hexadecimal UUID string`. Causa raiz: o
diretório resolvido acabou sendo a raiz do projeto (efeito colateral do
modo bare, onde `st.session_state`/`st.text_input` não funcionam como em
uma sessão real), que contém `MANIFESTO.json` — um arquivo `.json` que não
é uma jornada. `listar_ids()` assumia que todo `*.json` no diretório era
`<uuid>.json` e chamava `UUID(caminho.stem)` sem tratamento de erro,
derrubando a listagem inteira por causa de um único arquivo estranho.

**Corrigido** em `src/workforce_storage/repositorio_jornada.py`:
`listar_ids()` agora ignora arquivos cujo nome não é um UUID válido, em
vez de propagar a exceção — mesma disciplina de resiliência já usada em
`carregar()`/`listar_abertas()` para arquivos corrompidos. Teste de
regressão: `test_listar_ids_ignora_json_que_nao_e_uuid`
(`tests/test_persistencia.py`).

Também foram adicionados guardas explícitos em `painel/app.py` e
`painel/pages/1_Mapa_Operacional.py`: se o campo de diretório estiver
vazio, a página para com um aviso em vez de silenciosamente operar sobre
o diretório de trabalho atual.

## Validação realizada

- `tests/test_geo.py` (8 testes): simplificação de trajetória (lista
  vazia, pontos distantes mantidos, pontos próximos descartados com
  extremos preservados, ordenação por timestamp), agrupamento de
  permanência (lista vazia, cluster parado detectado, grupo curto demais
  ignorado, dois locais distintos separados corretamente).
- `tests/test_mapa.py` (6 testes): geração determinística de pulsos de
  exemplo cobrindo o período da jornada, mapa sem pulsos não quebra, mapa
  com pulsos gera as camadas esperadas, popup escapa HTML de campo
  controlado pelo usuário, cores por qualidade aparecem no HTML gerado.
- `tests/test_persistencia.py`: teste de regressão do bug acima.
- **Smoke test real do servidor**: `streamlit run painel/app.py
  --server.headless true`, com dados de exemplo (jornadas + pulsos)
  pré-gerados, HTTP 200 confirmado tanto na página inicial quanto na rota
  do mapa, sem traceback no log do servidor.

## Validação NÃO realizada

**Não foi possível abrir o mapa em um navegador real** para confirmar
visualmente a renderização do Folium/Leaflet, a interatividade das
camadas, nem testar a seleção de jornada via `st.selectbox` — mesma
limitação de ambiente já registrada nos ADRs 4 e 9 (sem
`chromium-cli`/Playwright disponíveis). A execução direta do script em
modo "bare" (fora de `streamlit run`) tem limitações conhecidas e
documentadas pelo próprio Streamlit (`st.session_state` e a
interatividade de widgets como `st.selectbox` não funcionam sem uma
sessão real) — foi útil para encontrar o bug de `listar_ids()` acima, mas
não substitui um teste real em navegador.

## Deliberadamente fora deste incremento

- **Camadas não implementadas**: pinos de início/fim de evento, falhas
  por sintoma/impacto, ativos e pátios, heatmap de HH — dependem de mais
  volume de dados reais e de decisões ainda pendentes (catálogo de
  falhas/RASF já existe desde o Incremento 6, mas a camada de mapa
  específica para isso não foi priorizada aqui).
- **Filtros de coordenação, equipe, pátio e impacto** (citados em
  `docs/13`): não implementados porque esses conceitos **não existem** no
  domínio do sistema ainda — não é uma omissão, é a ausência do modelo de
  dados correspondente.
- **Restrição de pulsos brutos por perfil autorizado** (`docs/13`,
  "Camadas": "pulsos brutos, restritos a perfis autorizados"): não há
  autenticação nem perfis no sistema ainda — qualquer pessoa com acesso ao
  painel vê todos os pulsos.
- **Filtro de data/período**: não implementado nesta página — o usuário
  escolhe uma jornada específica em vez de um intervalo de tempo livre.

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (filtros que dependem de
  conceitos ainda não modelados, perfis de acesso) e teste manual em
  navegador real antes de qualquer demonstração.
