# Changelog

## [Unreleased]

### Adicionado
- Motor de domínio do Incremento 1 (`src/workforce_core/`): entidades
  `Jornada`, `Atividade` e `Pausa`, enums de estado, exceções de domínio,
  motor de transições (`MotorJornada`) e motor de cálculo de HH
  (`calculo.py`).
- Suíte de testes unitários (`tests/test_motor_jornada.py`) cobrindo os 13
  casos obrigatórios da seção 9 do alinhamento oficial v1.2, mais 3 testes
  adicionais de regras estruturais (jornada exigida, atividade ativa
  exigida, motivo obrigatório).
- `docs/28_ADR_0001_MODELAGEM_PROVISORIA_DA_PAUSA.md`: registro da decisão
  provisória de modelar a pausa como evento próprio vinculado à atividade.
- `pyproject.toml` com configuração de `pytest` (`pythonpath = src`).
- Incremento 2 — persistência local e recuperação de estado
  (`src/workforce_storage/`): serialização de entidades para JSON
  (`serializacao.py`), repositório de jornadas em arquivo com escrita
  atômica e tratamento de corrupção (`RepositorioJornadaArquivo`).
- `MotorJornada.a_partir_de()` e `EstadoInconsistenteError` em
  `workforce_core`: reconstrói o motor a partir de uma jornada persistida,
  recalculando atividade/pausa ativas a partir dos estados (nunca de um
  campo redundante) e recusando estados logicamente impossíveis.
- `tests/test_persistencia.py`: 12 testes cobrindo round-trip, preservação
  de UUID, recuperação após fechamento abrupto com pausa/atividade em
  andamento, escrita atômica sem resíduo `.tmp`, arquivo JSON inválido não
  apagado, estrutura inválida não apagada, estado semanticamente
  inconsistente detectado, `listar_abertas` ignorando corrompidos sem
  apagá-los, e exclusão.
- `docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md`: decisão provisória
  de formato de serialização, escrita atômica e política de corrupção.
- Incremento 3 — fila offline e sincronização idempotente
  (`src/workforce_sync/`): `RegistroFila`/`StatusSincronizacao`
  (`PENDENTE`/`SINCRONIZADO`/`ERRO`/`CONFLITO`), `RepositorioFilaArquivo`
  (mesmo padrão de escrita atômica e não deleção em corrupção),
  `FilaSincronizacao` (enfileirar, listar, resumo, marcar_*), contrato
  `ClienteSincronizacao` (Protocol) com implementação falsa idempotente
  `ClienteSincronizacaoEmMemoria` para testes/dev, e `Sincronizador`
  (`sincronizar_pendentes`, isolamento de falha por item, conflito nunca
  automático).
- `tests/test_sincronizacao.py`: 11 testes cobrindo enfileiramento,
  sincronização idempotente (sem reenvio quando nada mudou, upsert sem
  duplicidade em reenvio pós-confirmação-perdida), retry automático de
  erro, conflito nunca resolvido silenciosamente (exclui do lote até
  reenfileiramento explícito), os 4 status simultâneos, limite de tamanho
  de lote, fila sobrevivendo a "reinício do app", e registro de fila
  corrompido não apagado.
- `docs/30_ADR_0003_FILA_OFFLINE_E_SINCRONIZACAO_PROVISORIA.md`: decisão
  provisória de transporte plugável, granularidade por jornada, tamanho de
  lote e política de conflito/retry.
- Incremento 4 — interface operacional simples para celular
  (`interface_campo/`): PWA estático (HTML/CSS/JS, sem framework nem
  build), motor de domínio e motor de cálculo portados para JavaScript
  espelhando `workforce_core` (`js/motorJornada.js`, `js/calculo.js`,
  `js/enums.js`, `js/erros.js`, `js/entidades.js`), armazenamento em
  IndexedDB com recuperação de estado (`js/armazenamento.js`), UI mínima
  com DOM seguro (sem `innerHTML` com conteúdo dinâmico), manifest PWA e
  service worker cache-first para uso offline.
