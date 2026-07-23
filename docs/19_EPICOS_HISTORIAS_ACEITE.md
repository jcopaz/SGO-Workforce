# Épicos, histórias e critérios de aceite

## Épico A | Jornada
Como técnico, quero iniciar e encerrar a jornada para que o sistema delimite a captura operacional.

Aceite: uma jornada aberta por usuário; offline; timestamp persistido; fila visível; encerramento com pendências explícitas.

## Épico B | Eventos e pausas
Como técnico, quero trocar de atividade e pausar com motivo para obter tempo líquido.

Aceite: sem sobreposição silenciosa; retorno ao contexto anterior; catálogo local; duração reconciliada.

## Épico C | Falha
Como técnico, quero registrar o atendimento e fechar com dados técnicos.

Aceite: nota, ativo, sintoma, causa, ação e observação obrigatórios; rascunho offline; vínculo com evento.

## Épico D | GPS
Como gestão autorizada, quero visualizar a cronologia geográfica durante a jornada.

Aceite: captura apenas em jornada; precisão registrada; lote idempotente; mapa filtrável; política de privacidade.

## Épico E | Analytics
Como PCM, quero ver capacidade e exportar HH.

Aceite: dashboards ECharts; CSV/XLSX; totais reconciliados; filtros aplicados; dicionário de dados.
