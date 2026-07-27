# ADR-0023 | Reclassificação produtiva/improdutiva e renumeração do catálogo Relatório 1

## Contexto

Desde o ADR-0014 (2026-07-23), os 23 códigos reais do "Relatório de
Atividades Diárias de Manutenção" (EE01-EE23) existem no catálogo, mas
`classificacao_hh` permanecia `NAO_DEFINIDO` em todos — decisão de negócio
explicitamente pendente (`docs/23_DECISOES_PENDENTES.md`, item 3), que
bloqueava os cards de HH produtivo/improdutivo do dashboard oficial
(`docs/12_DASHBOARDS_ECHARTS.md`).

Ao ser perguntado "o que falta antes da integração com o SGO", o
responsável pelo produto pediu que eu trouxesse uma tabela com os 23
códigos para ele devolver a classificação — e, durante essa revisão,
identificou três problemas adicionais no catálogo existente:

1. Faltava um código para "manutenção programada (EE17) não concluída no
   turno" — nenhum dos 23 códigos existentes representava esse resultado.
2. EE18 ("Suporte da manutenção") e EE22 ("Manutenção não planejada") eram,
   na prática operacional, a mesma coisa que EE22 já representava melhor
   como "Atendimento de Falha" — duplicidade a resolver excluindo um deles.
3. Três descrições estavam desatualizadas frente ao formulário real
   atual: EE17 "Manutenção em equipamentos" → "Manutenção Programada",
   EE21 "SMS" → "DDS / APR", EE22 "Manutenção não planejada" →
   "Atendimento de Falha".

## Decisão

### 1. Classificação produtiva/improdutiva/não computável — validada código a código

Todos os 23 códigos passam a ter `classificacao_hh` definida (antes,
100% `NAO_DEFINIDO`). Regra geral aplicada pelo responsável pelo produto:
tempo de ausência real (refeição) é `NAO_COMPUTAVEL`; esperas/paradas por
causas externas e trabalho administrativo são `IMPRODUTIVA`; execução,
deslocamento, preparação/desmontagem de posto e apoio à operação são
`PRODUTIVA` — **com uma exceção deliberada**: "produtiva não rentável" no
bucket de PCM (ADR-0015) não significa improdutiva para fins de HH (a
pessoa está trabalhando de verdade, só não fatura direto) — por isso
esses códigos entram como `PRODUTIVA`, não `IMPRODUTIVA`. A única
divergência da minha sugestão inicial foi EE16 (Desmontar atividade),
que o responsável classificou como `IMPRODUTIVA`.

Tabela final (código → classificação):

| Categoria | Códigos |
|---|---|
| `IMPRODUTIVA` | EE01, EE03, EE04, EE05, EE06, EE07, EE08, EE09, EE10, EE16 |
| `NAO_COMPUTAVEL` | EE02 |
| `PRODUTIVA` | EE11, EE12, EE13, EE14, EE15, EE17, EE18, EE19, EE20, EE21, EE22, EE23 |

### 2. EE18 (Suporte da manutenção) excluído — duplicava Atendimento de Falha

O responsável pelo produto confirmou que EE18 e o que já era EE22 (agora
EE21, "Atendimento de Falha") representam a mesma coisa operacionalmente.
Mantido o código que já sustenta toda a funcionalidade construída nos
ADR-0006/0021/0022 (nota, ativo, sintoma, objeto, observação, GPS, foto,
transferência) — **excluído o antigo EE18**, não o antigo EE22, para não
precisar refazer essa funcionalidade sob outro código.

### 3. Renumeração — códigos EE19 a EE24 deslizam uma posição

Com a exclusão de EE18, os códigos seguintes deslizam uma posição para
preencher o buraco (mesmo padrão de uma planilha real quando se remove
uma linha):

| Código antigo | Código novo | Descrição |
|---|---|---|
| EE18 (Suporte da manutenção) | *(excluído)* | — |
| EE19 | EE18 | Carregar veículo |
| EE20 | EE19 | Descarregar veículo |
| EE21 | EE20 | DDS / APR (renomeado de "SMS") |
| EE22 | EE21 | Atendimento de Falha (renomeado de "Manutenção não planejada") |
| EE23 | EE22 | Treinamento |
| — | EE23 | **Manutenção Programada Não Concluída** (novo, ver item 4) |

Códigos EE01-EE17 não mudam de número (EE17 só teve a descrição
renomeada para "Manutenção Programada").

### 4. Novo código EE23 — "Manutenção Programada Não Concluída"

Contraparte de EE17 quando o colaborador não conclui a manutenção
programada no próprio turno. Antes desta decisão, "EE24" era um número
**reservado e nunca uma entrada de catálogo** — representava "Horas não
apontadas", o próprio conceito de tempo não classificado que
`workforce_core.calculo` já deriva automaticamente das lacunas entre
eventos (ver ADR-0014). Com a renumeração do item 3, esse número ficou
livre e a "Manutenção Programada Não Concluída" ocupa o novo EE23 (não
EE24) — **"Horas não apontadas" continua existindo exatamente como
antes** (cálculo automático de gap, nunca uma entrada de catálogo), só
não tem mais nenhum número reservado associado a ela.

`Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA` (novo valor do enum),
`tipo_registro="atividade"` (mesmo padrão de EE17/EE21),
`classificacao_hh=PRODUTIVA` (o trabalho foi feito de verdade, mesmo sem
concluir a OS). Fica fora do mapeamento de buckets de PCM
(`mapeamento_categoria_bucket_relatorio_1_manutencao()`), mesmo
tratamento de EE17/EE21 — ver ADR-0015.

**Este ADR só cataloga o código.** A mecânica de uso (associação de uma
ou mais OS em texto livre a uma atividade EE17, exclusão parcial de OS
não concluídas, os dois botões "Concluir atividade"/"Atividade não
concluída" que produzem EE17 ou EE23 conforme o caso) é um incremento de
produto **separado, ainda não implementado** — decisões já tomadas com o
responsável pelo produto (texto livre para OS, dois botões, sem
transferência entre colaboradores por enquanto), mas pendente de desenho
e construção.

## Arquivos afetados

- `src/workforce_core/catalogo.py`: novo `Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA`;
  `_RELATORIO_1_ENTRADAS` reescrita (tuplas de 5 elementos, incluindo
  `classificacao_hh`); `catalogo_relatorio_1_manutencao()` e
  `codigos_relatorio_1_por_tipo_registro()` atualizadas para o novo
  formato de tupla.
- `src/workforce_core/pcm.py`: docstring de
  `mapeamento_categoria_bucket_relatorio_1_manutencao()` atualizada
  (EE22→EE21, EE23 novo também fora de bucket).
- `painel/dados.py`, `painel/telas/capacidade_pcm.py`: comentários/legendas
  com os códigos antigos atualizados.
- `interface_campo/js/catalogoMotivos.js`: fallback mínimo offline
  (`CATALOGO_MINIMO_OFFLINE`) atualizado com os novos códigos/descrições.
- `tests/test_catalogo_relatorio_1.py`: reescrito para a nova numeração e
  com um teste novo cobrindo a classificação completa validada.
- `docs/23_DECISOES_PENDENTES.md`: item 3 marcado resolvido.

## Consequências

- Os cards de HH produtivo/improdutivo do dashboard oficial
  (`docs/12_DASHBOARDS_ECHARTS.md`) deixam de estar bloqueados por falta
  de classificação — nenhuma tela nova foi construída ainda, mas a
  informação já existe em `EntradaCatalogo.classificacao_hh`.
- **Catálogo dinâmico em produção (Postgres/Render, ADR-0019) pode estar
  desatualizado**: `RepositorioCatalogoPostgres._semear_se_vazio()` só
  popula a tabela `motivos_catalogo` na primeira vez que ela está vazia -
  se o backend já rodou com a numeração antiga antes deste ADR, a tabela
  em produção não vai se atualizar sozinha com o próximo deploy. Precisa
  de ação manual (limpar a tabela para reseed automático, ou reaplicar
  pela tela de administração) - ver seção "Validação NÃO realizada".
- Qualquer exportação (CSV/XLSX) ou jornada já sincronizada com os
  códigos antigos (EE18 antigo, EE19-EE24 antigos) fica com os códigos
  desatualizados nos dados já gravados - não há migração retroativa de
  dados históricos (mesmo princípio de "correção nunca apaga o evento
  original", mas aqui não há histórico real de produção para migrar,
  só dados de teste/piloto).

## Fora de escopo (próximo incremento)

Associação de uma ou mais OS (texto livre) a atividades EE17, conclusão
parcial de OS (excluir da lista as não concluídas), os dois botões de
encerramento ("Concluir atividade" grava EE17, "Atividade não concluída"
grava EE23) - decisões já tomadas com o responsável pelo produto, ainda
não desenhadas nem construídas.

## Validação de qualidade realizada

- `tests/test_catalogo_relatorio_1.py`: reescrito, cobre os 23 códigos,
  a classificação completa, categorias estruturais (EE17/EE21/EE23) e
  contagem por tipo de registro.
- `pytest` completo: 226/226 (nenhuma regressão nos consumidores do
  catálogo — `painel/dados.py`, `pcm.py`, exportações, atendimento de
  falha).
- `node --test tests/js`: 72/72 (fallback de `catalogoMotivos.js`
  testado indiretamente pelos testes existentes, que não fixam os
  códigos específicos do fallback).
- `python -m py_compile` em `catalogo.py`/`pcm.py`: OK.

## Validação NÃO realizada

- **Reseed do catálogo dinâmico em produção**: não verificado se a
  tabela `motivos_catalogo` no Postgres do Render já foi semeada com a
  numeração antiga (o backend só passou a existir de fato com o deploy
  manual desta mesma sessão, mas qualquer chamada a `GET`/`POST
  /catalogo` entre esse deploy e este ADR pode ter semeado a versão
  antiga). Ação recomendada ao responsável pelo produto: consultar `GET
  /catalogo` após o próximo deploy e, se os códigos antigos aparecerem,
  limpar a tabela manualmente para forçar o reseed.
- Teste manual em navegador/celular do seletor de motivos com os novos
  códigos - mesma limitação de sempre.

## Data e responsáveis

- Data de registro: 2026-07-27.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), que validou pessoalmente a classificação de cada
  um dos 23 códigos, a exclusão do EE18 duplicado, a renumeração
  resultante e a criação do EE23.
