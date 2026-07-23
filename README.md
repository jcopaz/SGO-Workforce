# SGO Workforce Blueprint v1.0

Pacote oficial de concepção e treinamento de agentes para o **SGO Workforce**, plataforma de gestão de jornada, apropriação automática de HH, falhas, telemetria de campo e capacidade operacional.

## Como usar
1. Leia `CLAUDE.md` na raiz.
2. Leia `docs/00_INDICE.md` e os documentos na ordem indicada.
3. Antes de codificar, confirme o alvo da sessão e a fase do roadmap.
4. Use a branch `dev` para funcionalidades de captura, sincronização, GPS e banco.
5. Faça entregas pequenas, testáveis e reversíveis.

## Conteúdo
- visão de produto e contexto do ecossistema SGO;
- arquitetura offline first;
- motor de eventos e HH;
- modelo de pulsos GPS;
- atendimento estruturado de falhas;
- catálogo derivado do RASF;
- dashboards ECharts, mapa e exportações;
- modelo de dados, SQL inicial, backlog e critérios de aceite;
- instruções para Claude Code, GitHub Copilot, Copilot Studio e VS Code.

## Status
Blueprint de concepção, com o Incremento 1 (motor de domínio) já
implementado e testado em `src/workforce_core/`.

## Incremento 1 — Motor de Jornada, Atividade, Pausa e HH

Escopo, regras fechadas e casos de teste obrigatórios estão descritos em
`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` (documento oficial
vigente). A decisão provisória de modelagem da pausa está registrada em
`docs/28_ADR_0001_MODELAGEM_PROVISORIA_DA_PAUSA.md`.

Código: `src/workforce_core/` (`enums.py`, `exceptions.py`, `entities.py`,
`engine.py`, `calculo.py`). Testes: `tests/test_motor_jornada.py`.

## Incremento 2 — Persistência local e recuperação de estado

Cada jornada é gravada em um arquivo JSON próprio, com escrita atômica e
sem apagar dados em caso de corrupção. O "estado ativo" (qual atividade e
qual pausa estão em andamento) é sempre recalculado a partir dos estados
persistidos, nunca guardado como campo redundante. Decisão provisória de
formato registrada em `docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md`.

Código: `src/workforce_storage/` (`serializacao.py`,
`repositorio_jornada.py`). Testes: `tests/test_persistencia.py`.

## Incremento 3 — Fila offline e sincronização idempotente

Cada jornada é enfileirada para sincronização (`FilaSincronizacao`,
estados `PENDENTE`/`SINCRONIZADO`/`ERRO`/`CONFLITO`, persistidos em
arquivo). O `Sincronizador` envia pendentes em lote através de um cliente
de transporte plugável (`ClienteSincronizacao`); como ainda não existe uma
API real, `ClienteSincronizacaoEmMemoria` simula um servidor idempotente
para desenvolvimento e testes. Conflitos nunca são retomados
automaticamente — só voltam ao lote após reenfileiramento explícito.
Decisões provisórias em
`docs/30_ADR_0003_FILA_OFFLINE_E_SINCRONIZACAO_PROVISORIA.md`.

Código: `src/workforce_sync/`. Testes: `tests/test_sincronizacao.py`.

### Como rodar

```bash
python -m pip install pytest
python -m py_compile src/workforce_core/*.py src/workforce_storage/*.py src/workforce_sync/*.py tests/*.py
python -m pytest -v
```

Nenhuma dependência de `Requirements.txt` (Streamlit, FastAPI, banco) é
necessária para os Incrementos 1 a 3 — ainda não há interface, API real
nem banco de produção.

## Incremento 4 — Interface operacional simples para celular

PWA estático em `interface_campo/` (sem framework, sem build): motor de
domínio e de cálculo portados para JavaScript espelhando
`workforce_core` (validados por 17 testes Node com os mesmos casos da
seção 9), armazenamento em IndexedDB com recuperação de estado, e um
fluxo mínimo de 6 botões (iniciar jornada/atividade/pausa, finalizar
pausa, encerrar atividade/jornada). Decisões provisórias — e uma limitação
importante: **o app não foi testado em navegador ou celular real neste
ambiente** (sem ferramenta de automação de navegador disponível) — estão
registradas em `docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md`.

