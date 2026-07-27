# ADR-0014 | Catálogo real do Relatório de Atividades Diárias de Manutenção

## Contexto

Em 2026-07-23, após o primeiro teste manual da interface de campo em
navegador real, o responsável pelo produto forneceu dois documentos reais
da Gerência de Manutenção Eletroeletrônica (MRS Logística): "01. RELATÓRIO
DE ATIVIDADES.pdf" e "02. RELATÓRIO DE ATIVIDADES.pdf" — dois formulários
em papel que a equipe preenche manualmente hoje para registrar código,
início, término, número da OS e serviço executado ao longo do dia.

O responsável confirmou: **"Hoje a equipe utiliza apenas o Relatório 1"**
— ou seja, o formulário com os códigos `EE01` a `EE24` (coordenação
GEE.SP.IPA, distrito Planalto). O segundo documento (códigos numéricos
`10`–`250`, coordenação E.SP.IPA) é um formulário mais antigo, fora de uso,
e não foi incorporado a este catálogo.

Isso é exatamente o tipo de decisão que `docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`
seção 15.3 e `docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md`
deixavam como pendente ("catálogo oficial de pausas") — mas com uma
diferença importante: **isto não é o catálogo oficial final**, é o
formulário real que a equipe já usa em papel. A pedido é para alinhar a
catalogação do sistema a essa prática existente, não para validar
definitivamente produtividade/improdutividade (isso continua separado,
ver "Deliberadamente fora deste ADR").

## Decisão

### 1. Novo catálogo `catalogo_relatorio_1_manutencao()`

Adicionado em `workforce_core/catalogo.py`, com os 23 códigos catalogáveis
do Relatório 1 (`EE01`–`EE23`; `EE24` fica de fora, ver item 3). Cada
entrada usa o código e a descrição exatos do formulário — nada foi
reformulado ou abreviado. `classificacao_hh` permanece `NAO_DEFINIDO` em
todas: o código existir no formulário em papel não implica uma
classificação produtiva/improdutiva validada.

### 2. Mapeamento código a código para o modelo de domínio

Cada um dos 23 códigos foi classificado em um de três tipos de registro
(`codigos_relatorio_1_por_tipo_registro`), com a justificativa a seguir:

**`atividade`** (a atividade principal em si, não um motivo de
interrupção):
- `EE17` – Manutenção em equipamentos → `Atividade` comum (o "trabalho" que a jornada existe para fazer).
- `EE22` – Manutenção não planejada → `Atividade` com `DadosFalha` (atendimento de falha, Incremento 6) — a leitura mais natural de "não planejada" no contexto de manutenção corretiva.

**`pausa`** (interrompe uma `Atividade` em andamento, retomando o mesmo
contexto ao terminar — mesma semântica do Incremento 1/ADR-0001):
- `EE02` – Refeição 1 hora.
- `EE07` – Reunião ou ADM (os dois motivos vêm juntos no formulário; não foram desdobrados em dois códigos diferentes, para não divergir do que a equipe realmente escreve no papel).
- `EE11` – Consulta à documentação técnica (interrupção típica no meio da execução, não uma espera por terceiros).
- `EE21` – SMS (Segurança/Meio Ambiente/Saúde — o formulário real usa "SMS", não "DDS"; `Categoria.DDS`, citada em `docs/07`, permanece no enum mas nenhum código do Relatório 1 a usa hoje).
- `EE23` – Treinamento.

**`evento_secundario`** (vinculado à Jornada, não a uma Atividade
específica — mutuamente exclusivo com a atividade principal, mesma regra
do Incremento 5/ADR-0005 "apenas um evento principal ativo"):
- `EE01` – Preparação para jornada (acontece antes de qualquer atividade começar).
- `EE03` – Aguardando CCO, `EE05` – Trem parado na frente de serviço, `EE06` – Restrição de infraestrutura, `EE09` – Trabalho não distribuído, `EE10` – Aguardando sequência de serviço → todas são esperas por algo externo à equipe, mesma natureza de `EE04` (Falta de ferramenta ou material, já mapeado para `AGUARDANDO_MATERIAL` desde o ADR-0005).
- `EE08` – Serviço interno da coordenação, `EE15` – Preparar atividade, `EE16` – Desmontar atividade, `EE18` – Suporte da manutenção, `EE19` – Carregar veículo, `EE20` – Descarregar veículo → apoio operacional: acontecem como blocos de tempo próprios, com início/término e Nº OS próprios no formulário, não aninhados dentro de uma atividade em andamento.
- `EE12`/`EE13`/`EE14` – Deslocamento rodoviário/ferroviário/a pé → os três tipos de deslocamento (`EE14` exigiu uma categoria nova, `DESLOCAMENTO_A_PE`, que não existia até este ADR).

### 3. `EE24` (Horas não apontadas) não vira entrada de catálogo

