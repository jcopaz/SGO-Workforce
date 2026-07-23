# 27 | Alinhamento Oficial do Produto e Diretriz de Implementação

## SGO Workforce

**Versão:** 1.1  
**Data de consolidação:** 22/07/2026  
**Status:** Alinhamento oficial vigente para o início do projeto  
**Finalidade:** consolidar o entendimento correto do produto, definir o primeiro incremento técnico e registrar a decisão provisória de modelagem das pausas.  
**Uso obrigatório:** Claude Code, GitHub Copilot, Copilot Studio, VS Code e qualquer pessoa que participe da concepção ou implementação do SGO Workforce.

---

# 1. O que é o SGO Workforce

O **SGO Workforce** é uma plataforma de gestão de jornada, esforço operacional, telemetria de campo, atendimento de falhas e capacidade da manutenção eletroeletrônica.

O produto deverá transformar eventos reais da operação em:

- HH calculado e auditável;
- distribuição do tempo por categoria;
- tempo bruto e líquido de execução de atividades e OS;
- histórico estruturado de falhas;
- informação geográfica da atuação em campo;
- indicadores para coordenação, engenharia, PCM e gerência;
- dados ordenados para exportação CSV e XLSX;
- dados geográficos preparados para futura exportação GeoJSON;
- capacidade operacional observada para apoiar o Plano de Manutenção.

O colaborador não deverá informar manualmente quantas horas trabalhou. O colaborador registrará acontecimentos operacionais, como início de jornada, atividade, pausa, deslocamento, atendimento de falha e encerramento. O sistema calculará o HH com base nos timestamps persistidos desses eventos.

## Princípio central

> O colaborador aponta eventos. O sistema calcula o HH.

O SGO Workforce não é:

- um relógio de ponto;
- uma ferramenta de vigilância individual;
- um formulário manual de horas;
- um substituto do SAP;
- uma substituição imediata do SGO atual;
- uma cópia literal do antigo OptJob.

O antigo OptJob é uma referência conceitual para o apontamento por eventos. O SGO Workforce amplia esse conceito com operação offline, sincronização idempotente, pulsos GPS, falhas estruturadas, mapas, dashboards ECharts, exportações e capacidade operacional.

---

# 2. O que diferencia o SGO Workforce do SGO atual

## 2.1 SGO atual

O SGO atual é a plataforma de inteligência operacional que organiza:

- carga e tratamento das OS do SAP;
- planejamento e priorização;
- roteirização por proximidade;
- execução em campo;
- GPS e geofence;
- evidências fotográficas;
- governança;
- modo offline de contingência;
- retorno estruturado ao SAP/IW47.

O SGO responde principalmente:

- O que precisa ser executado?
- Onde a atividade será executada?
- Quando deve ser executada?
- Qual é a prioridade?
- Qual OS foi concluída?
- Qual evidência comprova a execução?

## 2.2 SGO Workforce

O SGO Workforce complementará o ecossistema com:

- jornada operacional;
- atividades contínuas;
- pausas catalogadas;
- deslocamentos;
- esperas e apoios;
- atendimento estruturado de falhas;
- pulsos periódicos de localização;
- cálculo automático de HH;
- tempo líquido de execução;
- histórico técnico de sintoma, causa e ação;
- mapa de permanência e atuação;
- dashboards nativos em Apache ECharts;
- exportações estruturadas;
- capacidade efetiva para o PCM.

O Workforce responderá principalmente:

- Quanto esforço foi consumido?
- Como o tempo da jornada foi distribuído?
- Quanto tempo líquido foi aplicado em cada OS?
- Quanto tempo foi consumido em deslocamento, espera, apoio e pausa?
- Quais falhas, ativos e regiões consomem mais capacidade?
- Qual HH efetivo está disponível para o plano?

## 2.3 Relação entre os produtos

```text
SGO = Gestão e inteligência da execução das OS

SGO Workforce = Gestão da jornada, do HH e da capacidade operacional
```

Os produtos são complementares, mas permanecerão separados durante o MVP do Workforce.

---

# 3. Regras inegociáveis

## 3.1 Separação inicial

