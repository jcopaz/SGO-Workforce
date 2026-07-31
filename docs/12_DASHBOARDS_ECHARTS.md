# Dashboards ECharts

## Stack
Streamlit + `streamlit-echarts`. Os dados exibidos devem vir de consultas consolidadas e filtros comuns.

## Abas
### Resumo
Cards de jornada, HH produtivo, HH deslocamento, HH pausas, falhas, ativos e qualidade de sync.

### Distribuição de HH
Sankey da jornada, barras empilhadas por categoria, série temporal e comparação planejado x realizado.

### Falhas
Top sintomas, causas, ações, sistemas, componentes, impacto, reincidência e HH consumido.

**Implementado no ADR-0029, ampliado no ADR-0031** (`painel/telas/falhas.py`):
tempo de atendimento (KPIs de total/média/maior duração/duração total,
ranking por duração), distribuição por sintoma e por objeto (componente
causador), evolução diária, HH por colaborador, duração média por
sintoma, reincidência de ativos, sunburst ativo > sintoma. Causa, ação e
sistema continuam sem tela — não são campos capturados por `DadosFalha`
hoje, mostrar essas dimensões exigiria inventar dado.

### Capacidade
Capacidade bruta, indisponibilidades, perdas, capacidade efetiva e utilização do plano.

### Qualidade
Jornadas abertas, lacunas, eventos sobrepostos, falhas sem fechamento técnico, GPS sem precisão e pendências de sync.

## Gráficos recomendados
- gauge para capacidade/utilização;
- stacked bar para HH;
- sankey para fluxo da jornada;
- treemap para causa/componente;
- heatmap para dia x hora;
- line/area para tendência;
- scatter para duração x frequência;
- sunburst para sistema > ativo > sintoma.

## Reconciliabilidade
Cada visual deve permitir drill-down ou exportação da base correspondente. Totais precisam coincidir com CSV/XLSX.

## Indicadores implementados (ADR-0027)
- **Utilização HH** (Horas Produtivas / Horas Totais): card KPI + gauge
  na aba "Visão geral" (`painel/telas/dashboard.py`), calculado a partir
  do mesmo `ResumoConsolidado` dos outros cards de HH — nunca diverge.
  Desde o ADR-0031, também por colaborador individual (bar chart).
- **Performance** (Tempo Planejado / Tempo Real): fórmula pronta em
  `workforce_core.consolidacao.performance`, mas ainda sem tela — depende
  de uma fonte de tempo planejado por atividade/OS que o sistema não tem
  (`docs/23_DECISOES_PENDENTES.md` item 14). O painel mostra um aviso
  explícito no lugar do indicador em vez de omitir o assunto.

## Rótulos legíveis e correções de layout (ADR-0031)
Todo gráfico usa `painel/dados.rotulo_categoria`/`rotulo_motivo` (nunca
`categoria.value`/código cru) e posicionamento fixo de título/legenda
(`painel/graficos._titulo_opts`/`_legenda_lateral_opts`/`_legenda_superior_opts`)
para nunca sobrepor — bug real relatado em produção com dado real (12+
categorias), nunca visível nos smoke tests com poucas categorias.
