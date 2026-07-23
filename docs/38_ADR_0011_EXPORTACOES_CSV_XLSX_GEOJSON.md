# ADR-0011 | Exportações CSV, XLSX e GeoJSON (Incremento 11)

## Contexto

`docs/14_EXPORTACOES.md` já definia, antes desta sessão: arquivos CSV
separados (jornadas, eventos, participantes, falhas, GPS), abas do XLSX
(Resumo, HH por categoria, HH por OS, HH por ativo, Jornadas, Pausas,
Falhas, Qualidade, Dicionário de dados), GeoJSON com "permissão e
minimização de dados pessoais", e regras: filtros da tela repetidos no
arquivo, data/hora em formato legível e técnico, colunas documentadas,
total exportado reconciliando com o dashboard, nome do arquivo com
período e geração, exportação registrando usuário/timestamp/filtros.

`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção 3.7 repete como
**regra inegociável**: "Totais dos dashboards deverão reconciliar com as
exportações... Toda exportação deverá possuir data de geração, período,
filtros e usuário responsável." Seção 15.3 ("Antes do Incremento 11")
deixa pendente: layout oficial definitivo de colunas, dados pessoais
permitidos, política de auditoria da exportação, perfis autorizados e
requisitos específicos de GeoJSON.

## Decisão

1. **Novo pacote `src/workforce_export/`** (mesmo padrão arquitetural de
   `workforce_storage`/`workforce_sync`): `metadados.py`,
   `csv_exportacao.py`, `xlsx_exportacao.py`, `geojson_exportacao.py`.
2. **`MetadadosExportacao`**: `usuario_responsavel` (obrigatório, levanta
   `ValueError` se vazio — não há autenticação no sistema, então é sempre
   parâmetro explícito de quem chama), `filtros` (dict livre),
   `periodo_inicio`/`periodo_fim`, `data_geracao` (UTC, automática).
   `sufixo_nome_arquivo()` implementa "nome do arquivo inclui período e
   geração" (docs/14).
3. **Reconciliação garantida por construção**: `linhas_jornadas` (CSV) e
   a aba "Resumo" (XLSX) usam exatamente
   `workforce_core.consolidacao.resumo_consolidado` — a mesma função que
   `painel/dados.py:montar_resumo` usa para o dashboard (Incremento 9).
   Não há um segundo cálculo independente que possa divergir; os testes
   (`test_linhas_jornadas_reconcilia_com_consolidacao`,
   `test_exportar_xlsx_reconcilia_totais_com_consolidacao`) verificam essa
   igualdade explicitamente.
4. **CSV**: `jornadas`, `eventos` (unifica Atividade/Pausa/EventoSecundario
   num único arquivo, no espírito do modelo genérico de "Evento" de
   `docs/07_MOTOR_EVENTOS_E_HH.md`), `falhas`, `gps` — mais um
   `metadados_<sufixo>.json` companheiro (CSV não tem como carregar
   metadados dentro do próprio arquivo). **`participantes` não é
   exportado**: o sistema não modela múltiplos participantes por evento
   (decisão pendente, seção 6 do alinhamento — "regra para múltiplas OS
   no mesmo evento").
5. **XLSX**: abas `Resumo`, `HH por categoria`, `HH por ativo`, `Jornadas`,
   `Pausas`, `Falhas`, `Qualidade`, `Dicionário de dados`. **`HH por OS`
   não existe** — o sistema não modela OS (fora de escopo até o
   Incremento 13). `HH por ativo` é limitada aos atendimentos de falha,
   único lugar onde `ativo` existe hoje (`DadosFalha.ativo`, texto livre).
   A aba `Falhas` inclui uma coluna `completo` (todos os 6 campos
   obrigatórios da seção 3.5 preenchidos ou não) — dado de qualidade, não
   inventado, apenas reaproveita a regra já fechada do Incremento 6.
6. **GeoJSON**: `feature_collection_pontos` e `feature_collection_trajetorias`
   (com `simplificar_trajetoria` do Incremento 10, evitando arquivos
   gigantes — "não carregar pulsos brutos integralmente sem necessidade",
   docs/13). **Minimização de dados pessoais por padrão**: sem sistema de
   perfil/permissão ainda, `colaborador_matricula` só entra nas
   propriedades se `incluir_identificacao_pessoal=True` for passado
   explicitamente — o padrão é *não* incluir. É a única forma responsável
   de cumprir "aplicar minimização de dados pessoais" (docs/14) sem um
   sistema de permissão real ainda implementado.
7. **`painel/pages/2_Exportacoes.py`**: terceira página do painel
   multipage. Exige `usuario_responsavel` preenchido antes de habilitar
   qualquer download (fail closed — nenhuma exportação sai sem essa
   informação, mesmo sendo só um campo de texto livre nesta fase, sem
   validar contra uma base de usuários real).

## Deliberadamente fora deste incremento

- **Layout oficial definitivo de colunas**: os nomes/ordem de coluna aqui
  são um ponto de partida técnico, não um layout validado com a operação
  (explicitamente pendente, seção 15.3).
- **Política de auditoria da exportação** (quem exportou o quê, quando,
  registrado centralmente): o arquivo `metadados_*.json`/a aba `Resumo`
  registram usuário/timestamp/filtros *dentro da própria exportação*, mas
  não há um log central de auditoria de exportações realizadas.
- **Perfis autorizados a exportar**: qualquer pessoa com acesso ao painel
  pode gerar qualquer exportação — não há controle de acesso.
- **Dados pessoais permitidos por política**: a escolha "matrícula fora
  por padrão" é uma decisão técnica defensiva, não uma política de LGPD
  validada — precisa de revisão formal antes de produção (mesma pendência
  já registrada no ADR-0007 para GPS).
- **HH por OS**: inexistente, porque OS não é modelado ainda.

## Validação realizada

- `tests/test_exportacoes.py` (15 testes): metadados obrigatórios e
  sufixo de nome de arquivo, reconciliação exata de totais CSV/XLSX com
  `consolidacao`, marcação de atendimento de falha completo/incompleto,
  arquivos CSV+metadados gravados corretamente (incluindo com pulsos),
  todas as abas do XLSX presentes e com dados corretos, GeoJSON omitindo
  matrícula por padrão e incluindo quando pedido explicitamente,
  coordenadas no formato `[longitude, latitude]` (padrão GeoJSON),
  trajetória por jornada respeitando a simplificação e ignorando jornada
  com um único pulso, escrita de arquivo GeoJSON válido.
- **Smoke test real do servidor**: `streamlit run painel/app.py
  --server.headless true`, com dados de exemplo pré-gerados, HTTP 200
  confirmado nas três páginas (Painel, Mapa Operacional, Exportações),
  sem traceback no log.

## Validação NÃO realizada

Mesma limitação já registrada nos ADRs 4, 9 e 10: não foi possível abrir a
página de exportações em um navegador real para clicar nos botões de
download e inspecionar visualmente os arquivos gerados. A lógica de
geração de arquivo é totalmente coberta por testes unitários; a interação
via botão do Streamlit (`st.download_button`) não foi exercitada em
tempo de execução real.

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (layout oficial, dados
  pessoais permitidos, perfis, auditoria) e teste manual em navegador
  real antes de qualquer uso com dados reais.
