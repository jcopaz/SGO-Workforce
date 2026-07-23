# ADR-0008 | Consolidação de HH e qualidade dos dados (Incremento 8)

## Contexto

O Incremento 8 do roadmap não tem seção própria de regras fechadas ou
pendências no alinhamento oficial v1.2 (que para no Incremento 7). A fonte
mais concreta para escopo é `docs/20_TESTES_E_QUALIDADE.md`, seções
"Reconciliação" (soma por jornada, soma por categoria, soma por OS,
dashboard x exportação, eventos x HH de equipe, pulsos enviados x
recebidos) e "Observabilidade" (métricas de sync, jornadas abertas
anormais, taxa de GPS válido) — documento já existente, não escrito nesta
sessão.

Vários itens dessa lista dependem de conceitos que ainda não existem no
sistema: OS (fora de escopo até o Incremento 13), "equipe" (nunca
modelada), dashboard e exportação (Incrementos 9 e 11, ainda não
construídos). Este incremento entrega apenas o que já é possível com o
que existe: `workforce_core` (Jornada/Atividade/Pausa/EventoSecundario/
DadosFalha/PulsoGps) e o catálogo do Incremento 5.

## Decisão

1. **`resumo_por_categoria(jornada, catalogo)`**
   (`workforce_core/consolidacao.py`): agrega a duração classificada de
   uma jornada por `Categoria`. Atividades são classificadas como
   `ATENDIMENTO_FALHA` (se tiverem `dados_falha`) ou `ATIVIDADE_PLANEJADA`
   (caso contrário) — as duas categorias de `docs/07_MOTOR_EVENTOS_E_HH.md`
   que já correspondem ao conceito de atividade, não categorias novas.
   Pausas e eventos secundários são classificados pela `categoria` do seu
   `motivo` no catálogo informado; motivo sem categoria (como
   `PAUSA_TESTE`, que tem `categoria=None` desde o ADR-0005) ou fora do
   catálogo cai no bucket `None` ("sem categoria conhecida") — nunca é
   descartado nem forçado numa categoria arbitrária.
2. **`resumo_consolidado(jornadas, catalogo)`**: primeira função do
   projeto capaz de agregar HH de **várias jornadas** (ex.: uma equipe, um
   período) — tudo que existia até aqui operava sobre uma jornada por vez.
   Soma jornada bruta, tempo classificado, tempo não classificado e o
   `resumo_por_categoria` de cada jornada **encerrada** (jornadas ainda
   abertas são ignoradas aqui, por não terem duração bruta válida — ver
   item 3 para como tratá-las).
3. **`jornadas_abertas_ha_muito_tempo(jornadas, *, agora, limite)`**:
   implementa "jornadas abertas anormais" de `docs/20`. `limite` é
   **sempre parâmetro explícito** — não há um valor "razoável" embutido,
   porque não existe hoje uma definição validada do que conta como jornada
   aberta por tempo demais.
4. **`taxa_qualidade_pulsos(pulsos)`**: proporção de pulsos `OK` entre os
   pulsos já avaliados (`NAO_AVALIADO` fica fora do denominador). Implementa
   "taxa de GPS válido" de `docs/20`. Retorna `None` quando não há nenhum
   pulso avaliado, para não ser confundido com "0% de qualidade".
5. **`pulsos_pendentes_de_sincronizacao(total_local, total_sincronizado)`**:
   implementa "pulsos enviados x recebidos" de `docs/20` de forma trivial
   — a diferença entre o que está gravado localmente
   (`RepositorioPulsosGpsArquivo.contar_pulsos`) e o que o cursor de
   sincronização já confirmou (`CursorSincronizacaoPulsos.total_sincronizado`,
   Incremento 7). Nunca retorna negativo.

## Por que não há uma função de "verificar reconciliação de jornada"

A conferência de soma "jornada = eventos computáveis + lacunas
classificadas" (exigida como validação mínima pelo `CLAUDE.md`) já é
garantida **por construção** desde o Incremento 1:
`calculo.tempo_nao_classificado` é definido como
`jornada_bruta - tempo_classificado`, então a igualdade é sempre
verdadeira por definição, não por uma checagem independente que possa
divergir. Escrever uma função que "verifica" isso seria uma checagem falsa
— não há dois caminhos de cálculo independentes para comparar ainda. Essa
reconciliação só se torna um teste de verdade quando existir um segundo
caminho de cálculo independente (uma exportação ou um dashboard,
Incrementos 9 e 11) para comparar contra o total do domínio — os testes
`tests/test_consolidacao.py` já verificam a igualdade como parte dos
asserts, mas isso confirma a implementação, não substitui a reconciliação
futura entre camadas independentes.

## Deliberadamente fora deste incremento

- **Soma por OS**: não há conceito de OS no sistema ainda (Incremento 13).
- **Eventos x HH de equipe**: não há conceito de "equipe" ou de múltiplos
  colaboradores por evento (item explicitamente pendente, seção 6 do
  alinhamento — "regra para múltiplas OS no mesmo evento" e rateio).
- **Dashboard x exportação**: nenhum dos dois existe ainda; a reconciliação
  real entre eles é tarefa dos Incrementos 9 e 11.
- **Métricas de sync, erros por endpoint, latência**: dependem de uma API
  real, que não existe (mesma lacuna registrada nos ADRs 3 e 7).

## Alternativas consideradas

- **Adicionar um campo `categoria` direto em `Atividade`**: rejeitado por
  ora — a inferência a partir de `dados_falha` já cobre as duas categorias
  de atividade existentes sem exigir mudança de schema; se o catálogo de
  atividades crescer (outras categorias de doc07 como "atividade
  administrativa"), essa decisão deve ser revisitada.
- **Definir um limite padrão para "jornada aberta há muito tempo" (ex.: 12h)**:
  rejeitado por ser uma decisão de negócio não validada — mantido como
  parâmetro obrigatório.

## Validação operacional

Ainda não realizada — depende de dados reais de campo para calibrar
limites (jornada aberta há muito tempo) e para validar se a classificação
por categoria produz agrupamentos úteis para a operação.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto, quando dashboards (9) e
  exportações (11) existirem para fechar o ciclo de reconciliação.
