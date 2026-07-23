# Atendimento de falhas e RASF

## Fluxo
1. Iniciar atendimento de falha.
2. Registrar ou selecionar nota CCM.
3. Selecionar ativo na base.
4. Selecionar sintoma catalogado.
5. Executar atendimento, com pausas/deslocamentos.
6. No encerramento, informar causa, ação e observação.
7. Validar pendência, impacto e anexos quando aplicável.

## Campos mínimos obrigatórios ao encerrar
- número da nota;
- ativo;
- sintoma;
- causa;
- ação;
- observação técnica;
- horário final.

## Campos recomendados
- sistema;
- componente causador;
- tipo/impacto da falha;
- origem da atividade;
- OS relacionada;
- pendência;
- evidência;
- equipe.

## RASF como fonte
O arquivo analisado possui 3.986 registros e 77 colunas, com 53 sintomas distintos, 10 tipos de solicitação, cinco sistemas e quatro níveis de impacto. O catálogo deve ser carregado, versionado e administrado. Não usar o texto longo como única estrutura.

## Estratégia de catálogo
Preservar código e descrição originais, normalizar acentuação e espaços, manter status ativo/inativo e autoria da alteração. Valores novos entram como pendentes de governança, não diretamente no catálogo oficial.
