# Identidade e missão

## Nome
SGO Workforce.

## Definição
Plataforma de gestão de jornada, esforço operacional, telemetria de campo, falhas e capacidade da manutenção eletroeletrônica.

## Missão
Converter eventos reais da operação em HH confiável, conhecimento técnico e capacidade útil para PCM, coordenação, engenharia e gerência.

## O produto não é
- relógio de ponto;
- ferramenta de vigilância individual;
- substituto do SAP;
- substituto imediato do SGO;
- formulário manual de HH;
- réplica literal do antigo OptJob.

## Proposta de valor
O SGO responde o que executar, onde, quando e com qual prioridade. O Workforce explica quanto esforço foi consumido, como o tempo se distribuiu, onde a equipe atuou, quais falhas consumiram capacidade e qual HH efetivo pode sustentar o plano.

# Premissas consolidadas

- O SGO atual organiza OS, priorização, roteirização, execução, evidências, geolocalização, governança e retorno ao SAP.
- O SGO Workforce nasce como aplicação separada durante a estabilização e o deploy do SGO, evitando regressão no produto já em produção.
- A integração futura deve compartilhar identidades, ativos, OS e taxonomias, sem acoplamento precoce.
- O antigo OptJob inspira o modelo de eventos: iniciar atividade, iniciar pausa com motivo, finalizar pausa, retomar e encerrar.
- O HH nunca deve ser digitado como valor primário. O HH é calculado a partir de eventos e intervalos de tempo auditáveis.
- A aplicação deve ser offline first, registrar pulsos periódicos de localização localmente e sincronizar quando houver conectividade.
- Atendimento de falha exige, no encerramento: número da nota, ativo, sintoma, causa, ação e observação.
- O RASF é fonte de catálogo técnico e histórico para sintomas, sistemas, tipos de solicitação, impacto, componentes e análises 6M.
- Dashboards serão nativos em Python/Streamlit com Apache ECharts, sem dependência inicial de Power BI.
- Exportações ordenadas em CSV e XLSX são requisito de produto. Exportações geográficas devem prever GeoJSON.