- `tests/js/motorJornada.test.mjs`: 17 testes Node (`node --test`)
  replicando os 13 casos obrigatórios da seção 9 do alinhamento oficial no
  motor JavaScript, mais regras estruturais e recuperação de estado —
  garante paridade com o motor Python já validado.
- `docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md`: decisão provisória
  de duplicação do motor em JS, contrato de IndexedDB, fluxo de botões, e
  registro explícito de que o teste em navegador/celular real **não foi
  realizado** neste ambiente (sem chromium-cli/Playwright disponível e sem
  acesso de rede para instalar — mesma causa do erro `ENOTFOUND` relatado
  nesta sessão).
- Incremento 5 — catálogo de motivos e eventos secundários
  (`src/workforce_core/catalogo.py`): `Categoria` (taxonomia de
  `docs/07_MOTOR_EVENTOS_E_HH.md`), `ClassificacaoHH` (sempre
  `NAO_DEFINIDO` por padrão), `EntradaCatalogo`, `CatalogoMotivos`,
  `catalogo_padrao()` com motivos `*_TESTE`.
- Nova entidade `EventoSecundario` (deslocamento/espera/apoio), vinculada
  diretamente à Jornada e mutuamente exclusiva com a atividade principal
  ("apenas um evento principal ativo", regra já documentada em
  `docs/07_MOTOR_EVENTOS_E_HH.md`). `MotorJornada` ganhou
  `iniciar_evento_secundario`/`encerrar_evento_secundario`, com as mesmas
  garantias de idempotência/consistência da Pausa; `a_partir_de` agora
  também recupera o evento secundário ativo.
- `calculo.py`: `duracao_evento_secundario`, `duracao_eventos_secundarios`;
  duração de eventos secundários agora entra em `tempo_classificado_jornada`;
  `resumo_jornada` inclui `eventos_secundarios`.
- `workforce_storage/serializacao.py`: `FORMATO_VERSAO` 1 → 2, serializa
  `eventos_secundarios`; leitura de arquivos v1 (sem esse campo) continua
  funcionando via `.get("eventos_secundarios", [])`.
- `tests/test_eventos_secundarios.py`: 18 testes cobrindo início/fim dos
  três tipos, tipo/motivo obrigatórios, exclusão mútua nos dois sentidos
  (evento após atividade e atividade após evento), bloqueio de segundo
  evento simultâneo, bloqueio de encerramento de jornada com evento aberto,
  timestamp inválido, entrada no tempo classificado, recuperação de estado,
  detecção de inconsistência (evento e atividade ativos juntos), round-trip
  de persistência, e comportamento do catálogo.
- `docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md`: decisão
  registrando a taxonomia (citada de doc já existente, não inventada), a
  regra de exclusão mútua, e o que continua deliberadamente fora de escopo
  (conteúdo oficial do catálogo, classificação produtiva/improdutiva,
  paridade em JavaScript).
- Incremento 6 — atendimento de falha e catálogo RASF: `Atividade` ganhou
  campo opcional `dados_falha: Optional[DadosFalha]`
  (`nota`/`ativo`/`sintoma`/`causa`/`acao`/`observacao`);
  `MotorJornada.iniciar_atendimento_falha` e
  `MotorJornada.registrar_dados_falha` (atualização parcial); regra
  inegociável da seção 3.5 aplicada em `encerrar_atividade`: não encerra
  atendimento de falha sem os 6 campos preenchidos
  (`AtendimentoFalhaCamposObrigatoriosError`, listando o que falta).
- `workforce_storage/catalogo_rasf.py`: carregador dos catálogos reais em
  `catalogos/` (sintomas, sistemas, tipos de solicitação, impactos,
  componentes causadores, 6M níveis 1-3), preservando código/descrição/
  frequência/status ativo, com `item_por_codigo`, `item_por_valor`,
  `apenas_ativos`.
- `workforce_storage/serializacao.py`: `FORMATO_VERSAO` 2 → 3, serializa
  `dados_falha`; leitura de arquivos v1/v2 continua funcionando.
