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

### 2026-08-05 | CORS do backend esquecido na migração pro Cloudflare

**Causa raiz**: a migração de `interface_campo/` pro Cloudflare
(ADR-0056) trocou onde o app de campo é servido, mas ninguém atualizou
`_origens_padrao` (lista de origens permitidas no `CORSMiddleware` do
backend) - continuava só com o domínio antigo do Netlify. O app de
campo real (celular) ficou com toda chamada de sincronização bloqueada
pelo próprio navegador, mostrando "sem conexão com o backend".

**Por que não foi pego na hora**: CORS é enforçado pelo **navegador**,
nunca pelo servidor - `WebFetch`/`curl` num backend com CORS mal
configurado responde normal (sem navegador, sem checagem de CORS
nenhuma). A verificação de deploy já estabelecida nesta sessão
(`WebFetch` em `/saude`/`openapi.json`) confirma que o backend está *no
ar*, mas nunca confirmaria que o navegador consegue *falar* com ele.

**Correção**: `_origens_padrao` atualizada para incluir a origem atual
do Cloudflare. Teste novo garante que a origem de produção vigente
sempre está na lista padrão. Ver ADR-0061.

**Lição**: toda migração de hospedagem do app de campo (ou do painel)
precisa checar CORS no backend como um passo explícito do checklist,
não só "o backend está no ar" - as duas verificações são independentes
e uma não implica a outra. `WebFetch`/`curl` nunca vão pegar um
problema de CORS sozinhos, porque eles não são um navegador.

### 2026-08-05 | "Só Pausa pode aninhar numa atividade" parecia regra de motor, era só a lista da tela

**Causa raiz**: a tela só oferecia os 5 códigos `tipo_registro="pausa"`
pra iniciar durante uma atividade/atendimento de falha - parecia
reflexo de uma regra de negócio (só pausa pode nascer dentro de uma
atividade), mas era só escolha de apresentação desde o ADR-0050. O
responsável do produto pediu pra oferecer os outros blocos também.

**Correção**: antes de desenhar qualquer mudança de motor, li
`engine.py`/`motorJornada.js::iniciarPausa` e `calculo.py`/`calculo.js`
diretamente - `tipo_registro` nunca é lido em nenhum dos dois, e a
consolidação de HH já classifica pausa por `catalogo.obter(pausa.motivo)`
(o código específico), nunca por "é do tipo pausa". A mudança pedida
não exigia tocar no motor - só ampliar a lista de códigos oferecida na
tela (`interface_campo/js/app.js`). Ver ADR-0060.

**Lição**: antes de assumir que atender um pedido exige mudar o motor de
domínio (mudança de maior risco, dois lugares - Python e JS - pra
manter sincronizados), ler o código real da regra suspeita primeiro.
Um campo de catálogo com nome que *sugere* ser uma restrição de negócio
(`tipo_registro`) pode ser só metadado de apresentação - só confirmar
lendo onde ele é (ou não) consultado no motor/consolidação evita um
refactor bem maior que o necessário.

### 2026-08-11 | Secret `SGO_API_URL` do painel apontava pro `api.py` de produção sem o endpoint de login

**Causa raiz**: a ADR-0062 (2026-08-07) adicionou `POST /auth/validar` só na
branch `dev` do repositório `Gestão_OS` (decisão deliberada, pra nunca
alterar produção sem revisão explícita do responsável do produto - ver
"Correção pós-revisão de segurança" da própria ADR). Ao configurar os
secrets `SGO_API_URL`/`SGO_WORKFORCE_API_KEY` no Streamlit Cloud do
painel Workforce pra destravar o login (`painel/login.py::exigir_login`),
`SGO_API_URL` foi apontado para `https://gestao-os-ee-mrs-producao.onrender.com`
(a URL de produção, já conhecida de `_sincronizar_baixa_offline`) - que
roda o `api.py` da branch `main`, sem o endpoint novo. O sintoma era
"SGO recusou a validação (HTTP 404)" - fácil de confundir com problema
de senha/chave (401/403), mas 404 significa rota inexistente no
processo que respondeu, nunca autenticação.

**Correção**: `SGO_API_URL` trocado para `https://api-sgo-mrs.onrender.com`
(serviço Render `api-sgo-mrs-dev`, branch `dev`, onde o endpoint
realmente existe) - confirmado antes da troca, via prints do próprio
responsável do produto, que esse serviço tinha deploy live do commit
com `/auth/validar` e as env vars `WORKFORCE_API_KEY_SECRET`/
`AUTH_TOKEN_SECRET` configuradas. `SGO_WORKFORCE_API_KEY` já estava
correto (mesmo valor de `WORKFORCE_API_KEY_SECRET`), não precisou
mudar. Login do painel passa hoje pelo banco de **dev**, não o de
produção - promover pra produção (merge `dev` → `main` no Gestão_OS)
fica como decisão pendente do responsável do produto, mesma ressalva já
registrada na ADR-0062.

**Lição**: quando uma integração nova tem código publicado em mais de
um ambiente/branch (aqui, `dev` com o endpoint vs. `main` sem ele), a
URL configurada no consumidor (o secret `SGO_API_URL` do Workforce)
precisa ser conferida contra qual ambiente specificamente tem o código
esperado - não basta reaproveitar uma URL já conhecida do mesmo
provedor (produção "parecia" a escolha óbvia por já ser usada em outro
fluxo). E: **HTTP 404 num contrato de API é sinal de ambiente/deploy
errado, não de credencial errada** - vale checar isso antes de suspeitar
de senha/chave.

