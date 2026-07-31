# Motor de eventos e HH

## Modelo
A jornada contém eventos. Evento tem início, fim, categoria, motivo, vínculo opcional com OS/ativo e origem.

## Categorias iniciais
- atividade planejada;
- atendimento de falha;
- deslocamento rodoviário;
- deslocamento ferroviário;
- refeição;
- DDS;
- reunião;
- treinamento;
- aguardando material;
- aguardando intervalo/liberação;
- apoio operacional;
- atividade administrativa;
- outros catalogados.

## Máquina de estados
`CRIADO -> ATIVO -> PAUSADO/SUSPENSO -> RETOMADO -> ENCERRADO`.

## Regras
- apenas uma jornada aberta por usuário;
- apenas um evento principal ativo;
- iniciar pausa suspende a atividade atual ou cria intervalo filho conforme configuração;
- finalizar pausa retoma o contexto anterior, se válido;
- encerramento de jornada fecha pendências somente mediante confirmação e motivo;
- intervalos não podem ter duração negativa;
- sobreposição é bloqueada ou enviada para auditoria;
- edição posterior requer perfil e trilha de auditoria.

## Cálculos
- duração bruta = fim - início;
- duração líquida da atividade = duração bruta - pausas descontáveis;
- HH de equipe = duração líquida x participantes válidos;
- HH da OS = soma de eventos líquidos associados;
- jornada conciliada = eventos + lacunas + intervalos não computáveis.

## Indicadores (ADR-0027)
- **Utilização HH** = Horas Produtivas / Horas Totais — quanto do
  período de trabalho o colaborador converteu em manutenção executável.
  Horas Produtivas soma a duração classificada como `ClassificacaoHH.PRODUTIVA`
  no catálogo (`workforce_core.consolidacao.resumo_por_classificacao_hh`);
  Horas Totais é a jornada bruta. Implementado em
  `workforce_core.consolidacao.utilizacao_hh`.
- **Performance** = Tempo Planejado / Tempo Real — quão aderente o
  colaborador esteve ao tempo planejado de execução da(s) atividade(s).
  Fórmula implementada em `workforce_core.consolidacao.performance`, mas
  **sem fonte de "tempo planejado" ainda** (decisão pendente, ver
  `docs/23_DECISOES_PENDENTES.md` item 14) — não exibida em nenhuma tela
  até essa fonte existir.

## Rateio
Quando um evento cobrir várias OS, aplicar regra explícita: proporcional ao HH planejado, divisão igual ou apontamento individual. Registrar qual regra foi usada.
