# ADR-0056 | Interface de campo migrada do Netlify para Cloudflare Workers (assets estáticos)

## Contexto

Em 2026-08-05, o Netlify parou de publicar novos deploys de produção do
`interface_campo/` (preso na v18, três versões atrás do que já tinha
sido enviado - v19/ADR-0048, v20/ADR-0050, v21/ADR-0055). O painel
mostrava "MRS Logística is now running on operational credits -
production deploys ... are paused", com o deploy do commit `c61bcd0`
marcado como "Skipped due to account credit usage exceeded".

Pesquisa nos fóruns de suporte do próprio Netlify confirmou que é um
**bug conhecido e generalizado**, afetando várias contas do plano Free
na mesma semana (banner de créditos esgotados aparecendo mesmo com saldo
disponível) - sem workaround da comunidade, só a orientação de abrir
chamado direto com o suporte oficial. Sem previsão de resolução e sem
poder ficar bloqueado (o app tem deploys frequentes pela frente),
decisão do responsável pelo produto: migrar para outra hospedagem
gratuita, mantendo o Netlify como pendência de suporte em paralelo (sem
prioridade).

## Decisão

### 1. Cloudflare Workers (assets estáticos), não Cloudflare Pages

Cloudflare unificou a antiga oferta "Pages" dentro do fluxo de Workers -
o assistente "Create a Worker" no dashboard já cobre publicar um
diretório estático sem nenhum código de Worker. Nenhuma mudança em
`interface_campo/` foi necessária (já é HTML/CSS/JS puro, sem build).

Escolhido em vez de GitHub Pages (banda mais limitada, sem preview por
branch) e Vercel (o plano gratuito restringe uso comercial nos termos de
serviço - inadequado para uma ferramenta de trabalho real da MRS).
Free tier do Cloudflare: 500 builds/mês, banda e requisições
ilimitadas, mesmo fluxo de auto-deploy no push que já existia no
Netlify.

### 2. `wrangler.toml` na raiz do repositório

```toml
name = "sgo-workforce"
compatibility_date = "2026-08-05"

[assets]
directory = "./interface_campo"
```

Fica na raiz (não dentro de `interface_campo/`) para não exigir mexer em
"Root directory" nas configurações do projeto Cloudflare - o comando de
deploy (`npx wrangler deploy`, preenchido automaticamente pelo
assistente) roda a partir da raiz do repositório por padrão e lê o
`wrangler.toml` de lá. Sem seção `[build]`/comando de build - o app já é
estático.

### 3. Subdomínio curto antes de divulgar

Pedido explícito do responsável do produto: encurtar a URL antes de
espalhar para os colaboradores. O formato `*.workers.dev` é sempre
`<nome-do-worker>.<subdominio-da-conta>.workers.dev` - o segmento da
conta é obrigatório (namespace compartilhado entre todas as contas
Cloudflare), não dá para ter só `sgoworkforce.workers.dev` puro.

Decisão tomada (`AskUserQuestion`): manter o nome do Worker
(`sgo-workforce` sem hífen no resultado final, ver nota abaixo) e trocar
só o subdomínio da conta - `mrs` sozinho já estava em uso por outra
conta Cloudflare (namespace global), coube `mrslogistica`. URL final:

**`https://sgoworkforce.mrslogistica.workers.dev`**

(o nome do Worker aparece sem hífen no resultado - provável normalização
do próprio Cloudflare ao trocar o subdomínio da conta; não foi criado
nenhum Worker novo, é o mesmo projeto configurado desde o início).

Trocar o subdomínio da conta é uma operação de conta inteira - o
subdomínio antigo (`j-copaz`) parou de resolver completamente assim que
o novo foi confirmado (`getaddrinfo ENOTFOUND` no teste), sem duplicata
nem worker órfão para limpar depois.

### 4. Ativação manual das rotas (achado durante o deploy)

Primeiro deploy voltou 404 tanto em `/` quanto em `/service-worker.js`
mesmo com o `wrangler.toml` correto - causa real: as rotas
`Production`/`Preview` (aba "Domains" do Worker) vêm **desligadas por
padrão** depois do primeiro deploy via GitHub, é preciso ativar o toggle
manualmente. Não é um problema de configuração do `wrangler.toml`.

### 5. Comentário desatualizado corrigido

`interface_campo/js/configSincronizacao.js` tinha um comentário de aviso
de segurança citando "Netlify" explicitamente (o token de sincronização
não é confidencial, é só um freio contra escrita acidental). Atualizado
para não nomear a hospedagem específica, evitando ficar desatualizado de
novo numa próxima migração.

## Validação de qualidade realizada

- `WebFetch` em `/service-worker.js` e `/` da URL final: HTTP 200,
  `CACHE_VERSAO` confirmado em `sgo-workforce-shell-v21`, HTML da
  aplicação real (não página de erro).
- `WebFetch` na URL antiga (`sgo-workforce.j-copaz.workers.dev`):
  `getaddrinfo ENOTFOUND` - confirma que não sobrou nenhuma rota
  duplicada servindo conteúdo antigo/divergente.

## Validação NÃO realizada

- Teste em celular real do novo endereço (mesma limitação de sempre) -
  especialmente importante aqui: quem já tinha o PWA instalado a partir
  do Netlify precisa reinstalar a partir da nova URL, o service worker
  antigo não migra sozinho.
- Chamado de suporte do Netlify não foi aberto (fica como pendência sem
  prioridade, já que o Cloudflare resolveu o bloqueio).

## Pendências

- Avisar todos os colaboradores de campo para trocar o link salvo/atalho
  da tela inicial do celular para `https://sgoworkforce.mrslogistica.workers.dev`.
- Considerar domínio próprio da MRS no futuro (elimina o sufixo
  `workers.dev` por completo, mais robusto atrás de proxy corporativo) -
  não decidido, não é urgente com o subdomínio atual já funcionando.

## Arquivos afetados

- `wrangler.toml` (novo).
- `interface_campo/js/configSincronizacao.js` (comentário).

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
