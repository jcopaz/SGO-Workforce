# 27 | Alinhamento Oficial do Produto e Diretriz de Implementação

## SGO Workforce

**Versão:** 1.0  
**Finalidade:** consolidar o entendimento correto do produto antes do início da codificação.  
**Uso:** leitura obrigatória pelo Claude Code, GitHub Copilot, Copilot Studio e qualquer pessoa que participe do projeto.

---

# 1. O que é o SGO Workforce

O **SGO Workforce** é uma plataforma de gestão de jornada, esforço operacional, telemetria de campo, atendimento de falhas e capacidade da manutenção eletroeletrônica.

O produto transforma eventos reais da operação em:

- HH calculado e auditável;
- distribuição do tempo por categoria;
- tempo líquido de execução de atividades e OS;
- histórico estruturado de falhas;
- informação geográfica da atuação em campo;
- indicadores para coordenação, engenharia, PCM e gerência;
- dados ordenados para exportação CSV, XLSX e, futuramente, GeoJSON;
- capacidade operacional observada para apoiar o Plano de Manutenção.

O colaborador não informa manualmente quantas horas trabalhou. O colaborador registra acontecimentos operacionais, como início de jornada, atividade, pausa, deslocamento, atendimento de falha e encerramento. O sistema calcula o HH com base nos timestamps persistidos desses eventos.

## Princípio central

> O colaborador aponta eventos. O sistema calcula o HH.

O SGO Workforce não é um relógio de ponto, uma ferramenta de vigilância individual, um formulário manual de horas ou uma cópia literal do antigo OptJob. O antigo OptJob serve como referência conceitual para o apontamento por eventos, mas o novo produto amplia o conceito com operação offline, pulsos GPS, falhas estruturadas, mapas, dashboards e capacidade operacional.

---

# 2. O que diferencia o SGO Workforce do SGO atual

## SGO atual

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

## SGO Workforce

O SGO Workforce complementa o ecossistema com:

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
- dashboards nativos em ECharts;
- exportações estruturadas;
- capacidade efetiva para o PCM.

O Workforce responde principalmente:

- Quanto esforço foi consumido?
- Como o tempo da jornada foi distribuído?
- Quanto tempo líquido foi aplicado em cada OS?
- Quanto tempo foi consumido em deslocamento, espera, apoio e pausa?
- Quais falhas, ativos e regiões consomem mais capacidade?
- Qual HH efetivo está disponível para o plano?

## Relação entre os produtos

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
- O Workforce deve possuir repositório, aplicação, API, ambiente e domínio próprios.
- A integração futura deve ocorrer por contratos definidos e versionados.

## 3.2 HH e tempo

- HH não pode ser digitado manualmente como fonte oficial.
- O relógio visual da tela não é a fonte do tempo.
- O tempo oficial deve vir de timestamps persistidos.
- Datas operacionais devem usar timestamps com timezone, preferencialmente armazenados em UTC e exibidos em `America/Sao_Paulo`.
- Toda correção posterior precisa manter o valor anterior, o novo valor, o responsável e a justificativa.

## 3.3 Jornada e eventos

- Um colaborador pode ter apenas uma jornada aberta por vez.
- Um colaborador pode ter apenas um evento principal ativo por vez.
- Sobreposições incompatíveis devem ser bloqueadas ou encaminhadas para auditoria.
- Iniciar uma pausa deve suspender o cômputo da atividade conforme a regra definida.
- Finalizar uma pausa deve permitir o retorno ao contexto anterior válido.
- Encerrar uma jornada com evento aberto exige tratamento explícito, nunca encerramento silencioso.
- O sistema deve identificar tempo não classificado dentro da jornada.

## 3.4 Offline first

- Jornada, atividade, pausa, deslocamento e falha devem funcionar sem internet.
- Registros locais não podem ser perdidos ao fechar ou reiniciar a aplicação.
- Cada registro deve possuir identificador UUID criado no cliente.
- A sincronização deve ser idempotente.
- Reenvio do mesmo registro não pode gerar duplicidade.
- A fila deve mostrar registros pendentes, sincronizados, com erro e em conflito.
- Conflitos não podem ser resolvidos silenciosamente.

