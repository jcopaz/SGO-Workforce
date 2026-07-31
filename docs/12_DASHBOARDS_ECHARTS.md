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

**Implementado parcialmente no ADR-0029** (`painel/telas/falhas.py`):
tempo de atendimento (KPIs de total/média/maior duração/duração total,
ranking por duração, distribuição por sintoma, contagem por ativo).
Causa, ação, sistemas, componentes, impacto e reincidência continuam sem
tela.

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
- **Performance** (Tempo Planejado / Tempo Real): fórmula pronta em
  `workforce_core.consolidacao.performance`, mas ainda sem tela — depende
  de uma fonte de tempo planejado por atividade/OS que o sistema não tem
  (`docs/23_DECISOES_PENDENTES.md` item 14). O painel mostra um aviso
  explícito no lugar do indicador em vez de omitir o assunto.