Código: `interface_campo/`. Testes: `tests/js/motorJornada.test.mjs`.

### Como rodar a interface de campo

```bash
cd interface_campo
python -m http.server 8000
# abrir http://localhost:8000 no navegador (ou http://<ip-da-maquina>:8000 no celular na mesma rede)
```

```bash
node --test tests/js/motorJornada.test.mjs
```

**Antes de qualquer piloto com colaboradores**: alguém precisa abrir esta
interface em um navegador/celular real e validar o fluxo completo — isso
ainda não foi feito (ver ADR-0004).

## Incremento 5 — Catálogo de motivos, deslocamentos, esperas e apoios

Infraestrutura de catálogo (`src/workforce_core/catalogo.py`), sem nenhum
conteúdo oficial — toda entrada nasce com classificação de HH
`NAO_DEFINIDO`. Nova entidade `EventoSecundario` (deslocamento, espera,
apoio), vinculada à Jornada e mutuamente exclusiva com a atividade
principal, seguindo a regra "apenas um evento principal ativo" já descrita
em `docs/07_MOTOR_EVENTOS_E_HH.md`. Decisões e o que ficou deliberadamente
fora de escopo (catálogo oficial, classificação produtiva/improdutiva,
paridade em JavaScript) em
`docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md`.

Código: `src/workforce_core/catalogo.py`, `entities.py`, `engine.py`,
`calculo.py` (estendidos). Testes: `tests/test_eventos_secundarios.py`.

## Incremento 6 — Atendimento de falha e catálogo RASF