- `tests/test_atendimento_falha.py` (8 testes) e `tests/test_catalogo_rasf.py`
  (6 testes, lendo os CSVs reais do repositório — não fixtures fabricadas):
  fluxo completo, bloqueio com campos ausentes/parciais (mensagem lista os
  faltantes), preenchimento progressivo, atendimento com pausa, atividade
  comum não exige campos de falha, números do catálogo real batendo com
  `catalogos/README.md` (53 sintomas, 5 sistemas, 10 tipos de solicitação,
  4 impactos, 148 componentes causadores).
- `docs/33_ADR_0006_ATENDIMENTO_FALHA_E_CATALOGO_RASF.md`: decisão de
  reaproveitar `Atividade` em vez de criar entidade paralela, e o que fica
  fora de escopo (campos recomendados, validação cruzada com catálogo,
  governança, paridade em JavaScript).
- Incremento 7 — pulsos GPS, qualidade e sincronização em lote: nova
  entidade `PulsoGps` (`workforce_core/entities.py`, vinculada por
  `jornada_id`, não aninhada) com todos os campos de
  `docs/08_GPS_PULSOS_E_PRIVACIDADE.md`; `QualidadePulso`
  (`OK`/`PRECISAO_RUIM`/`SALTO_IMPOSSIVEL`/`VELOCIDADE_INCOMPATIVEL`/
  `NAO_AVALIADO`).
- `workforce_core/qualidade_gps.py`: `distancia_metros` (haversine),
  `velocidade_implicita_metros_segundo`, `avaliar_pulso` — nenhum limiar
  numérico com valor padrão, sempre exigido explicitamente de quem chama.
- `workforce_storage/repositorio_pulsos_gps.py`: `RepositorioPulsosGpsArquivo`,
  armazenamento local append-only em `.jsonl` (uma linha por pulso, com
  `flush`+`fsync`), com leitura resiliente a linha corrompida
  (`ler_pulsos_com_erros` reporta o número da linha sem apagar nada).
- `workforce_sync`: `ClienteSincronizacao` ganhou `enviar_lote_pulsos`
  (upsert por id de pulso, idempotente); `CursorSincronizacaoPulsos` +
  `RepositorioCursorPulsosArquivo` (cursor por jornada, mais simples que a
  fila de 4 estados usada para jornadas, já que pulsos não têm conflito);
  `SincronizadorPulsos` (`sincronizar_pendentes`, `sincronizar_tudo`).
- `tests/test_gps.py` (18 testes): avaliação de qualidade (distância
  haversine, ok, precisão ruim, salto impossível, velocidade incompatível
  reportada pelo dispositivo, precisão original preservada), round-trip de
  serialização, gravação/leitura append-only em ordem, linha corrompida
  não apaga as demais, sincronização respeitando tamanho de lote,
  `sincronizar_tudo` esvaziando a fila em vários lotes, reenvio após ack
  perdido sem duplicar, erro de rede não avança o cursor.
- `docs/34_ADR_0007_PULSOS_GPS_QUALIDADE_E_SINCRONIZACAO_LOTE.md`: decisão
  de campos/categorias citados dos docs existentes (não inventados),
  nenhum limiar numérico embutido, e lista extensa do que fica
  deliberadamente fora (captura real em navegador, obrigatoriedade,
  contingência, retenção, perfis, LGPD).
- Incremento 8 — consolidação de HH e qualidade dos dados
  (`workforce_core/consolidacao.py`): `resumo_por_categoria` (agrega
  atividade/pausa/evento secundário por `Categoria`, usando o catálogo);
  `resumo_consolidado` (primeira função capaz de agregar HH de várias
  jornadas, ex.: equipe/período); `jornadas_abertas_ha_muito_tempo` e
  `taxa_qualidade_pulsos` (sem limiares embutidos);
  `pulsos_pendentes_de_sincronizacao` (reconciliação enviados x
  recebidos).
- `tests/test_consolidacao.py` (14 testes): classificação de atividade
  comum vs. atendimento de falha, pausa sem categoria/fora do catálogo,
  itens em andamento ignorados, soma multi-jornada com reconciliação
  bruta=classificado+não classificado, jornadas encerradas ignoradas na
  consolidação, jornada aberta há muito tempo detectada/ignorada, taxa de
  qualidade de GPS (incluindo `None` quando nada avaliado), pendências de
  sincronização de pulsos.
