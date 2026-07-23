# ADR-0005 | Catálogo de motivos e eventos secundários (deslocamento, espera, apoio)

## Contexto

O Incremento 5 do roadmap (`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`,
seção 11) chama-se "Catálogo de pausas, deslocamentos, esperas e apoios". A
mesma seção, em 15.3 "Antes do Incremento 5: catálogo operacional", lista
como pendente: o catálogo oficial de pausas, a classificação
produtiva/improdutiva/não computável, a regra de cômputo de cada motivo, a
regra de pausa sem atividade principal, e a governança de aprovação e
vigência do catálogo. A seção 6 (itens 6 a 9) repete essas mesmas
pendências como decisões que "o agente não deverá inventar".

Ao mesmo tempo, `docs/07_MOTOR_EVENTOS_E_HH.md` — parte da leitura
obrigatória do projeto conforme `CLAUDE.md` — já descrevia um vocabulário
de "categorias iniciais" de evento (deslocamento rodoviário/ferroviário,
refeição, DDS, reunião, treinamento, aguardando material, aguardando
intervalo/liberação, apoio operacional, atividade administrativa, entre
outras) e a regra "apenas um evento principal ativo". Esse vocabulário e
essa regra **não são invenção deste incremento** — já estavam documentados
antes do alinhamento v1.2.

Esta decisão constrói a infraestrutura técnica mínima para representar
catálogo e eventos secundários, sem preencher nenhuma das pendências de
negócio acima.

## Decisão

1. **Taxonomia de categoria** (`workforce_core/catalogo.py:Categoria`):
   enum com as categorias iniciais de `docs/07_MOTOR_EVENTOS_E_HH.md`,
   citadas diretamente, não inventadas.
2. **Classificação de HH nunca decidida por omissão**
   (`ClassificacaoHH`): toda entrada de catálogo nasce com
   `classificacao_hh = NAO_DEFINIDO`. Nenhum código deste incremento define
   um motivo como produtivo ou improdutivo — isso continua sendo decisão do
   responsável pelo produto.
3. **Registro de catálogo em memória** (`CatalogoMotivos`): apenas
   `registrar`/`obter`/`todos`. Sem fonte oficial, sem processo de
   aprovação/vigência — ambos pendentes (seção 15.3).
