# ADR-0001 | Modelagem provisória da pausa como evento vinculado à atividade

## Contexto

O Incremento 1 exige um motor de domínio capaz de calcular HH bruto, HH
líquido e tempo não classificado a partir de eventos com timestamps
persistidos (`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 7).
Para isso é necessário decidir, ainda que provisoriamente, como a pausa se
relaciona com a atividade principal.

O catálogo oficial de pausas, a classificação em produtiva/improdutiva/não
computável e as regras trabalhistas associadas **não estão definidos** e
pertencem ao Incremento 5. Sem uma decisão mínima de modelagem, porém, não é
possível implementar nem testar o motor de cálculo do Incremento 1.

## Decisão

A pausa é modelada como um **evento próprio, vinculado à atividade
principal em andamento**, e não como uma subdivisão implícita do intervalo
da atividade.

```text
JORNADA
|
+-- ATIVIDADE (intervalo bruto: início -> fim)
|
+-- PAUSA (intervalo próprio: início -> fim)
    +-- referencia a ATIVIDADE
```

Regras adotadas (implementadas em `src/workforce_core/engine.py` e
`src/workforce_core/calculo.py`):

1. A atividade preserva o intervalo bruto entre início e fim.
2. A pausa possui início e fim próprios, além de motivo obrigatório.
3. A pausa referencia a atividade que estava em andamento (`atividade_id`).
4. A duração da pausa é integralmente descontada da duração bruta da
   atividade (não há, ainda, pausas não descontáveis).
5. Ao finalizar a pausa, o motor retorna automaticamente ao contexto da
   atividade (`Atividade.estado` volta de `PAUSADA` para `ATIVA`).
6. Apenas uma atividade principal pode estar ativa por vez.
7. Apenas uma pausa pode estar ativa por vez.
8. Não é permitido iniciar outra atividade durante uma pausa.
9. Não é permitido encerrar a atividade enquanto houver pausa aberta.
10. Não é permitido encerrar a jornada enquanto houver pausa aberta.
11. Pausas não podem se sobrepor (decorre da regra 7).
12. A pausa deve estar contida no intervalo bruto da atividade
    (`PausaForaDoIntervaloError` se violado).
13. O motivo provisório de teste é `PAUSA_TESTE`; não há catálogo oficial
    ainda.
14. Toda duração é calculada por timestamps persistidos, nunca por relógio
    visual.

## Alternativas consideradas

- **Pausa como subintervalo puramente derivado** (sem entidade própria,
  apenas dois timestamps soltos dentro da atividade): rejeitada por não
  preservar motivo, rastreabilidade individual e não permitir evolução para
  múltiplos tipos de pausa (produtiva/improdutiva) sem reestruturação.
- **Pausa como evento paralelo independente da atividade** (sem vínculo
  formal): rejeitada porque quebraria a regra de retorno automático ao
  contexto da atividade e dificultaria o cálculo de líquido por atividade.
- **Pausa como novo estado da jornada** (em vez de vinculada à atividade):
  rejeitada porque o requisito de negócio é pausar a *atividade*, não a
  jornada como um todo; a jornada apenas herda a restrição de não encerrar
  com pausa aberta.

## Consequências

- O motor de cálculo consegue produzir, apenas com este modelo, os quatro
  números exigidos pelo caso mínimo obrigatório (jornada bruta, atividade
  bruta, pausa, atividade líquida, tempo não classificado).
- Toda pausa é 100% descontável no Incremento 1. Isso **não é definitivo**:
  quando o catálogo oficial de pausas for definido (Incremento 5), esta
  regra poderá ser substituída por uma tabela de classificação
  (descontável / não descontável / produtiva / improdutiva) sem alterar a
  estrutura de entidades (`Pausa` já carrega `motivo` para suportar essa
  evolução).
- "Pausa sem atividade principal em andamento" continua fora de escopo:
  o motor bloqueia essa tentativa com `PausaExigeAtividadeAtivaError` até
  que uma decisão de negócio defina o comportamento correto (seção 6, item
  9 do alinhamento oficial).
- Comportamento de encerramento forçado (jornada ou atividade encerradas
  administrativamente com pendências abertas) não foi implementado; hoje o
  motor apenas bloqueia essas transições.

## Validação operacional

Ainda não realizada. Esta decisão é **provisória**, conforme
`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md` seção 5.1, e deve ser
revalidada com o time operacional antes da adoção definitiva, junto com o
catálogo oficial de pausas do Incremento 5.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, a partir do alinhamento oficial v1.2
  aprovado pelo responsável pelo produto (j.copaz@hotmail.com).
- Revisão pendente: responsável pelo produto, antes do Incremento 5.
