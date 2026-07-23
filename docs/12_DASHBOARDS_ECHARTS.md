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