`Atividade` ganhou um campo opcional `dados_falha`; quando presente, o
encerramento exige nota, ativo, sintoma, causa, ação e observação técnica
(regra fechada, `docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção
3.5). `workforce_storage/catalogo_rasf.py` carrega os catálogos reais já
extraídos do RASF em `catalogos/` (sintomas, sistemas, tipos de
solicitação, impactos, componentes causadores, 6M). Decisões e escopo em
`docs/33_ADR_0006_ATENDIMENTO_FALHA_E_CATALOGO_RASF.md`.

Código: `workforce_core` (estendido), `workforce_storage/catalogo_rasf.py`.
Testes: `tests/test_atendimento_falha.py`, `tests/test_catalogo_rasf.py`.

## Incremento 7 — Pulsos GPS, qualidade e sincronização em lote

`PulsoGps` (entidade própria, vinculada por `jornada_id`) com os campos de
`docs/08_GPS_PULSOS_E_PRIVACIDADE.md`. Avaliação de qualidade
(`workforce_core/qualidade_gps.py`) sem nenhum limiar numérico embutido —
precisão máxima aceitável e velocidade máxima plausível são sempre
parâmetros explícitos. Armazenamento local append-only em `.jsonl`
(`RepositorioPulsosGpsArquivo`) e sincronização em lote por cursor
(`SincronizadorPulsos`), reaproveitando o `ClienteSincronizacao` do
Incremento 3. Decisões e o que fica fora de escopo (captura real em
navegador, obrigatoriedade, contingência, retenção, LGPD) em
`docs/34_ADR_0007_PULSOS_GPS_QUALIDADE_E_SINCRONIZACAO_LOTE.md`.

Código: `workforce_core/qualidade_gps.py`,
`workforce_storage/repositorio_pulsos_gps.py`,
`workforce_sync/cursor_pulsos.py`, `workforce_sync/sincronizador_pulsos.py`.
Testes: `tests/test_gps.py`.

## Incremento 8 — Consolidação de HH e qualidade dos dados

`workforce_core/consolidacao.py`: soma por categoria (uma jornada) e
consolidação de HH entre várias jornadas, jornadas abertas há muito tempo
e taxa de qualidade de GPS (sem nenhum limiar numérico embutido), e
pendências de sincronização de pulsos. Grounded em
`docs/20_TESTES_E_QUALIDADE.md` (Reconciliação/Observabilidade). Decisões
em `docs/35_ADR_0008_CONSOLIDACAO_HH_E_QUALIDADE.md`.

Testes: `tests/test_consolidacao.py`.

## Incremento 9 — Dashboard ECharts (Streamlit)

Painel gerencial piloto em `painel/` (`dados.py`, `graficos.py`, `app.py`).
Gráficos via **pyecharts** (não `streamlit-echarts`, incompatível com o
Streamlit deste ambiente — troca documentada em
`docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md`), renderizados como HTML
autocontido sem depender de CDN. Indicadores oficiais, filtros e metas
continuam pendentes — o painel mostra apenas o que já é calculável pelo
motor de domínio.

### Como rodar o painel

```bash
python -m pip install streamlit pyecharts pandas
python -m streamlit run painel/app.py
```

Abra `http://localhost:8501`. Use o botão "Gerar dados de exemplo" para
ver o painel populado sem precisar de dados reais.

Testes: `tests/test_painel.py` (roda com `python -m pytest`).

## Incremento 10 — Mapa operacional (Folium)

Segunda página do painel (`painel/pages/1_Mapa_Operacional.py`): pulsos
brutos coloridos por qualidade, trajetória simplificada e clusters de
permanência (sempre rotulados como inferência, nunca prova). Lógica pura
em `workforce_core/geo.py`, sem nenhum limiar padrão embutido. Decisões,
um bug real encontrado/corrigido durante a validação, e o que fica fora
de escopo em `docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md`.

Testes: `tests/test_geo.py`, `tests/test_mapa.py`.

## Incremento 11 — Exportações (CSV, XLSX, GeoJSON)

`src/workforce_export/`: CSV (jornadas/eventos/falhas/gps + metadados),
XLSX (8 abas, totais idênticos ao painel via `workforce_core.consolidacao`)
e GeoJSON (pontos/trajetórias, matrícula do colaborador omitida por
padrão). Terceira página do painel:
`painel/pages/2_Exportacoes.py`. Decisões e o que fica fora de escopo em
`docs/38_ADR_0011_EXPORTACOES_CSV_XLSX_GEOJSON.md`.

Testes: `tests/test_exportacoes.py`.

## Incremento 12 — Capacidade PCM

`workforce_core/pcm.py`: fórmula de capacidade bruta/efetiva de
`docs/15_CAPACIDADE_PCM.md` (todos os termos como parâmetros explícitos,
piso zero), buckets citados do doc, e `simular_cenario` que sempre
devolve as premissas usadas. Quarta página do painel:
`painel/pages/3_Capacidade_PCM.py`, com mapeamento categoria→bucket
rotulado como exemplo não oficial. Decisões em
`docs/39_ADR_0012_CAPACIDADE_PCM.md` — o incremento com mais pendências
de negócio até agora (fonte de escala, ausências, buckets oficiais).

Testes: `tests/test_pcm.py`.

## Incremento 13 — Contrato de integração futura com o SGO (último do roadmap)

`workforce_core/integracao_sgo.py`: `ReferenciaOS` (identidade nunca é só
o número da OS — usa número + ciclo/plano, conforme
`docs/16_INTEGRACAO_FUTURA_SGO.md`), value objects para
usuário/coordenação/especialidade/pátio/ativo/OS programada, e
`ContratoSGO` (Protocol somente leitura) com uma implementação falsa
(`ContratoSGOEmMemoria`) para testes — **nenhuma integração real existe**,
apenas a forma do contrato já documentado, preparada com antecedência.
`DadosFalha.os_referencia` (campo recomendado, opcional) usa essa chave
desde já. Decisões e o fechamento do roadmap completo em
`docs/40_ADR_0013_CONTRATO_INTEGRACAO_FUTURA_SGO.md`.

Testes: `tests/test_integracao_sgo.py`.

## Status do roadmap

Os 13 incrementos de `docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`
(seção 11) estão implementados, com 158 testes automatizados
(`python -m pytest`) e um ADR por incremento (`docs/28` a `docs/40`)
registrando decisões provisórias e o que ficou fora de escopo. **Nenhuma
tela deste projeto foi aberta em um navegador real** nesta sessão (sem
ferramenta de automação de navegador disponível no ambiente) — isso
continua pendente antes de qualquer piloto com colaboradores reais, assim
como as decisões de negócio explicitamente marcadas como pendentes em
cada ADR (catálogos oficiais, limiares de GPS, fonte de escala/ausências,
LGPD, autenticação).