4. **`catalogo_padrao()`**: popula somente entradas `*_TESTE`
   (`PAUSA_TESTE`, já existente desde o Incremento 1;
   `DESLOCAMENTO_TESTE`, `ESPERA_TESTE`, `APOIO_TESTE`, novas), todas com
   `classificacao_hh = NAO_DEFINIDO`. Estende por analogia a decisão
   explícita da seção 5.3 do alinhamento oficial ("Para o primeiro teste,
   será utilizado o motivo PAUSA_TESTE") aos três novos tipos de evento —
   não é um catálogo oficial, é o mesmo tipo de placeholder de teste já
   autorizado para pausa.
5. **`EventoSecundario`** (`workforce_core/entities.py`): nova entidade
   para deslocamento, espera e apoio, com `tipo`
   (`TipoEventoSecundario.DESLOCAMENTO|ESPERA|APOIO`), `motivo`, `inicio`,
   `fim`, `estado` (`CRIADA/ATIVA/ENCERRADA`, mesma forma da Pausa).
   Ao contrário da Pausa (vinculada a uma Atividade específica), o
   `EventoSecundario` é vinculado diretamente à Jornada.
6. **Exclusão mútua com a atividade principal**: um evento secundário só
   pode começar se não houver atividade principal ativa/pausada, e uma
   atividade só pode começar se não houver evento secundário ativo
   (`EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError`,
   `AtividadeExigeNenhumEventoSecundarioAtivoError`). Isso é a tradução
   literal da regra "apenas um evento principal ativo" de
   `docs/07_MOTOR_EVENTOS_E_HH.md` — não uma regra nova inventada aqui.
7. **Demais restrições, espelhando a Pausa**: apenas um evento secundário
   ativo por vez; tipo e motivo obrigatórios; timestamp de fim não pode
   anteceder o início; jornada não pode ser encerrada com evento secundário
   aberto (`JornadaComEventoSecundarioAbertoError`).
8. **Recuperação de estado**: `MotorJornada.a_partir_de` agora também
   deriva o evento secundário ativo a partir dos estados persistidos, e
   `EstadoInconsistenteError` cobre o novo caso "evento secundário ativo
   simultaneamente com atividade ativa" — a mesma disciplina do Incremento
   2, estendida.
9. **Cálculo**: a duração de eventos secundários entra no "tempo
   classificado" da jornada (`tempo_classificado_jornada`), ao lado de
   atividade líquida e pausas. Isso significa apenas "sabemos o que foi
   esse tempo", não "isso conta como HH produtivo" — a classificação
   produtiva/improdutiva continua não definida (ver item 2).
10. **Persistência**: `FORMATO_VERSAO` sobe de 1 para 2 em
    `workforce_storage/serializacao.py`. Compatibilidade retroativa
    garantida com `.get("eventos_secundarios", [])` — arquivos gravados no
    Incremento 2 (sem esse campo) continuam sendo lidos normalmente, sem
    necessidade de migração.

## Deliberadamente fora deste incremento

- **Conteúdo oficial do catálogo** (quais motivos existem de fato, quais
  são produtivos/improdutivos/não computáveis): continua pendente,
  responsabilidade do time operacional.
- **Pausa sem atividade principal em andamento**: continua bloqueada
  (`PausaExigeAtividadeAtivaError`, inalterado desde o Incremento 1); não
  foi decidido se isso deveria mudar.
- **Governança de aprovação e vigência do catálogo**: nenhum mecanismo de
  versionamento, aprovação ou data de vigência foi criado.
- **Paridade em JavaScript** (`interface_campo/`): `EventoSecundario` e o
  catálogo **não foram portados para `interface_campo/js/`** nesta sessão.
  A interface de campo (Incremento 4) ainda não expõe nenhum botão para
  deslocamento/espera/apoio, então não há risco imediato de a UI exercitar
  um comportamento divergente do motor Python. Isso deve ser feito antes
  de qualquer botão de deslocamento/espera/apoio ser adicionado à
  interface (ver ADR-0004 sobre o risco de duplicação de motor).
- **Rateio entre múltiplas OS, GPS, RASF**: continuam fora de escopo,
  como já registrado nos ADRs anteriores.

## Alternativas consideradas

- **Modelar deslocamento/espera/apoio como subtipos de Pausa** (aninhados
  em uma Atividade): rejeitado porque, na prática operacional descrita em
  `docs/07_MOTOR_EVENTOS_E_HH.md`, esses eventos frequentemente ocorrem
  **entre** atividades (ex.: deslocamento até o próximo ativo), não durante
  uma atividade em andamento — forçar o aninhamento em Atividade exigiria
  uma atividade "fictícia" só para hospedar o evento.
  Manteve-se cada um vinculado diretamente à Jornada.
- **Permitir deslocamento/espera/apoio concorrente com a atividade**:
  rejeitado por contradizer diretamente a regra já documentada "apenas um
  evento principal ativo" — adotar concorrência seria uma decisão de
  negócio nova, não uma leitura do que já existia.
- **Preencher `classificacao_hh` com um valor "razoável" (ex.: deslocamento
  = produtivo)**: rejeitado explicitamente — é exatamente o tipo de decisão
  que a seção 6 do alinhamento oficial proíbe o agente de inventar.

## Validação operacional

Ainda não realizada. Toda a taxonomia de categoria, a classificação de HH e
o catálogo de motivos são provisórios e dependem de validação do
responsável pelo produto e da operação antes de uso real.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (catálogo oficial,
  classificação de HH, governança) antes de qualquer uso real; paridade em
  JavaScript antes de expor estes eventos na interface de campo.