## 3.5 Atendimento de falha

Um atendimento de falha não pode ser encerrado sem os campos obrigatórios definidos para o MVP:

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

- A captura de pulsos deve ocorrer somente dentro da jornada ativa e conforme política corporativa aprovada.
- Todo pulso deve registrar timestamp, latitude, longitude e precisão.
- A precisão original não deve ser descartada.
- Falha de GPS não deve apagar eventos operacionais já registrados.
- GPS inválido deve gerar informação de qualidade, contingência ou bloqueio conforme decisão de negócio.
- Permanência e deslocamento inferidos por GPS devem ser identificados como inferências, não como prova absoluta.
- O uso em produção depende de validação de LGPD, segurança da informação, política corporativa e relações trabalhistas.

## 3.7 Dashboards e exportações

- Os dashboards serão construídos no próprio Python/Streamlit com Apache ECharts.
- O Power BI não é dependência do MVP.
- Mapas utilizarão inicialmente Folium/Leaflet, salvo decisão arquitetural documentada.
- Totais dos dashboards devem reconciliar com as exportações.
- CSV e XLSX devem respeitar os filtros aplicados.
- Toda exportação deve possuir data de geração, período, filtros e usuário responsável.

## 3.8 Segurança e qualidade

- Ações críticas devem seguir o princípio fail closed.
- SQL deve ser parametrizado.
- Segredos não podem ser versionados.
- Dependências devem ter faixas ou versões validadas.
- Mudanças relevantes devem passar por ambiente de desenvolvimento e homologação.
- Teste unitário não substitui teste em celular real.
- Widgets stateful do Streamlit não devem desaparecer entre reruns sem validação específica.

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

# 5. Decisões de negócio ainda pendentes

O agente não deve inventar respostas para os itens abaixo. Cada decisão deve ser validada operacionalmente e registrada em ADR.

1. Intervalo padrão dos pulsos GPS.
2. Estratégia de adaptação do pulso por movimento ou bateria.
3. Política de retenção e acesso aos dados de localização.
4. Obrigatoriedade de GPS para iniciar e encerrar eventos.
5. Regra de contingência quando o GPS estiver indisponível.
6. Catálogo oficial de pausas.
7. Regra de cômputo de cada pausa.
8. Se a pausa será evento filho, suspensão ou encerramento e retomada.
9. Fonte oficial de escala e capacidade bruta.
10. Regra para múltiplas OS no mesmo evento.
11. Regra de rateio entre várias OS.
12. Obrigatoriedade de evidência fotográfica no atendimento de falha.
13. Grau de detalhe do mapa por perfil.
14. Hospedagem e autenticação do piloto.
15. Processo de aprovação de novos sintomas, causas e ações.
16. Periodicidade e método de atualização do RASF.
17. Critérios para classificar tempo não apontado.
18. Política para edição posterior de eventos.
19. Perfis que poderão visualizar trajetórias individuais.
20. Retenção local dos registros após sincronização.

---

# 6. Primeiro incremento técnico validável

## Diretriz oficial

O primeiro incremento não deve incluir login, Streamlit, PWA, IndexedDB, FastAPI, PostgreSQL, GPS, RASF, dashboards, mapa, exportações ou integração com o SGO.

O primeiro incremento deve validar somente o coração do produto:

```text
Motor de Jornada + Eventos + Pausas + HH
```

## Escopo

- entidade Jornada;
- entidade Evento;
- evento de atividade;
- pausa;
- finalização da pausa;
- retorno à atividade;
- encerramento da atividade;
- encerramento da jornada;
- máquina de estados;
- bloqueio de sobreposição;
- cálculo de duração bruta;
- cálculo de pausa;
- cálculo de duração líquida;
- cálculo de tempo não classificado;
- testes unitários.

## Caso mínimo obrigatório

```text
08:00  início da jornada
08:10  início da atividade
10:00  início da pausa
10:20  final da pausa
12:00  final da atividade
12:10  final da jornada
```

## Resultado esperado

