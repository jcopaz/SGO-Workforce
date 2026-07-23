# ADR-0015 | Buckets reais de perda de capacidade PCM (MRS Logística)

## Contexto

Em 2026-07-23, logo após fornecer o catálogo real do Relatório de
Atividades (ADR-0014), o responsável pelo produto forneceu um print da
planilha real de cálculo de PCM da MRS Logística — a tabela "PERDAS", com
três colunas (`PARÂMETRO`, `%`, `PAUSAS MRS`) e quatro categorias de perda:

```text
HORAS AUSENTES                              18,25%
    FÉRIAS                                   8,83%
    MOTIVOS LEGAIS                           1,91%
    REFEIÇÃO 1 HORA                          7,51%

HORAS PRESENTES IMPRODUTIVAS                14,23%
    AGUARDANDO CCO                           0,17%
    AGUARDANDO SEQUÊNCIA DE SERVIÇO          0,16%
    FALTA DE FERRAMENTA OU MATERIAL          0,00%
    PREPARAÇÃO PARA JORNADA                  5,83%
    RESTRIÇÃO DE INFRAESTRUTURA              0,00%
    REUNIÃO OU ADM                           0,88%
    SERVIÇO INTERNO DA COORDENAÇÃO           7,16%
    TRABALHO NÃO DISTRIBUÍDO                 0,00%
    TREM PARADO NA FRENTE DE SERVIÇO         0,02%

HORAS PRESENTES NAO APONTADAS                0,00%
    HORAS PRESENTES NAO APONTADAS            0,00%

HORAS PRESENTES PRODUTIVAS NAO RENTAVEIS    30,12%
    CARREGAR VEÍCULO                         0,15%
    DESCARREGAR VEÍCULO                      0,08%
    DESLOCAMENTO A PÉ                        0,11%
    DESLOCAMENTO FERROVIÁRIO                 0,00%
    DESLOCAMENTO RODOVIÁRIO                 24,70%
    DESMONTAR ATIVIDADE                      0,18%
    MANUTENÇÃO EM EQUIPAMENTOS                0,00%
    MANUTENÇÃO NÃO PLANEJADA                  0,00%
    PREPARAR ATIVIDADE                       0,67%
    SMS                                      2,21%
    SUPORTE DA MANUTENÇÃO                    0,17%
    TREINAMENTO                              1,82%
    CONSULTA À DOCUMENTAÇÃO TÉCNICA          0,05%
```

