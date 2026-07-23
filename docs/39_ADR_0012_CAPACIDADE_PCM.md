# ADR-0012 | Capacidade PCM (Incremento 12)

## Contexto

`docs/15_CAPACIDADE_PCM.md` já definia, antes desta sessão, a fórmula
conceitual e os buckets:

```text
Capacidade bruta = pessoas previstas x horas de escala.
Capacidade efetiva = capacidade bruta - ausencias - pausas nao
computaveis - improdutividade - atividades produtivas nao aplicaveis
ao plano.
```

Buckets: ausente, presente produtivo aplicável ao plano, presente
produtivo não aplicável, deslocamento, espera operacional, pausa
legal/refeição, treinamento/DDS/reunião, falha corretiva,
lacuna/não apontado.

`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção 15.3 ("Antes do
Incremento 12") deixa pendente: fonte oficial de escala, fonte de
ausências e férias, buckets oficiais de perdas (isto é, qual motivo/
categoria real cai em qual bucket, e quais buckets contam como
"improdutividade" para a fórmula), horizonte de projeção, tratamento de
sazonalidade e regras do simulador/premissas editáveis.

Este é o incremento com a maior proporção de decisões pendentes até
agora — a fórmula existe, mas quase todas as fontes de dados que a
alimentam não.

## Decisão

1. **`workforce_core/pcm.py`**: `capacidade_bruta` e `capacidade_efetiva`
   implementam a fórmula de `docs/15` exatamente, com **todos os termos
   como parâmetros obrigatórios** (`pessoas_previstas`, `horas_escala`,
   `ausencias`, `pausas_nao_computaveis`, `improdutividade`,
   `atividades_nao_aplicaveis`) — nenhuma fonte real (escala, RH, férias)
   é assumida ou tem valor padrão. `capacidade_efetiva` nunca fica
   negativa (piso zero — um valor negativo não tem significado
   operacional).
2. **`BucketCapacidade`**: enum citado literalmente dos "Buckets" de
   `docs/15`.
3. **`agrupar_por_bucket(resumo, mapeamento_categoria_bucket)`**: o
   mapeamento `Categoria -> BucketCapacidade` é **sempre parâmetro
   explícito** — não há "buckets oficiais" embutidos no motor. A única
   correspondência automática é `tempo_nao_classificado_total ->
   LACUNA_NAO_APONTADO`, que não é um mapeamento inventado: é a própria
   definição de "lacuna/não apontado" já usada desde o Incremento 1
   (tempo sem nenhum evento registrado).
4. **`PremissasCenario`/`ResultadoCenario`/`simular_cenario`**: implementa
   literalmente "sempre mostrar premissas" (`docs/15`, seção
   "Simulação") — `ResultadoCenario.premissas` sempre carrega as mesmas
   premissas usadas no cálculo, nunca esconde a entrada atrás da saída.
5. **`painel/pages/3_Capacidade_PCM.py`**: página do simulador. Pessoas
   previstas, horas de escala e ausências são entradas manuais (não há
   fonte de escala/RH conectada). O mapeamento categoria→bucket exibido
   na tela é rotulado explicitamente como **"EXEMPLO, não oficial"** — a
   página não afirma que aquela classificação foi validada.
6. **Escopo deliberadamente reduzido do cálculo automático**: a página
   só desconta `ausências` da capacidade bruta automaticamente. Pausas
   não computáveis, improdutividade e atividades não aplicáveis
   **não são descontadas automaticamente**, porque decidir quais buckets
   observados contam como cada um desses três termos depende
   diretamente da classificação produtiva/improdutiva/não computável do
   catálogo — que continua `NAO_DEFINIDO` desde o ADR-0005 e é
   explicitamente uma decisão pendente. A página mostra os buckets
   observados e deixa a decisão de quais contam como perda para quem
   está lendo, em vez de decidir sozinha.

## Deliberadamente fora deste incremento

- **Fonte oficial de escala e de ausências/férias**: nenhuma integração
  com sistema de RH ou tabela de escala — `pessoas_previstas`,
  `horas_escala` e `ausencias` são sempre digitados manualmente no
  simulador.
- **Buckets oficiais de perdas**: o mapeamento categoria→bucket exibido é
  um exemplo ilustrativo, não uma classificação aprovada pela operação.
- **Horizonte de projeção e sazonalidade**: o simulador calcula um único
  cenário estático a partir de premissas informadas; não há projeção de
  série temporal nem ajuste sazonal.
- **Uso de histórico para recomendação**: `docs/15`, seção "Evolução",
  já diz "No MVP, medir. Depois, consolidar séries. Somente então usar
  histórico para projeção e recomendação" — este incremento fica na fase
  "medir" (buckets observados a partir de jornadas reais), sem projeção
  nem recomendação automática.
- **Filtro por coordenação/especialidade** (citados em `docs/15`, seção
  "Simulação"): não implementado — esses conceitos não são modelados no
  sistema (mesma lacuna já registrada no ADR-0010 para o mapa).

## Validação realizada

- `tests/test_pcm.py` (7 testes): fórmula de capacidade bruta/efetiva
  (incluindo piso zero e rejeição de `pessoas_previstas` negativo),
  agrupamento por bucket com mapeamento explícito e lacuna automática,
  ausência de chave de lacuna quando não há tempo não classificado,
  `simular_cenario` sempre devolvendo as premissas usadas.
- **Smoke test real do servidor**: `streamlit run painel/app.py
  --server.headless true`, com dados de exemplo, HTTP 200 confirmado nas
  quatro páginas do painel (Painel, Mapa Operacional, Exportações,
  Capacidade PCM), sem traceback no log.

## Validação NÃO realizada

Mesma limitação já registrada nos ADRs 4, 9, 10 e 11: não foi possível
abrir a página do simulador em um navegador real para interagir com os
campos numéricos e conferir visualmente o resultado.

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (fonte de escala/ausências,
  buckets oficiais, classificação produtiva/improdutiva do catálogo) antes
  de qualquer uso do simulador para decisão real de capacidade.