```text
Jornada bruta:          4h10
Atividade bruta:        3h50
Pausa:                  0h20
Atividade líquida:      3h30
Tempo não classificado: 0h20
```

## Fora do primeiro incremento

- banco de produção;
- interface gráfica;
- autenticação;
- offline;
- API;
- sincronização;
- deslocamento;
- falhas;
- GPS;
- mapas;
- ECharts;
- exportações;
- PCM;
- integração com SGO.

## Justificativa

O domínio deve ser validado isoladamente antes de misturar interface, persistência, offline e backend. Isso facilita identificar erros na regra de cálculo e evita construir uma aplicação complexa sobre um motor de HH incorreto.

---

# 7. Como a aplicação será construída separada do SGO e unificada posteriormente

## 7.1 Separação inicial

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

## 7.2 Razões para a separação

- O SGO está em processo de estabilização e deploy.
- O Workforce introduz novos riscos: jornada contínua, offline, localização periódica e sincronização em lote.
- Um erro no Workforce não pode interromper a conclusão de OS no SGO.
- A separação permite testar com grupo piloto e evoluir rapidamente.
- O domínio do Workforce precisa amadurecer antes da fusão visual.

## 7.3 Preparação para integração desde o início

Mesmo separado, o Workforce deve preservar chaves compatíveis:

- matrícula do usuário;
- código da coordenação;
- número da OS;
- referência do ciclo/plano da OS;
- identificador do ativo;
- código do pátio;
- taxonomias técnicas;
- timestamps padronizados.

A OS não pode ser associada somente pelo número, porque o SAP pode reutilizar o número em ciclos diferentes.

## 7.4 Primeira integração

A primeira integração deve ser de leitura por contrato:

- usuários autorizados;
- ativos;
- pátios;
- OS programadas;
- coordenações;
- especialidades.

Essa integração pode ocorrer inicialmente por snapshot ou endpoint controlado.

## 7.5 Segunda integração

Após estabilização, o Workforce poderá devolver:

- HH real por OS;
- início e fim real;
- participantes;
- falhas relacionadas;
- distribuição do esforço;
- qualidade do apontamento.

## 7.6 Unificação posterior

A unificação deve ocorrer primeiro na experiência do usuário e somente depois na arquitetura interna.

Possíveis caminhos:

1. Portal único com navegação entre SGO e Workforce.
2. SSO único.
3. Menu integrado.
4. Componentes e identidade visual comuns.
5. APIs compartilhadas.
6. Dashboards consolidados.
7. Eventual consolidação de serviços, caso tecnicamente vantajosa.

Unificação não significa colocar todo o código em um único arquivo. O objetivo é experiência integrada com domínios desacoplados e contratos claros.

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

# 8. Ordem oficial de construção

## Incremento 1

Motor de jornada, eventos, pausas e HH com testes.

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

# 9. Resposta obrigatória do agente antes de codificar

Depois de ler este documento, o agente deve confirmar:

1. Que o Workforce ficará separado do SGO no MVP.
2. Que o HH será calculado por timestamps persistidos.
3. Que o primeiro incremento será apenas o motor de domínio.
4. Que offline, GPS, RASF e dashboards virão em incrementos posteriores.
5. Que regras pendentes não serão inventadas.
6. Que cada fase terá testes e critérios de aceite.
7. Que a futura integração será feita por contratos e chaves compatíveis.

Se o agente propuser começar por dashboard, mapa, GPS, banco de produção ou integração direta no SGO, o agente deve reler este documento antes de continuar.

---

# 10. Diretriz final

O SGO Workforce deve ser desenvolvido com a mesma disciplina aprendida no SGO:

- compreender antes de codificar;
- validar com caso real;
- trabalhar em micro-sessões;
- fazer patches pequenos;
- preservar rastreabilidade;
- testar em dispositivo real;
- documentar decisões;
- consolidar antes de expandir.

> O sucesso do SGO Workforce não será medido pela quantidade de telas, mas pela confiabilidade com que a aplicação transforma eventos reais de campo em HH, conhecimento técnico e capacidade operacional.