Legendado pelo próprio responsável como "Exemplo de cálculo de horas pelo
PCM" — os valores percentuais são de um período específico real, não uma
meta oficial fixa, mas **a estrutura de 4 buckets e a lista de quais
motivos caem em qual bucket é exatamente o que
`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção 15.3 e
`docs/39_ADR_0012_CAPACIDADE_PCM.md` deixavam pendente** ("buckets
oficiais de perdas").

## Decisão

### 1. `BucketCapacidade` substituído pelos 4 buckets reais

Os buckets genéricos derivados de `docs/15_CAPACIDADE_PCM.md`
(`PRESENTE_PRODUTIVO_APLICAVEL`, `DESLOCAMENTO`, `ESPERA_OPERACIONAL`,
`PAUSA_LEGAL_REFEICAO`, `TREINAMENTO_DDS_REUNIAO`, `FALHA_CORRETIVA`,
`LACUNA_NAO_APONTADO`, `PRESENTE_PRODUTIVO_NAO_APLICAVEL`) foram
substituídos pelos 4 buckets reais, com os mesmos nomes da planilha:

- `HORAS_AUSENTES`
- `HORAS_PRESENTES_IMPRODUTIVAS`
- `HORAS_PRESENTES_NAO_APONTADAS`
- `HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS`

É uma mudança que quebra compatibilidade com o enum anterior — aceitável
porque não há nenhum uso em produção ainda (todo o Incremento 12 era
baseado em buckets de exemplo, nunca usados com dados reais).

### 2. `mapeamento_categoria_bucket_relatorio_1_manutencao()`

Nova função em `workforce_core/pcm.py`, mapeando cada `Categoria` do
Relatório 1 (ADR-0014) para o bucket real correspondente, código a código,
exatamente como a planilha lista:

| Bucket real | Categorias (código EE) |
|---|---|
| `HORAS_AUSENTES` | Refeição 1 hora (`EE02`) |
| `HORAS_PRESENTES_IMPRODUTIVAS` | Aguardando CCO (`EE03`), Aguardando sequência de serviço (`EE10`), Falta de ferramenta ou material (`EE04`), Preparação para jornada (`EE01`), Restrição de infraestrutura (`EE06`), Reunião ou ADM (`EE07`), Serviço interno da coordenação (`EE08`), Trabalho não distribuído (`EE09`), Trem parado na frente de serviço (`EE05`) |
| `HORAS_PRESENTES_NAO_APONTADAS` | Automático — é o `tempo_nao_classificado` já calculado (`EE24`, ver ADR-0014) |
| `HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS` | Carregar veículo (`EE19`), Descarregar veículo (`EE20`), Deslocamento a pé (`EE14`), Deslocamento ferroviário (`EE13`), Deslocamento rodoviário (`EE12`), Desmontar atividade (`EE16`), Preparar atividade (`EE15`), SMS (`EE21`), Suporte da manutenção (`EE18`), Treinamento (`EE23`), Consulta à documentação técnica (`EE11`) |

`FÉRIAS` e `MOTIVOS LEGAIS` (dentro de `HORAS_AUSENTES` na planilha real)
**não têm código no Relatório 1** — vêm de uma fonte de RH/escala externa
que o sistema não tem (mesma pendência de sempre). Por isso continuam
como entrada manual (`ausencias_externas`) na função de simulação, nunca
derivadas do apontamento.

### 3. `MANUTENÇÃO EM EQUIPAMENTOS` (`EE17`) e `MANUTENÇÃO NÃO PLANEJADA`
   (`EE22`) deliberadamente fora do mapeamento

Na planilha real, essas duas linhas aparecem dentro de
"produtivas não rentáveis" com **0,00%** no exemplo fornecido. A leitura
mais provável: elas só contam como perda ("não rentável") quando **não**
estão vinculadas a uma OS planejada válida — quando vinculadas
corretamente, contam como capacidade efetiva/rentável (não uma perda).

O sistema hoje **não verifica isso automaticamente** — não há checagem de
"a OS vinculada é válida/planejada" (só existe o campo opcional
`DadosFalha.os_referencia`, Incremento 13, sem validação de "plano").
Até essa checagem existir, `EE17`/`EE22` ficam **fora de qualquer bucket
de perda por padrão** — o mesmo valor (0,00% de perda) que a planilha
real mostrava no exemplo. Isso é uma simplificação deliberada, não uma
tentativa de resolver a distinção rentável/não-rentável sem dado
suficiente para isso.

### 4. `simular_cenario_relatorio_1_manutencao()`

Nova função de conveniência que:
- usa `mapeamento_categoria_bucket_relatorio_1_manutencao()` automaticamente;
- deriva `pausas_nao_computaveis`, `improdutividade` e
  `atividades_nao_aplicaveis` **diretamente do apontamento real**, via os
  3 buckets calculáveis (`HORAS_PRESENTES_NAO_APONTADAS`,
  `HORAS_PRESENTES_IMPRODUTIVAS`, `HORAS_PRESENTES_PRODUTIVAS_NAO_RENTAVEIS`);
- soma o tempo de refeição já apontado (`HORAS_AUSENTES` do apontamento)
  ao único termo que continua manual: `ausencias_externas` (férias +
  motivos legais).

Isso substitui a versão anterior do simulador na página do painel, que
exigia estimar manualmente os 3 termos — agora só "pessoas previstas",
"horas de escala" e "ausências externas" continuam sendo entrada humana.
`simular_cenario()` (genérico, com mapeamento arbitrário) continua
disponível para quem quiser usar outro catálogo/mapeamento.

### 5. `painel/pages/3_Capacidade_PCM.py` atualizada

Usa `catalogo_relatorio_1_manutencao()` (em vez do catálogo de exemplo) e
`simular_cenario_relatorio_1_manutencao()`. A tabela de mapeamento exibida
na tela deixou de ser rotulada "EXEMPLO, não oficial" — agora é a
planilha real, com a ressalva explícita sobre `EE17`/`EE22` (item 3
acima) e sobre a fonte de escala/ausências externas continuar pendente.

## Deliberadamente fora deste ADR

- **Distinção "OS planejada válida" vs não**: não implementada — é a
  peça que faltaria para classificar `EE17`/`EE22` corretamente entre
  rentável e não rentável.
- **Percentuais-alvo (parâmetro) da planilha** (18,25%, 14,23%, etc.):
  não incorporados como metas no sistema — são dados de um período
  específico, não uma meta validada para o produto usar como referência
  fixa.
- **`FÉRIAS`/`MOTIVOS LEGAIS` automatizados**: continuam manuais — sem
  fonte de RH/escala conectada.
- **Coordenação/distrito/equipe como filtro do cálculo de PCM**: não
  implementado (mesma lacuna já registrada nos ADRs de mapa/painel).

## Alternativas consideradas

- **Manter os buckets genéricos antigos e só adicionar o mapeamento real
  por cima**: rejeitado — os nomes antigos (`PRESENTE_PRODUTIVO_APLICAVEL`,
  `ESPERA_OPERACIONAL` etc.) não correspondem à terminologia real que a
  MRS usa, e mantê-los criaria dois vocabulários paralelos para a mesma
  ideia. Substituir foi mais simples e mais fiel à fonte real.
- **Tentar adivinhar uma regra para separar `EE17`/`EE22` rentável de não
  rentável a partir dos dados já existentes**: rejeitado — não há dado
  suficiente (validade da OS) para fazer essa distinção com confiança;
  melhor deixar de fora do bucket de perda do que inventar um critério.

## Validação operacional

Ainda não realizada. Os percentuais mostrados na planilha fornecida são
de um período real específico, não uma meta ou classificação validada
para uso contínuo — o mapeamento estrutural (qual categoria cai em qual
bucket) é a parte reaproveitada aqui, não os números do exemplo.

## Data e responsáveis

- Data de registro: 2026-07-23.
- Registrado por: Claude Code, a partir da planilha fornecida pelo
  responsável pelo produto (j.copaz@hotmail.com).
- Revisão pendente: responsável pelo produto (confirmar o mapeamento,
  especialmente a decisão de deixar `EE17`/`EE22` fora de qualquer bucket
  de perda por padrão).