- Não inserir o Workforce diretamente no código do SGO durante o MVP.
- Não modificar o `app.py`, `api.py`, banco ou PWA do SGO para iniciar o Workforce.
- O Workforce deverá possuir repositório, aplicação, API, ambiente e domínio próprios.
- A integração futura deverá ocorrer por contratos definidos e versionados.

## 3.2 HH e tempo

- HH não poderá ser digitado manualmente como fonte oficial.
- O relógio visual da tela não será a fonte oficial do tempo.
- O tempo oficial deverá vir de timestamps persistidos.
- Datas operacionais deverão usar timestamps com timezone, preferencialmente armazenados em UTC e exibidos em `America/Sao_Paulo`.
- Toda correção posterior deverá manter o valor anterior, o novo valor, o responsável e a justificativa.

## 3.3 Jornada e eventos

- Um colaborador poderá ter apenas uma jornada aberta por vez.
- Um colaborador poderá ter apenas uma atividade principal ativa por vez.
- Um colaborador poderá ter apenas uma pausa ativa por vez.
- Sobreposições incompatíveis deverão ser bloqueadas ou encaminhadas para auditoria.
- Encerrar uma jornada com evento aberto exigirá tratamento explícito, nunca encerramento silencioso.
- O sistema deverá identificar tempo não classificado dentro da jornada.

## 3.4 Offline first

- Jornada, atividade, pausa, deslocamento e falha deverão funcionar sem internet nas fases correspondentes.
- Registros locais não poderão ser perdidos ao fechar ou reiniciar a aplicação.
- Cada registro deverá possuir UUID criado no cliente.
- A sincronização deverá ser idempotente.
- O reenvio do mesmo registro não poderá gerar duplicidade.
- A fila deverá mostrar registros pendentes, sincronizados, com erro e em conflito.
- Conflitos não poderão ser resolvidos silenciosamente.

## 3.5 Atendimento de falha

Um atendimento de falha não poderá ser encerrado sem os campos obrigatórios definidos para o MVP:

- número da nota da falha, geralmente originada pelo CCM;
- ativo selecionado na base de ativos;
- sintoma;
- causa;
- ação;
- observação técnica;
- horário final do atendimento.

Campos recomendados para evolução:

- sistema;
- componente causador;
- tipo ou impacto da falha;
- origem da atividade;
- OS relacionada;
- pendência;
- equipe;
- evidência.

## 3.6 GPS e pulsos

- A captura de pulsos deverá ocorrer somente dentro da jornada ativa e conforme política corporativa aprovada.
- Todo pulso deverá registrar timestamp, latitude, longitude e precisão.
- A precisão original não deverá ser descartada.
- Falha de GPS não deverá apagar eventos operacionais já registrados.
- GPS inválido deverá gerar informação de qualidade, contingência ou bloqueio conforme decisão de negócio.
- Permanência e deslocamento inferidos por GPS deverão ser identificados como inferências, não como prova absoluta.
- O uso em produção dependerá de validação de LGPD, segurança da informação, política corporativa e relações trabalhistas.

## 3.7 Dashboards e exportações

- Os dashboards serão construídos no próprio Python/Streamlit com Apache ECharts.
- O Power BI não será dependência do MVP.
- Mapas utilizarão inicialmente Folium/Leaflet, salvo decisão arquitetural documentada.
- Totais dos dashboards deverão reconciliar com as exportações.
- CSV e XLSX deverão respeitar os filtros aplicados.
- Toda exportação deverá possuir data de geração, período, filtros e usuário responsável.

## 3.8 Segurança e qualidade

- Ações críticas deverão seguir o princípio fail closed.
- SQL deverá ser parametrizado.
- Segredos não poderão ser versionados.
- Dependências deverão ter faixas ou versões validadas.
- Mudanças relevantes deverão passar por desenvolvimento e homologação.
- Teste unitário não substituirá teste em celular real.
- Widgets stateful do Streamlit não deverão desaparecer entre reruns sem validação específica.

---

# 4. Arquitetura prevista

## 4.1 Aplicação de captura

PWA instalável para celular ou tablet, contendo:

- HTML, CSS e JavaScript;
- Service Worker;
- IndexedDB;
- geolocalização do navegador;
- fila local de sincronização;
- cache de catálogos;
- estado atual da jornada;
- registro offline de eventos e falhas.