- `docs/35_ADR_0008_CONSOLIDACAO_HH_E_QUALIDADE.md`: decisão registrando
  por que a reconciliação de soma já é garantida por construção desde o
  Incremento 1, e o que fica fora (soma por OS, HH de equipe, dashboard x
  exportação — dependem de conceitos ainda não construídos).
- Incremento 9 — dashboard ECharts (`painel/`): `dados.py` (carregamento
  de jornadas via `workforce_storage`, sem apagar arquivo corrompido;
  `montar_resumo` via `workforce_core.consolidacao`; geração de dados de
  exemplo para demonstração); `graficos.py` (gráficos de barra e pizza via
  **pyecharts**, renderizados como HTML autocontido com o JS do ECharts
  embutido localmente — sem CDN, com falha explícita se o asset local
  estiver ausente); `app.py` (entrypoint Streamlit, aviso permanente de
  piloto técnico, estado do diretório preservado via `st.session_state`).
- **Troca arquitetural**: `streamlit-echarts` (previsto em
  `Requirements.txt`) está incompatível com a versão do Streamlit
  disponível neste ambiente (exige `asset_dir` em `pyproject.toml` que o
  pacote não suporta em nenhuma versão publicada). Substituído por
  `pyecharts` + `st.components.v1.html` — continua sendo Apache ECharts,
  só que integrado de outra forma. `Requirements.txt` atualizado.
- `tests/test_painel.py` (9 testes): formatação de horas, carregamento
  com/sem erro, geração e agregação de dados de exemplo, arquivo
  corrompido reportado sem ser apagado, HTML de gráfico autocontido sem
  CDN, falha explícita quando o asset local está ausente.
- **Smoke test real**: `streamlit run painel/app.py --server.headless
  true` iniciado de fato (não apenas import), com HTTP 200 confirmado por
  `curl` em `/` e `/_stcore/health`, sem dados e com dados de exemplo
  (exercitando gráficos e tabela), sem traceback no log.
- `docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md`: decisão completa da
  troca de biblioteca, mitigação de CDN sem integrity, e o que fica fora
  (indicadores oficiais, filtros, autenticação, teste em navegador real).
