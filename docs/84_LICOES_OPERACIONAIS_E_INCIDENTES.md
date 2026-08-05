# Lições operacionais e incidentes resolvidos

Log vivo de incidentes reais (bug relatado, interpretação errada de
especificação, decisão que precisou ser revertida) com causa raiz,
correção e a lição que fica - inspirado no app irmão Gestão_OS
(`Agente/09_APRENDIZADOS_E_ERROS.md`, ver análise registrada na memória
de sessão em 2026-08-05). Diferente de `docs/21_APRENDIZADOS_HERDADOS_SGO.md`
(motivação histórica herdada do OptJob/SGO original) - este arquivo é
sobre os próprios incidentes deste projeto, daqui pra frente.

Cada ADR já documenta o incidente que motivou a mudança em detalhe; este
arquivo existe pra consolidar o padrão que se repete entre eles, sem
precisar reabrir cada ADR pra encontrar a lição. Adicionar uma entrada
nova sempre que um bug real (não hipotético) for corrigido ou uma
decisão precisar ser revertida por feedback direto do responsável do
produto.

## Incidentes

### 2026-08-01 | Timezone: HH reclassificado no dia UTC errado

**Causa raiz**: agrupamento por data (`linhas_eventos_classificadas`,
`linhas_atendimento_falha`) aplicava `.date()` direto num datetime UTC
sem converter pra horário de Brasília antes. Eventos entre ~21h e meia-
noite de Brasília (já virou o dia seguinte em UTC) eram contados no dia
UTC errado em todos os agrupamentos por data do painel - não era só
exibição, reclassificava HH pro dia errado.

**Correção**: `workforce_core/fuso_horario.py::para_horario_brasil()`
aplicado só no limite de apresentação/agrupamento (nunca na
captura/armazenamento, que corretamente continuam em UTC). Ver
ADR-0047.

**Lição**: qualquer `.date()`/agrupamento por dia sobre um timestamp
aware precisa converter pro fuso do usuário final antes de truncar -
nunca truncar em UTC e assumir que "dia" significa a mesma coisa nos
dois fusos.

### 2026-08-04 | EE22 esquecido na especificação original dos blocos

**Causa raiz**: a especificação escrita pelo responsável do produto pra
reorganizar os 23 códigos EE em blocos (ADR-0050) simplesmente não
citava o EE22 (Treinamento) em bloco nenhum - erro humano de
especificação, não de implementação.

**Correção**: adicionado em Interrupções → Pausas (mesma família de
EE02/EE11). Mais importante: `agruparCodigosDisponiveis` ganhou uma
rede de segurança - código presente no catálogo mas não classificado em
nenhum bloco cai automaticamente num bloco "Outros" em vez de sumir
silenciosamente, e um teste dedicado (`tests/js/estruturaCodigos.test.mjs`)
verifica que todos os códigos reais aparecem exatamente uma vez na
estrutura.

**Lição**: quando uma especificação lista itens de um catálogo já
existente (aqui, os 23 códigos EE01-EE23), validar por código (teste que
compara a especificação contra a fonte de verdade), não confiar que a
lista foi copiada certa - specs escritas por humanos esquecem item às
vezes, principalmente em listas longas.

### 2026-08-05 | Navegação de blocos virou acordeão, especificação pedia todos visíveis

**Causa raiz**: a especificação original (ADR-0050) pedia "3 blocos
operacionais" sem uma imagem/mockup, e foi interpretada como um
drill-down de 2 telas (escolher bloco → ver só os códigos daquele
bloco, escondendo os outros dois) - imagem mental razoável, mas errada.
O responsável do produto só percebeu a diferença testando ao vivo:
"não está vindo separado nesses blocos... um Bloco em negrito e as
opções abaixo, outro bloco em negrito e as opções abaixo, tudo no mesmo
Drill".

**Correção**: `renderSelecaoHierarquica` reescrita pra mostrar todos os
blocos juntos, cada um com título em negrito seguido direto da lista de
códigos - sem estado de navegação, sem "← Voltar". Ver ADR-0055.

**Lição**: uma especificação de UI em texto puro (sem mockup/imagem) tem
mais de uma interpretação visual válida - depois de implementar,
descrever de volta pro responsável do produto o que foi construído
("blocos que expandem ao tocar" vs. "todos os blocos sempre visíveis")
antes de considerar a tarefa encerrada, principalmente quando não há
como o agente testar visualmente no navegador.

**Continuação (mesmo dia, mesma tela, mais 2 rodadas)**: "todos os
blocos sempre visíveis" (ADR-0055) esticou a página inteira com 23
códigos como botões - corrigido com rolagem própria por bloco
(ADR-0058) - até o responsável do produto mostrar um print de uma lista
suspensa nativa e pedir pra voltar a esse formato, agora com
`<optgroup>` por bloco (ADR-0059). Quatro versões da mesma tela (0050 →
0055 → 0058 → 0059) no mesmo dia. **Lição reforçada**: quando o agente
não consegue testar visualmente e a especificação é só texto, o custo
de iterar em cima de UI é alto - vale considerar perguntar por um
mockup/desenho/print de referência (como o responsável do produto
acabou fazendo na 3ª rodada) **antes** da primeira implementação, não só
depois de errar - principalmente pra componentes de seleção/navegação
que o usuário vai usar repetidamente.

### 2026-08-05 | Calendário de dias com jornada removido no dia seguinte de ser criado

