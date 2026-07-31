# Aprendizados herdados do SGO

- Validar causa raiz com SQL/log e dado real.
- Segurança usa fail closed.
- Não criar filtros redundantes baseados em texto.
- Chave de conflito deve usar o identificador real.
- Datas operacionais não devem ser VARCHAR.
- Pin de dependências e Python suportado.
- Teste unitário não substitui teste em celular.
- Não remover widget stateful da árvore entre reruns.
- Offline exige idempotência e preservação do histórico sincronizado.
- Métrica zerada/anômala é alerta prioritário.
- Mudança grande vai para dev/homologação, nunca direto à produção.

## Aprendizados extraídos dos manuais originais do OptJob (2026-07-30)

Leitura completa dos 27 PDFs em `Referencias/` (procedimentos operacionais
do OptJob MF/Via Permanente, o sistema que o Workforce está substituindo).
São procedimentos de tela, não documentação de indicadores — nenhuma
fórmula de "Utilização de HH" ou "Performance" foi encontrada neles
(provavelmente vivia em relatórios Discoverer/EBS não fornecidos). O que
segue são achados operacionais confirmados por texto real dos manuais,
não suposição.

- **Motivação histórica confirmada para a Regra de Ouro nº 5** ("toda
  transição deve ser idempotente e auditável"): o OptJob desktop tinha
  exclusão real de apontamento (`Tutorial - Exclusão de Apontamento`) —
  um "x" na linha "PAUSA INICIADA" com uma justificativa de dropdown, e o
  registro some da lista, sem flag de correção nem preservação do evento
  original.
- **Motivação histórica confirmada para a Regra de Ouro nº 2** (não
  digitar HH direto): existia "Produção Complementar", um campo desktop
  onde o admin digitava manualmente um intervalo De/Até estendendo a
  jornada de um colaborador além do turno programado.
- Sincronização no OptJob era **manual e esquecível** (4 botões — OS,
  Calendário, Apontamentos, Solicitações — só no início/fim de turno, sem
  sync automático em segundo plano). O Workforce já mitiga isso com sync
  automático best-effort (`docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md`)
  — validação de que essa escolha de arquitetura foi acertada.
- A taxonomia original do OptJob (`Códigos de Pausas com Figuras
  produção_Via v6`) usa **5 níveis de "Tipo de Hora"**: HORAS PRESENTES
  PRODUTIVAS, HORAS PRESENTES PRODUTIVAS NÃO RENTÁVEIS, HORAS PRESENTES
  IMPRODUTIVAS, HORAS AUSENTES, HORAS NÃO APONTADAS — o Workforce hoje
  (`ClassificacaoHH`) tem só `PRODUTIVA/IMPRODUTIVA/NAO_COMPUTAVEL/NAO_DEFINIDO`,
  sem a distinção "produtiva mas não rentável" (que no original cobria
  deslocamento, preparar/desmontar atividade, carregar/descarregar
  veículo, SMS, manutenção não planejada e treinamento). Registrado como
  decisão pendente em `docs/23_DECISOES_PENDENTES.md` item 15/16 — **não
  alterado no código**, porque `ClassificacaoHH` já foi validada código a
  código pelo responsável do produto (ADR-0023) e mudá-la exige nova
  validação dele, não inferência do agente.
- Os 23 códigos EE01-EE23 do catálogo real (ADR-0014) quase certamente
  herdam o vocabulário do OptJob Via Permanente (nomes praticamente
  idênticos: "Aguardando CCO", "Trem parado na frente de serviço",
  "Consulta a documentação técnica" etc.), mas a fonte declarada no
  ADR-0014 é um formulário em papel ("Relatório de Atividades") fornecido
  separadamente pelo responsável do produto, não este manual digital —
  são linhagens próximas, não a mesma fonte.
- Atenção a uma ambiguidade de sigla: "EE" em
  `Instruções para Abertura de SS para EE` = **Equipamentos
  Eletroeletrônicos** (tipo de ativo/SS dentro do OptJob), diferente do
  prefixo "EE" dos códigos EE01-EE23 do Workforce (numeração sequencial
  do formulário em papel). Não confundir os dois em documentação futura.
- O OptJob apontava por **equipe inteira** (Colaborador único / Equipe
  MRS / Equipe de Terceiros como headcount), não por indivíduo desde o
  início. O Workforce optou por granularidade individual — registrado
  aqui como decisão deliberada (mais precisa para HH real), não lacuna.