### 2026-08-12 | `hidden` parava de esconder elementos com classe `display:flex` (Etapa 1/2 apareciam juntas)

**Causa raiz**: `.campo` e `.etapa-tela` (`interface_campo/css/estilo.css`)
definem `display: flex` explicitamente. O atributo HTML `hidden` também
aplica `display: none`, mas via regra do navegador (user-agent
stylesheet) com a mesma especificidade CSS (0,1,0) de uma classe -
quando duas regras empatam em especificidade, o CSS do próprio site
vence a do navegador. Resultado: qualquer elemento com `hidden` **e**
uma dessas classes continuava visível. Sintoma real relatado pelo
responsável do produto: a tela de "Pergunta" (Online/Offline,
`#etapaPergunta.etapa-tela`) e o bloco de instrução do modo Offline
(`#blocoOfflineSgo.campo`) apareciam **junto** com a tela de Login,
mesmo com `hidden` sendo alternado corretamente via JS
(`mostrarEtapaPreJornada`) - o problema nunca foi a lógica de estado,
sempre foi essa colisão de CSS.

**Como não foi confundido com cache/deploy**: o usuário testou em aba
anônima (elimina cache do navegador) e o commit no Cloudflare foi
confirmado como o mais recente (mensagem do commit conferida contra o
histórico do Git) - só depois de descartar as duas hipóteses óbvias
(cache, deploy atrasado) é que a causa real (CSS) foi investigada.

**Correção**: uma regra única e genérica no topo do CSS,
`[hidden] { display: none !important; }`, em vez de corrigir classe por
classe - cobre qualquer elemento `hidden` do app, presente ou futuro,
sem precisar lembrar dessa colisão toda vez que uma nova classe com
`display` explícito for criada. `CACHE_VERSAO` v32 → v33.

**Lição**: `hidden` e uma classe com `display` explícito têm a mesma
especificidade CSS - o navegador não dá prioridade nenhuma ao atributo
semântico `hidden` por padrão. Qualquer componente que alterna
visibilidade via `.hidden = true/false` no JS precisa de uma regra
`[hidden] { display: none !important; }` (ou seletor mais específico
tipo `.classe[hidden]`) garantida no CSS desde o início - não é algo que
aparece nos testes automatizados (não renderizam CSS de verdade), só em
teste visual real, e só quando dois elementos "escondidos" coincidem na
mesma tela o suficiente pra notar.

### 2026-08-12 | Duas telas do painel pediam pasta local, nunca funcionaram no Streamlit Cloud

**Causa raiz**: `painel/telas/capacidade_pcm.py` e `dados_exportacoes.py`
continuavam usando `carregar_jornadas(diretorio)`/`carregar_pulsos(diretorio)`
(leitura de arquivo local) enquanto as outras 3 telas do painel
(Dashboard, Falhas, Mapa Operacional) já tinham migrado pra buscar dados
via API desde o ADR-0041. As duas telas nunca foram atualizadas junto -
ficaram pedindo `st.text_input("Diretório de jornadas persistidas")`,
uma caixa de texto que não faz sentido nenhum no Streamlit Cloud (sem
disco persistente compartilhado com a interface de campo lá).

**Como foi encontrado**: não veio de um relato de bug específico - surgiu
de uma auditoria de UI pedida pelo responsável do produto ("algumas abas
estão poluídas, gráficos bizarros"), lendo as 6 telas do painel por
completo em vez de confiar só na descrição do sintoma.

**Correção**: as duas telas migradas pro mesmo padrão `carregar_jornadas_via_api`/
`carregar_pulsos_via_api` + `st.secrets` já usado nas outras 3. Ver
ADR-0066.

**Lição**: quando uma decisão de arquitetura muda (aqui, "fonte de dados
fixa em API", ADR-0041), migrar só as telas mais usadas/visíveis e
assumir que as outras "devem ter sido pegas junto" é um risco real -
vale um grep pelo padrão antigo (`carregar_jornadas(` sem `_via_api`)
depois de qualquer migração desse tipo, não só confiar na memória de
quais arquivos foram tocados no commit da migração original.

### 2026-08-12 | Tela de Configurações expunha URL e token do backend em campo editável

**Causa raiz**: `painel/telas/configuracoes_catalogo.py` carregava
`SYNC_API_URL`/`SYNC_TOKEN` de `st.secrets` só como valor *padrão* de
dois `st.text_input` editáveis e visíveis na tela - as outras telas do
painel já tinham a decisão explícita de nunca mostrar/pedir credencial
na tela (só `st.secrets`, fail closed se ausente), mas esta tela (mais
antiga, nunca revisada) ficou com o padrão anterior.

**Correção**: mesmo padrão `st.secrets` + `st.error`/`st.stop()` das
demais telas - nenhum campo de credencial na tela. Ver ADR-0066.

**Lição**: mesma dos incidentes acima (CSS `[hidden]`, pasta local) -
uma decisão de segurança/arquitetura tomada e aplicada nas telas
"principais" precisa de uma varredura explícita nas telas menos usadas
(Configurações, aqui) pra confirmar que também foi aplicada lá, em vez
de assumir que "decisão tomada" significa "decisão em todo lugar".

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