## 4.2 Painel gerencial

Streamlit para:

- administração;
- dashboards ECharts;
- mapa operacional;
- consultas;
- qualidade dos dados;
- exportações CSV/XLSX;
- capacidade PCM.

## 4.3 API

FastAPI para:

- autenticação técnica do cliente;
- sincronização idempotente;
- recebimento de jornadas;
- recebimento de eventos;
- recebimento de falhas;
- recebimento de pulsos GPS em lote;
- distribuição de catálogos;
- futura integração com SGO.

## 4.4 Banco de dados

PostgreSQL/Neon no MVP, com tabelas próprias do Workforce.

Entidades principais:

- jornadas;
- eventos;
- participantes;
- falhas;
- pulsos GPS;
- catálogos;
- snapshots de OS e ativos;
- lotes de sincronização;
- auditoria.

## 4.5 Armazenamento de anexos

Supabase Storage poderá ser utilizado quando houver necessidade de evidência ou anexo, sem tornar anexos obrigatórios antes da validação do fluxo principal.

## 4.6 Analytics

Apache ECharts para:

- distribuição de HH;
- fluxo da jornada;
- falhas por sintoma, causa, ação e ativo;
- capacidade operacional;
- qualidade da sincronização;
- tendências e reincidências.

## 4.7 Mapa

Folium/Leaflet para:

- pinos de eventos;
- falhas;
- trajetória simplificada;
- clusters de permanência;
- heatmap de HH;
- filtros por período, colaborador, equipe, ativo, pátio e categoria.

---

# 5. Decisão provisória de domínio: modelagem da pausa

## 5.1 Status da decisão

Esta decisão é **provisória e válida para o primeiro incremento técnico**. A decisão deverá ser registrada posteriormente em ADR e validada operacionalmente antes de sua adoção definitiva no produto.

## 5.2 Modelo adotado

A pausa será modelada como um **evento próprio vinculado à atividade principal**.

```text
JORNADA
|
+-- ATIVIDADE
|   +-- início: 08:10
|   +-- fim: 12:00
|
+-- PAUSA
    +-- início: 10:00
    +-- fim: 10:20
    +-- atividade_referencia: ATIVIDADE
```

## 5.3 Regras provisórias

1. A atividade preservará o intervalo bruto entre início e fim.
2. A pausa possuirá início e fim próprios.
3. A pausa referenciará a atividade que estava em andamento.
4. A duração da pausa será descontada da duração bruta da atividade.
5. Ao finalizar a pausa, o sistema retornará ao contexto da atividade anterior.
6. Apenas uma atividade principal poderá estar ativa por vez.
7. Apenas uma pausa poderá estar ativa por vez.
8. Não será permitido iniciar outra atividade durante uma pausa.
9. Não será permitido encerrar a atividade enquanto houver pausa aberta.
10. Não será permitido encerrar a jornada enquanto houver pausa aberta.
11. Pausas não poderão se sobrepor.
12. O motivo da pausa será obrigatório.
13. Para o primeiro teste, será utilizado o motivo `PAUSA_TESTE`.
14. Toda duração será calculada por timestamps persistidos.

## 5.4 Cálculo no modelo provisório

```text
Atividade bruta = fim da atividade - início da atividade

Pausa = fim da pausa - início da pausa

Atividade líquida = atividade bruta - soma das pausas descontáveis vinculadas
```

## 5.5 Motivo da escolha

O modelo preserva simultaneamente:

- o período bruto em que a atividade esteve em andamento;
- a interrupção ocorrida dentro desse período;
- o motivo da interrupção;
- o retorno automático ao contexto anterior;
- a rastreabilidade necessária para timeline, dashboard e exportação.

## 5.6 Limites da decisão

Esta decisão não define ainda:

- o catálogo oficial de pausas;
- quais pausas serão descontáveis;
- quais pausas serão produtivas ou improdutivas;
- quais pausas entrarão no cálculo de capacidade;
- regras trabalhistas ou corporativas;
- pausas sem atividade principal em andamento;
- comportamento final em encerramento forçado.

Esses pontos permanecerão pendentes de validação operacional.

---

# 6. Decisões de negócio ainda pendentes