**Causa raiz**: ADR-0052 introduziu um calendário (`streamlit-calendar-input`,
pacote pequeno/pouco maduro) pra marcar dias com jornada no filtro do
mapa - risco assumido conscientemente, mas a funcionalidade acabou
sendo mais complexidade do que valor pro fluxo real de uso. O
responsável do produto pediu a remoção completa no dia seguinte, ao
testar ao vivo.

**Correção**: calendário removido por completo (import, coluna, lógica,
dependência do `requirements.txt`); o filtro "Jornada" passou a mostrar
só a data (`dd/mm/aaaa`) em vez do timestamp completo. Ver ADR-0053.

**Lição**: um componente de terceiro pouco maduro adicionado por
"parecer uma boa ideia" deve ser tratado como reversível por padrão -
tempo entre "implementado" e "descartado" foi menor que 24h aqui, o que
é o resultado *certo* de assumir esse risco conscientemente (identificar
rápido que não valia a pena), não uma falha de julgamento.

### 2026-08-05 | Qualidade de GPS nunca avaliada em produção

**Causa raiz**: `workforce_core/qualidade_gps.py::avaliar_pulso` existia
desde o Incremento 7, testado, mas nunca era chamado em lugar nenhum do
pipeline real (captura, sincronização, backend, painel) - os limiares
numéricos (precisão máxima aceitável, velocidade máxima plausível) eram
decisão de negócio deliberadamente pendente, e sem os limiares a função
nunca foi integrada. Sintoma real relatado: pulso final de uma jornada
apareceu no mapa longe da posição real, sem nenhum filtro capaz de
sinalizar isso.

**Correção**: limiares aprovados explicitamente pelo responsável do
produto (precisão ≤100m, velocidade ≤50 m/s) e `reclassificar_qualidade_pulsos`
wireada no carregamento do mapa - pulso suspeito ganha marcador distinto
e sai da trajetória/clusters (camadas de inferência), nunca é apagado
do pulso bruto. Ver ADR-0054.

**Lição**: uma função pronta e testada, mas nunca chamada em produção
porque "falta uma decisão de negócio", é uma lacuna que fica invisível
até um incidente real forçar a pergunta - vale revisitar periodicamente
funções de domínio sem nenhum caller real (`grep` pelo nome da função
fora de `tests/`), não só esperar o incidente.

### 2026-08-05 | `CLAUDE.md` desatualizado em relação a uma decisão já tomada

**Causa raiz**: o ADR-0021 (2026-07-27) simplificou os campos
obrigatórios de atendimento de falha (causa/ação viraram um campo livre
de observação), mas a regra de ouro 6 e a premissa consolidada do
`CLAUDE.md` nunca foram atualizadas - o guia mestre do projeto
contradizia o próprio código/ADR já aprovado havia mais de uma semana.

**Correção**: as duas linhas corrigidas para refletir a regra real
(nota/ativo/sintoma/objeto/observação), com referência ao ADR-0021. Ver
ADR-0054.

**Lição**: um ADR que muda uma regra citada literalmente no `CLAUDE.md`
devia atualizar o `CLAUDE.md` no mesmo commit, não só o doc do ADR -
documentação mestre desatualizada é pior que ausente, porque parece
autoritativa mesmo estando errada.

### 2026-08-05 | Netlify bloqueou deploys de produção por bug de billing

**Causa raiz**: bug generalizado do próprio Netlify (banner "operational
credits" travando deploys mesmo com saldo disponível), confirmado em
múltiplos relatos nos fóruns de suporte deles na mesma semana - não era
um problema de configuração deste projeto.

**Correção**: `interface_campo/` migrado pra Cloudflare Workers (assets
estáticos, sem build) via `wrangler.toml`. Ver ADR-0056.

**Lição**: quando um provedor de hospedagem gratuito trava de forma não
diagnosticável (sem erro claro, sem ação corretiva óbvia do lado do
projeto), não vale insistir tentando "consertar" - confirmar se é um
problema conhecido do provedor (busca em fóruns de suporte oficiais) e,
se for, migrar em vez de esperar. `interface_campo/` sendo HTML/CSS/JS
puro sem build facilitou a migração ser rápida - um lembrete de que
manter dependência mínima de plataforma paga dividendo quando precisa
trocar de provedor às pressas.

## Lições transversais

Princípios que já se repetiram em mais de um incidente acima, valem
como checklist geral:

- **Fail-closed em ação crítica/destrutiva** (regra de ouro 9): qualquer
  endpoint que apaga dado permanentemente deveria ter `dry_run` seguro
  por padrão - aplicado em `POST /pulsos/expurgar` (ADR-0057) depois de
  aprender esse exato padrão com o app irmão Gestão_OS, antes de um
  incidente real forçar a lição aqui.
- **Nunca assumir que `push` bem-sucedido significa deploy no ar** -
  Render, Netlify e (uma vez) Cloudflare já exigiram verificação
  explícita via `WebFetch` antes de considerar uma mudança publicada.
- **Confirmar interpretação de UI com o responsável do produto antes de
  encerrar a tarefa**, principalmente quando a especificação foi só
  texto (sem mockup) e o agente não consegue testar visualmente.
- **Componente/dependência nova = risco assumido conscientemente**,
  reversível por padrão - remover rápido quando não vale a pena, sem
  tratar como fracasso.
- **Documentação mestre (`CLAUDE.md`) muda junto com a decisão que ela
  descreve**, no mesmo commit - nunca deixar pra depois.
- **Função de domínio pronta sem nenhum caller real é uma lacuna
  silenciosa** - vale revisitar antes que um incidente force a pergunta.