- Incremento 10 — mapa operacional: `workforce_core/geo.py`
  (`simplificar_trajetoria`, `agrupar_permanencia`/`ClusterPermanencia`,
  sem nenhum limiar padrão embutido); `painel/mapa.py`
  (`construir_mapa` com Folium: pulsos brutos coloridos por qualidade,
  trajetória simplificada, clusters de permanência com popup "inferência,
  não prova", escape de HTML nos popups); `painel/pages/1_Mapa_Operacional.py`
  (segunda página do painel multipage, com `gerar_pulsos_exemplo`
  determinístico para demonstração).
- **Bug real encontrado e corrigido**: `RepositorioJornadaArquivo.listar_ids()`
  quebrava com `ValueError` se o diretório contivesse qualquer `.json`
  cujo nome não fosse um UUID (ex.: `MANIFESTO.json` na raiz do projeto).
  Corrigido para ignorar esses arquivos, mesma disciplina de resiliência
  já usada para arquivos corrompidos. Teste de regressão em
  `tests/test_persistencia.py`. Guardas de diretório vazio adicionados em
  `painel/app.py` e na página do mapa.
- `tests/test_geo.py` (8 testes) e `tests/test_mapa.py` (6 testes):
  simplificação de trajetória, agrupamento de permanência, mapa sem
  quebrar sem dados, camadas geradas corretamente, popup escapando HTML
  de campo controlado pelo usuário, cores por qualidade.
- `docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md`: decisão completa,
  incluindo o relato do bug encontrado/corrigido e o que fica fora
  (camadas dependentes de mais dados, filtros de conceitos ainda não
  modelados, restrição por perfil).
- Incremento 11 — exportações (`src/workforce_export/`):
  `MetadadosExportacao` (usuário responsável obrigatório, sufixo de
  arquivo com período+geração); `csv_exportacao.py` (jornadas, eventos
  unificados, falhas com coluna `completo`, gps + `metadados_*.json`
  companheiro); `xlsx_exportacao.py` (abas Resumo, HH por categoria, HH
  por ativo, Jornadas, Pausas, Falhas, Qualidade, Dicionário de dados —
  totais vêm exatamente de `workforce_core.consolidacao`, mesma fonte do
  painel); `geojson_exportacao.py` (pontos e trajetórias simplificadas,
  matrícula do colaborador omitida por padrão — minimização de dados
  pessoais). `painel/pages/2_Exportacoes.py`: terceira página do painel,
  exige usuário responsável antes de habilitar downloads.
- `tests/test_exportacoes.py` (15 testes): reconciliação exata de totais
  CSV/XLSX com `consolidacao`, metadados obrigatórios, marcação de
  atendimento de falha completo/incompleto, todas as abas do XLSX,
  GeoJSON com minimização de dados pessoais por padrão e coordenadas no
  formato correto.
- `docs/38_ADR_0011_EXPORTACOES_CSV_XLSX_GEOJSON.md`: decisão completa,
  incluindo por que "participantes" e "HH por OS" não são exportados
  (conceitos ainda não modelados) e a decisão de minimização de dados
  pessoais por padrão no GeoJSON.
- Incremento 12 — capacidade PCM (`workforce_core/pcm.py`):
  `capacidade_bruta`/`capacidade_efetiva` (fórmula de
  `docs/15_CAPACIDADE_PCM.md`, todos os termos como parâmetros
  obrigatórios, piso zero); `BucketCapacidade` (citado do doc);
  `agrupar_por_bucket` (mapeamento categoria→bucket sempre explícito,
  única correspondência automática é lacuna não classificada →
  `LACUNA_NAO_APONTADO`); `PremissasCenario`/`ResultadoCenario`/
  `simular_cenario` ("sempre mostrar premissas", literal do doc).
  `painel/pages/3_Capacidade_PCM.py`: quarta página do painel, simulador
  com mapeamento de exemplo rotulado "não oficial".
- `tests/test_pcm.py` (7 testes): fórmula, piso zero, agrupamento por
  bucket com e sem lacuna, premissas sempre devolvidas no resultado.
- `docs/39_ADR_0012_CAPACIDADE_PCM.md`: decisão completa — o incremento
  com mais pendências de negócio até agora; documenta por que o cálculo
  automático fica deliberadamente limitado a descontar só ausências.
- Incremento 13 (último do roadmap) — contrato de integração futura com
  o SGO (`workforce_core/integracao_sgo.py`), sem integrar com nada real:
  `ReferenciaOS` (numero+ciclo_ou_plano na identidade, nunca só o número;
  data_importacao fora da igualdade); value objects `UsuarioAutorizado`,
  `Coordenacao`, `Especialidade`, `Patio`, `Ativo`, `OsProgramada`
  (chaves já documentadas em `docs/16`, nenhuma inventada);
  `ContratoSGO` (`Protocol` somente leitura, `@runtime_checkable`);
  `ContratoSGOEmMemoria` (implementação falsa, mesmo papel de
  `ClienteSincronizacaoEmMemoria`). `DadosFalha.os_referencia` (campo
  recomendado, opcional) usa `ReferenciaOS` desde o início.
  `FORMATO_VERSAO` 3 → 4, retrocompatível.
- `tests/test_integracao_sgo.py` (10 testes): identidade correta de
  `ReferenciaOS`, uso como chave de dict, atendimento de falha com OS
  referenciada opcionalmente, round-trip com/sem `os_referencia`,
  conformidade do contrato falso com o Protocol.
- `docs/40_ADR_0013_CONTRATO_INTEGRACAO_FUTURA_SGO.md`: decisão final e
  fechamento do roadmap de 13 incrementos — resume o que foi entregue e o
  que continua exigindo decisão humana antes de uso real.

### Alterado
- N/A (primeira entrega de código do projeto).

### Corrigido
- `MotorJornada.iniciar_pausa`: a checagem de "já existe pausa ativa"
  estava depois da checagem de "atividade ativa", e como a atividade fica
  `PAUSADA` durante uma pausa em curso, uma segunda tentativa de pausa
  levantava `PausaExigeAtividadeAtivaError` em vez de `PausaJaAtivaError`.
  Ordem invertida para checar `_pausa_ativa` primeiro.
- **Bug real encontrado no primeiro teste manual em navegador**
  (`interface_campo/js/app.js`): o botão "Iniciar jornada" quebrava com
  "Falha inesperada ao registrar o evento" no primeiro uso do app (antes
  de existir qualquer jornada no IndexedDB), porque tentava chamar
  `motor.iniciarJornada(...)` com `motor` ainda `null`. Corrigido com
  `prepararMotorComMatricula()`, chamada no clique do botão para garantir
  que o motor existe antes de iniciar a jornada (unifica o caminho do
  primeiro uso com o de "Iniciar nova jornada", que antes usava a função
  `reiniciar()`, agora removida). `CACHE_VERSAO` do Service Worker
  incrementada (`v1` → `v2`) para que a correção realmente chegue ao
  navegador — o Service Worker cacheia `app.js` e não busca a versão nova
  sozinho sem essa mudança de versão. Detalhes em
  `docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md`.

### Testes
- `python -m py_compile src/workforce_core/*.py src/workforce_storage/*.py src/workforce_sync/*.py tests/*.py`: OK.
- `python -m pytest`: 43 passed.
- `node --check` em todos os arquivos de `interface_campo/js/` e
  `interface_campo/service-worker.js`: sintaxe válida.
- `node --test tests/js/motorJornada.test.mjs`: 17 passed.
- Servidor estático real (`python -m http.server`) servindo
  `interface_campo/`: todos os arquivos (HTML, CSS, JS, manifest, service
  worker, ícone) respondem HTTP 200 com `Content-Type` correto.
- **Não realizado**: clique real em navegador/celular (sem
  chromium-cli/Playwright disponíveis neste ambiente). Ver
  ADR-0004, seção "Validação NÃO realizada".
- `python -m pytest`: 60 passed (após Incremento 5); 74 passed (após
  Incremento 6, incluindo leitura dos CSVs reais de `catalogos/`); 88
  passed (após Incremento 7); 102 passed (após Incremento 8); 111 passed
  (após Incremento 9); 126 passed (após Incremento 10); 141 passed (após
  Incremento 11); 148 passed (após Incremento 12); 158 passed (após
  Incremento 13 — roadmap completo).
- Caso mínimo obrigatório (seção 7.3) validado com os valores exatos da
  seção 7.4: jornada bruta 4h10, atividade bruta 3h50, pausa 0h20,
  atividade líquida 3h30, tempo não classificado 0h20.

### Riscos
- Toda pausa é 100% descontável neste incremento (decisão provisória, ver
  ADR-0001); catálogo oficial e classificação produtiva/improdutiva ficam
  para o Incremento 5.
- Formato de persistência local (arquivo JSON por jornada) é provisório
  (ADR-0002); o contrato de campos precisará ser replicado em JavaScript
  quando o Incremento 4 implementar IndexedDB no PWA.
- Política de retenção do arquivo local após confirmação de sincronização
  ainda não existe (o arquivo em `workforce_storage` não é removido nem
  marcado após `marcar_sincronizado`).
- `ClienteSincronizacaoEmMemoria` é exclusivamente para desenvolvimento e
  testes; não existe ainda um cliente HTTP real nem uma API para receber os
  dados (FastAPI/Postgres não fazem parte de nenhum incremento numerado até
  aqui).
- Regra de resolução de conflito é intencionalmente inexistente: o sistema
  detecta e sinaliza (`CONFLITO`), mas não decide automaticamente qual
  versão prevalece.
- Motor de domínio duplicado em Python e JavaScript (ADR-0004): qualquer
  mudança de regra de negócio precisa ser replicada manualmente nos dois
  lados até existir uma única fonte de verdade.
- Interface de campo (`interface_campo/`) nunca foi aberta em um navegador
  real nem testada em celular físico neste ambiente — validação manual
  pendente antes de qualquer piloto com colaboradores (ADR-0004).
- `interface_campo/` ainda não está conectada à fila de sincronização
  (`workforce_sync`, Incremento 3): não há API real para ela conversar.
- Catálogo de motivos (Incremento 5) não tem nenhum conteúdo oficial:
  todas as entradas têm `classificacao_hh = NAO_DEFINIDO` e são apenas
  placeholders de teste (`*_TESTE`). `EventoSecundario` (deslocamento,
  espera, apoio) não foi portado para `interface_campo/js/` — só existe no
  motor Python.
- Catálogo RASF (`catalogos/`) declaradamente **não é catálogo oficial de
  produção** (ver `catalogos/README.md`) — precisa de governança e
  validação da Eletroeletrônica antes de uso real.
- Nenhuma validação cruzada entre `DadosFalha` (sintoma/causa/ação) e o
  catálogo RASF carregado: o motor aceita qualquer string, igual já
  acontecia com motivo de pausa/evento secundário.
- Campos recomendados de atendimento de falha (sistema, componente
  causador, tipo/impacto, OS relacionada, pendência, evidência, equipe)
  ainda não implementados — só os 7 campos mínimos obrigatórios.
- Atendimento de falha (Incremento 6) não foi portado para
  `interface_campo/js/` — mesma situação de `EventoSecundario`.
- Painel (`painel/`) nunca foi aberto em navegador real — smoke test
  confirma que o servidor Python não quebra, não que os gráficos
  renderizam visualmente corretos (ADR-0009).
- Nenhum indicador do painel foi validado como oficial: filtros, metas,
  perfis de acesso e autenticação não existem.
- Mapa operacional (`painel/pages/1_Mapa_Operacional.py`) também nunca
  foi aberto em navegador real (ADR-0010). Camadas de pinos de
  evento/falha, ativos/pátios e heatmap de HH não implementadas. Filtros
  de coordenação/equipe/pátio/impacto não existem porque esses conceitos
  não estão modelados no sistema. Pulsos brutos não têm restrição por
  perfil (sem autenticação).
- Exportações (`painel/pages/2_Exportacoes.py`) nunca abertas em
  navegador real (ADR-0011). Layout de colunas não é oficial. Sem
  auditoria centralizada de exportações nem controle de acesso — qualquer
  pessoa com acesso ao painel exporta qualquer dado. "Matrícula fora do
  GeoJSON por padrão" é decisão técnica defensiva, não política de LGPD
  validada.
- Capacidade PCM (`painel/pages/3_Capacidade_PCM.py`) nunca aberta em
  navegador real (ADR-0012). Sem fonte real de escala/ausências/férias —
  tudo digitado manualmente. Mapeamento categoria→bucket é só um exemplo.
  Cálculo automático desconta apenas ausências; pausas não computáveis,
  improdutividade e atividades não aplicáveis exigem decisão manual de
  quem lê os buckets observados, porque a classificação
  produtiva/improdutiva do catálogo continua indefinida (ADR-0005).
- `ContratoSGO` (Incremento 13) não tem nenhuma implementação real — só
  `ContratoSGOEmMemoria`, para testes. Não há autenticação entre
  aplicações, SSO, nem definição de responsabilidade sobre dados mestres.
  A "segunda integração" (devolução de HH real ao SGO) não existe.
- Captura real de GPS (`navigator.geolocation`) não foi implementada em
  `interface_campo/js/` — não há como testar em dispositivo real neste
  ambiente. Nenhum limiar de qualidade (precisão mínima, velocidade máxima
  plausível) está definido em lugar nenhum do código — são parâmetros
  obrigatórios sem valor padrão. GPS não é obrigatório para nenhuma
  transição de jornada/atividade. Retenção, perfis autorizados e validação
  de LGPD continuam pendentes antes de qualquer uso real (ADR-0007).