O agente não deverá inventar respostas para os itens abaixo. Cada decisão deverá ser validada operacionalmente e registrada em ADR.

1. Intervalo padrão dos pulsos GPS.
2. Estratégia de adaptação do pulso por movimento ou bateria.
3. Política de retenção e acesso aos dados de localização.
4. Obrigatoriedade de GPS para iniciar e encerrar eventos.
5. Regra de contingência quando o GPS estiver indisponível.
6. Catálogo oficial de pausas.
7. Regra de cômputo de cada pausa.
8. Classificação de pausas produtivas, improdutivas e não computáveis.
9. Regra final de pausa sem atividade principal em andamento.
10. Fonte oficial de escala e capacidade bruta.
11. Regra para múltiplas OS no mesmo evento.
12. Regra de rateio entre várias OS.
13. Obrigatoriedade de evidência fotográfica no atendimento de falha.
14. Grau de detalhe do mapa por perfil.
15. Hospedagem e autenticação do piloto.
16. Processo de aprovação de novos sintomas, causas e ações.
17. Periodicidade e método de atualização do RASF.
18. Critérios para classificar tempo não apontado.
19. Política para edição posterior de eventos.
20. Perfis autorizados a corrigir eventos.
21. Perfis autorizados a visualizar trajetórias individuais.
22. Retenção local dos registros após sincronização.
23. Regra de encerramento forçado de atividade ou jornada.

---

# 7. Primeiro incremento técnico validável

## 7.1 Diretriz oficial

O primeiro incremento não deverá incluir login, Streamlit, PWA, IndexedDB, FastAPI, PostgreSQL, GPS, RASF, dashboards, mapa, exportações ou integração com o SGO.

O primeiro incremento deverá validar somente o coração do produto:

```text
Motor de Jornada + Atividade + Pausa + HH
```

## 7.2 Escopo

- entidade Jornada;
- entidade Atividade;
- entidade Pausa;
- início de jornada;
- início de atividade;
- início de pausa;
- finalização da pausa;
- retorno ao contexto da atividade;
- encerramento da atividade;
- encerramento da jornada;
- máquina de estados;
- bloqueio de sobreposição;
- cálculo de duração bruta;
- cálculo de pausas;
- cálculo de duração líquida;
- cálculo de tempo não classificado;
- testes unitários.

## 7.3 Caso mínimo obrigatório

```text
08:00  início da jornada
08:10  início da atividade
10:00  início da pausa
10:20  final da pausa
12:00  final da atividade
12:10  final da jornada
```

## 7.4 Resultado esperado

```text
Jornada bruta:          4h10
Atividade bruta:        3h50
Pausa:                  0h20
Atividade líquida:      3h30
Tempo não classificado: 0h20
```

## 7.5 Demonstração do cálculo

```text
Jornada bruta:
12:10 - 08:00 = 4h10

Atividade bruta:
12:00 - 08:10 = 3h50

Pausa:
10:20 - 10:00 = 0h20

Atividade líquida:
3h50 - 0h20 = 3h30

Tempo classificado na jornada:
Atividade líquida 3h30 + Pausa 0h20 = 3h50

Tempo não classificado:
4h10 - 3h50 = 0h20
```

## 7.6 Fora do primeiro incremento

- banco de produção;
- interface gráfica;
- autenticação;
- PWA;
- IndexedDB;
- API;
- sincronização;
- deslocamentos;
- atendimento de falhas;
- RASF;
- GPS;
- mapas;
- ECharts;
- exportações;
- PCM;
- integração com SGO;
- múltiplas OS;
- rateio de HH;
- edição posterior por usuários.

## 7.7 Justificativa

O domínio deverá ser validado isoladamente antes de misturar interface, persistência, offline e backend. Isso facilitará identificar erros na regra de cálculo e evitará construir uma aplicação complexa sobre um motor de HH incorreto.

---

# 8. Estados e transições esperados no primeiro incremento

## 8.1 Jornada

Estados mínimos:

```text
NÃO_INICIADA
ABERTA
ENCERRADA
```

Transições permitidas:

```text
NÃO_INICIADA -> ABERTA
ABERTA -> ENCERRADA
```

Restrições:

