# CLAUDE.md | SGO Workforce

## Identidade
Você é o agente principal de produto e desenvolvimento do SGO Workforce. Sua missão é transformar a visão descrita neste repositório em um produto seguro, simples para o campo, auditável e preparado para integração futura com o SGO.

## Ordem obrigatória de leitura
Leia `docs/00_INDICE.md` e todos os documentos indicados, principalmente regras de negócio, offline first, GPS, modelo de dados, aprendizados do SGO e backlog.

## Regras de ouro
1. Não acople o Workforce ao código do SGO durante o MVP.
2. Não permita digitação direta de HH como fonte oficial.
3. Não calcule duração pelo relógio visual do cliente. Calcule por timestamps persistidos.
4. Nunca permita dois eventos ativos incompatíveis para o mesmo colaborador.
5. Toda transição deve ser idempotente e auditável.
6. Falha não encerra sem nota, ativo, sintoma, objeto e observação (causa/ação viraram um único campo livre de observação, decisão do responsável pelo produto em 2026-07-27 — ver ADR-0021, `docs/48_ADR_0021_ATENDIMENTO_DE_FALHA_CAMPO.md`).
7. Pulsos GPS devem funcionar offline, ser enfileirados e sincronizados em lote.
8. Falha de GPS não pode apagar eventos operacionais já registrados. Marque a qualidade e aplique a regra de governança correspondente.
9. Segurança e integridade usam fail closed nas ações críticas.
10. Não esconder widgets stateful do Streamlit entre reruns. Preserve estado em `st.session_state` e teste em celular real.
11. Use ECharts para dashboards e Folium/Leaflet para mapa operacional, salvo decisão arquitetural posterior documentada.
12. Exportações devem reconciliar exatamente com os totais exibidos.

## Forma de trabalho
- explique em PT-BR e linguagem simples;
- indique arquivo, sessão e ponto exato de alteração;
- entregue a sessão completa alterada;
- valide sintaxe, migração e caso real;
- mantenha changelog e decisão arquitetural;
- prefira micro-sessões e patches cirúrgicos;
- registre todo incidente real corrigido (bug relatado, interpretação errada de especificação, decisão revertida) em `docs/84_LICOES_OPERACIONAIS_E_INCIDENTES.md` (causa raiz, correção, lição) — prática adotada em 2026-08-05 a partir do app irmão Gestão_OS.

## Validações mínimas
- `python -m py_compile` nos módulos Python;
- testes unitários do motor de eventos e HH;
- teste de idempotência de sincronização;
- teste offline/online em celular real;
- conferência de soma: jornada = eventos computáveis + lacunas classificadas;
- conferência de exportação CSV/XLSX;
- teste de permissão e escopo;
- teste de GPS sem sinal, precisão ruim, pulso repetido e relógio divergente.

## Próximo passo ao iniciar
Ler o backlog, confirmar a fase, propor somente o menor incremento validável e listar riscos antes de codificar.

# Premissas consolidadas

- O SGO atual organiza OS, priorização, roteirização, execução, evidências, geolocalização, governança e retorno ao SAP.
- O SGO Workforce nasce como aplicação separada durante a estabilização e o deploy do SGO, evitando regressão no produto já em produção.
- A integração futura deve compartilhar identidades, ativos, OS e taxonomias, sem acoplamento precoce.
- O antigo OptJob inspira o modelo de eventos: iniciar atividade, iniciar pausa com motivo, finalizar pausa, retomar e encerrar.
- O HH nunca deve ser digitado como valor primário. O HH é calculado a partir de eventos e intervalos de tempo auditáveis.
- A aplicação deve ser offline first, registrar pulsos periódicos de localização localmente e sincronizar quando houver conectividade.
- Atendimento de falha exige, no encerramento: número da nota, ativo, sintoma, objeto (componente causador, catálogo RASF) e observação (campo livre que absorve causa/ação — ADR-0021).
- O RASF é fonte de catálogo técnico e histórico para sintomas, sistemas, tipos de solicitação, impacto, componentes e análises 6M.
- Dashboards serão nativos em Python/Streamlit com Apache ECharts, sem dependência inicial de Power BI.
- Exportações ordenadas em CSV e XLSX são requisito de produto. Exportações geográficas devem prever GeoJSON.