No formulário em papel, `EE24` é usado quando o funcionário não sabe (ou
não quer) categorizar o tempo. No motor de domínio, isso **já existe
automaticamente**: é o `tempo_nao_classificado` calculado por
`workforce_core.calculo` a partir das lacunas entre eventos registrados —
não algo que alguém escolhe ativamente ao iniciar um evento. Criar uma
entrada de catálogo "EE24" e permitir que o colaborador a selecione ativa
e conscientemente contradiria o próprio ponto do cálculo automático:
a diferença entre "nada foi registrado" (inferido) e "o colaborador
escolheu declarar que não sabe o que fez" (declarado) é uma distinção que
já existe estruturalmente e não precisa de um código de motivo.

### 4. Interface de campo: só os 5 códigos de `pausa` foram conectados

`interface_campo/js/app.js` — o seletor de motivo de pausa agora mostra os
5 códigos reais (`EE02`, `EE07`, `EE11`, `EE21`, `EE23`), com o rótulo
exato do formulário. Os 16 códigos `evento_secundario` **não** foram
conectados à interface nesta sessão — a interface de campo (JavaScript)
nunca teve `EventoSecundario`/Deslocamento/Espera/Apoio implementados
(decisão explícita do ADR-0004/ADR-0005: "sem UI exercitando a
funcionalidade, sem risco imediato de divergência"). Adicionar 16 opções
de evento secundário exigiria antes portar `EventoSecundario` para
`motorJornada.js`/`calculo.js`/`armazenamento.js` (mutuamente exclusivo com
atividade, novas transições, nova tela) — um trabalho do tamanho de um
incremento próprio, não uma extensão do seletor de pausa existente.

## Deliberadamente fora deste ADR

- **Classificação produtiva/improdutiva/não computável de cada código**:
  continua `NAO_DEFINIDO` para todos os 23. O formulário em papel não
  define isso — só define que o tempo é rastreado com aquele código.
- **Porte de Deslocamento/Espera/Apoio para a interface de campo**: os 16
  códigos `evento_secundario` estão catalogados no lado Python, prontos
  para uso (ex.: em exportações, consolidação), mas sem tela na interface.
  Fica como próximo passo natural, não implementado aqui.
- **Campo "Nº OS" em Pausa/EventoSecundario**: o formulário real vincula
  cada linha (mesmo uma pausa ou deslocamento) a um número de OS. Hoje só
  `DadosFalha` carrega `os_referencia` (Incremento 13). Estender isso a
  `Pausa`/`EventoSecundario` é uma mudança de modelo maior, sinalizada mas
  não decidida/implementada nesta sessão.
- **Coordenação/distrito/equipe** (campos do cabeçalho do formulário): não
  modelados no sistema ainda (mesma lacuna já registrada nos ADRs
  anteriores para filtros de mapa/painel).
- **O segundo relatório (códigos 10–250)**: fora de uso confirmado pelo
  responsável pelo produto — não incorporado a este catálogo.

## Alternativas consideradas

- **Manter os motivos de exemplo do ADR-0005 (Refeição, DDS, Reunião,
  Treinamento) em vez de trocar pelos códigos reais**: rejeitado agora que
  existe uma fonte real — manter os exemplos genéricos seria ignorar um
  dado concreto oferecido pelo responsável pelo produto.
- **Desdobrar "EE07 – Reunião ou ADM" em dois códigos separados**:
  rejeitado para não divergir do que a equipe realmente escreve no papel;
  pode ser revisto se a operação um dia quiser essa granularidade.
- **Tratar todos os 23 códigos como `pausa`, ignorando a distinção com
  `evento_secundario`**: rejeitado — misturar deslocamento/espera/apoio
  (que hoje são mutuamente exclusivos com a atividade principal) dentro do
  conceito de pausa (que pressupõe uma atividade em andamento)
  contradiria a própria regra "apenas um evento principal ativo" já
  registrada no ADR-0005.

## Validação operacional

Ainda não realizada quanto à classificação de HH de cada código. O
mapeamento estrutural (pausa vs. evento secundário vs. atividade) é uma
interpretação de quem implementou, não confirmada linha a linha com o
responsável pelo produto — sujeita a correção.

## Atualização (2026-07-27) — reclassificação e renumeração (ADR-0023)

A classificação de HH pendente acima foi resolvida: o responsável pelo
produto validou `classificacao_hh` código a código. Nesse processo,
identificou que o antigo `EE18` ("Suporte da manutenção") duplicava o que
já era `EE22` ("Manutenção não planejada") e pediu a exclusão de um dos
dois — mantido o que hoje é `EE21` ("Atendimento de Falha", a base de
toda a funcionalidade construída desde o ADR-0006). Isso deslizou os
códigos `EE19`-`EE24` uma posição, e um código novo, `EE23` ("Manutenção
Programada Não Concluída"), passou a existir. `EE17` e `EE22` (agora
`EE21`) também tiveram a descrição atualizada para o texto atual do
formulário. A tabela completa e atualizada está em
`docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md` — a numeração
citada no restante deste documento (contexto histórico de 2026-07-23)
não reflete mais os códigos atuais de `EE18` em diante.

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, a partir dos documentos fornecidos pelo
  responsável pelo produto (j.copaz@hotmail.com).
- Revisão pendente: responsável pelo produto (confirmar o mapeamento
  código a código, especialmente os casos de julgamento como `EE07`,
  `EE11`, `EE15`/`EE16`) e decisão sobre portar Deslocamento/Espera/Apoio
  para a interface de campo.