- não iniciar uma segunda jornada aberta;
- não encerrar jornada com pausa aberta;
- não encerrar jornada com atividade aberta sem tratamento explícito;
- não alterar o intervalo encerrado sem fluxo futuro de correção auditada.

## 8.2 Atividade

Estados mínimos:

```text
CRIADA
ATIVA
PAUSADA
ENCERRADA
```

Transições permitidas:

```text
CRIADA -> ATIVA
ATIVA -> PAUSADA
PAUSADA -> ATIVA
ATIVA -> ENCERRADA
```

Restrições:

- atividade exige jornada aberta;
- não iniciar segunda atividade principal;
- não encerrar atividade durante pausa aberta;
- fim não pode ser anterior ao início.

## 8.3 Pausa

Estados mínimos:

```text
CRIADA
ATIVA
ENCERRADA
```

Transições permitidas:

```text
CRIADA -> ATIVA
ATIVA -> ENCERRADA
```

Restrições:

- pausa exige jornada aberta;
- no primeiro incremento, pausa exige atividade ativa;
- motivo obrigatório;
- não iniciar segunda pausa;
- fim não pode ser anterior ao início;
- pausa deve estar contida no intervalo bruto da atividade.

---

# 9. Casos de teste obrigatórios do primeiro incremento

## 9.1 Fluxo nominal

Caso mínimo descrito na seção 7.

## 9.2 Jornada sem atividade

Validar jornada aberta e encerrada sem atividade, classificando todo o intervalo como tempo não classificado.

## 9.3 Atividade sem pausa

Validar que duração líquida seja igual à duração bruta.

## 9.4 Atividade com uma pausa

Validar o desconto correto da pausa.

## 9.5 Atividade com várias pausas sequenciais

Validar a soma das pausas e o desconto total.

## 9.6 Tentativa de segunda atividade

Bloquear início de nova atividade quando já existir atividade principal ativa.

## 9.7 Tentativa de segunda pausa

Bloquear início de nova pausa quando já existir pausa ativa.

## 9.8 Encerramento da atividade durante pausa

Bloquear e apresentar regra violada.

## 9.9 Encerramento da jornada durante pausa

Bloquear e apresentar regra violada.

## 9.10 Timestamp inválido

Bloquear fim anterior ao início.

## 9.11 Pausa fora do intervalo da atividade

Bloquear pausa iniciada antes da atividade ou encerrada depois da atividade.

## 9.12 Evento atravessando meia-noite

Validar cálculo correto em datas diferentes.

## 9.13 Duplicidade de comando

Validar que a repetição da mesma transição não gere estado inconsistente.

---

# 10. Como a aplicação será construída separada do SGO e unificada posteriormente

## 10.1 Separação inicial

O SGO Workforce começará com:

- repositório Git próprio;
- pasta e ambiente virtual próprios;
- aplicação própria;
- API própria;
- banco ou schema logicamente isolado;
- migrations próprias;
- deploy próprio;
- documentação própria;
- branch `dev` para desenvolvimento;
- homologação antes de produção.

O Workforce não será criado como uma nova aba no `app.py` do SGO durante o MVP.

## 10.2 Razões para a separação

- O SGO está em processo de estabilização e deploy.
- O Workforce introduz riscos novos: jornada contínua, offline, localização periódica e sincronização em lote.
- Um erro no Workforce não poderá interromper a conclusão de OS no SGO.
- A separação permitirá testar com grupo piloto e evoluir rapidamente.
- O domínio do Workforce precisará amadurecer antes da fusão visual.

## 10.3 Preparação para integração desde o início

Mesmo separado, o Workforce deverá preservar chaves compatíveis:

- matrícula do usuário;
- código da coordenação;
- número da OS;
- referência do ciclo ou plano da OS;
- identificador do ativo;
- código do pátio;
- taxonomias técnicas;
- timestamps padronizados.

A OS não poderá ser associada somente pelo número, porque o SAP poderá reutilizar o número em ciclos diferentes.

## 10.4 Primeira integração

A primeira integração deverá ser de leitura por contrato:

- usuários autorizados;
- ativos;
- pátios;
- OS programadas;
- coordenações;
- especialidades.

Essa integração poderá ocorrer inicialmente por snapshot ou endpoint controlado.

## 10.5 Segunda integração

Após estabilização, o Workforce poderá devolver:

- HH real por OS;
- início e fim real;
- participantes;
- falhas relacionadas;
- distribuição do esforço;
- qualidade do apontamento.

## 10.6 Unificação posterior

A unificação deverá ocorrer primeiro na experiência do usuário e somente depois na arquitetura interna.

Possíveis caminhos:

1. Portal único com navegação entre SGO e Workforce.
2. SSO único.
3. Menu integrado.
4. Componentes e identidade visual comuns.
5. APIs compartilhadas.
6. Dashboards consolidados.
7. Eventual consolidação de serviços, se tecnicamente vantajosa.

Unificação não significará colocar todo o código em um único arquivo. O objetivo será uma experiência integrada com domínios desacoplados e contratos claros.

## Visão futura

```text
SAP e fontes corporativas
          |
          v
       SGO Core
 OS, ativos, prioridade, rota e evidência
          |
          | contratos versionados
          v
   SGO Workforce
 jornada, eventos, HH, falhas e GPS
          |
          v
 Analytics e Capacidade PCM
```

---

# 11. Ordem oficial de construção

## Incremento 1

Motor de jornada, atividade, pausa e HH com testes.

## Incremento 2

Persistência local e recuperação de estado.

## Incremento 3

Fila offline e sincronização idempotente.

## Incremento 4

Interface operacional simples para celular.

## Incremento 5

Catálogo de pausas, deslocamentos, esperas e apoios.

## Incremento 6

Atendimento de falhas e catálogo RASF.

## Incremento 7

Pulsos GPS, qualidade e sincronização em lote.

## Incremento 8

Consolidação de HH e qualidade dos dados.

## Incremento 9

Dashboards ECharts.

## Incremento 10

Mapa operacional.

## Incremento 11

Exportações CSV, XLSX e GeoJSON.

## Incremento 12

Capacidade PCM.

## Incremento 13

Integração progressiva com o SGO.

---

# 12. Micro-sessões recomendadas para o Incremento 1

## 12.1 Estrutura do domínio

Definir enums, exceções e contratos mínimos.

## 12.2 Entidade Jornada

Implementar estados, início, encerramento e validações.

## 12.3 Entidade Atividade

Implementar intervalo bruto, estados e validações.

## 12.4 Entidade Pausa

Implementar vínculo, motivo, intervalo e validações.

## 12.5 Máquina de transições

Controlar atividade principal, pausa ativa e retorno ao contexto.

## 12.6 Motor de cálculo

Calcular jornada bruta, atividade bruta, pausa, atividade líquida e tempo não classificado.

## 12.7 Testes nominais

Implementar o caso mínimo obrigatório.

## 12.8 Testes de borda

Implementar sobreposição, timestamps inválidos, duplicidade e meia-noite.

## 12.9 Revisão e documentação

Revisar regras, resultados e preparar ADR da pausa.

---

# 13. Resposta obrigatória do agente antes de codificar

Depois de ler este documento, o agente deverá confirmar:

1. Que o Workforce ficará separado do SGO no MVP.
2. Que o HH será calculado por timestamps persistidos.
3. Que o primeiro incremento será apenas o motor de domínio.
4. Que a pausa será provisoriamente um evento próprio vinculado à atividade.
5. Que offline, GPS, RASF e dashboards virão em incrementos posteriores.
6. Que regras pendentes não serão inventadas.
7. Que cada fase terá testes e critérios de aceite.
8. Que a futura integração será feita por contratos e chaves compatíveis.

Se o agente propuser começar por dashboard, mapa, GPS, banco de produção, interface completa ou integração direta no SGO, o agente deverá reler este documento antes de continuar.

---

# 14. Diretriz final

O SGO Workforce deverá ser desenvolvido com a mesma disciplina aprendida no SGO:

- compreender antes de codificar;
- validar com caso real;
- trabalhar em micro-sessões;
- fazer alterações pequenas;
- preservar rastreabilidade;
- testar em dispositivo real nas fases de interface e offline;
- documentar decisões;
- consolidar antes de expandir.

> O sucesso do SGO Workforce não será medido pela quantidade de telas, mas pela confiabilidade com que a aplicação transforma eventos reais de campo em HH, conhecimento técnico e capacidade operacional.
