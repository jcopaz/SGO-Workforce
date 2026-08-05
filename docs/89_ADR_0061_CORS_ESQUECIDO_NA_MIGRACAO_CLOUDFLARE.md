# ADR-0061 | CORS do backend esquecido na migração para Cloudflare

## Contexto

Depois da migração de `interface_campo/` para Cloudflare (ADR-0056), o
responsável do produto reportou "Sem conexão com o backend" persistente
no app de campo real. Verificação direta (`WebFetch` em `/saude` e
`/openapi.json`) mostrou o backend saudável e respondendo normalmente -
o que descartava "backend fora do ar" e apontava para algo que só afeta
requisições feitas de dentro de um navegador.

## Causa raiz

CORS é **enforçado pelo navegador**, não pelo servidor - uma chamada
direta ao backend (via `WebFetch`, `curl`, `requests`) nunca passa pela
checagem de CORS, só o `fetch()` feito de dentro de uma página web
passa. `src/workforce_api/app.py::_origens_padrao` (lista de origens
permitidas no `CORSMiddleware`) continuava fixa em
`"https://sgoworkforce.netlify.app,http://localhost:8000"` - a migração
pro Cloudflare (ADR-0056) trocou onde `interface_campo/` é servido, mas
não atualizou de quais origens o backend aceita requisição. O app de
campo real, rodando em `https://sgoworkforce.mrslogistica.workers.dev`,
tinha toda chamada de sincronização bloqueada pelo próprio navegador -
por isso a checagem via `WebFetch` (sem navegador) nunca teria pego
isso sozinha.

## Decisão

`_origens_padrao` atualizada para incluir a origem atual do Cloudflare,
mantendo a do Netlify (sem uso, mas sem custo manter) e localhost:

```python
_origens_padrao = (
    "https://sgoworkforce.mrslogistica.workers.dev,"
    "https://sgoworkforce.netlify.app,"
    "http://localhost:8000"
)
```

`ORIGENS_PERMITIDAS` (variável de ambiente no Render) continua podendo
sobrescrever isso sem precisar de deploy novo - se ela já estiver
configurada no Render com o valor antigo, precisa ser atualizada lá
também (o código não tem como saber/corrigir uma variável de ambiente já
setada).

Novo teste (`tests/test_workforce_api.py::test_origens_permitidas_padrao_inclui_cloudflare_e_netlify`)
confirma que a origem de produção atual está sempre na lista padrão -
protege contra o mesmo esquecimento numa migração futura.

## Validação de qualidade realizada

- `python -m py_compile`: OK.
- `pytest` completo: 400 passed (1 teste novo).
- `WebFetch` confirmando `/saude` (200) e `/openapi.json` acessíveis
  antes de descartar "backend fora do ar" como causa.

## Validação NÃO realizada

- Confirmação de que `ORIGENS_PERMITIDAS` no Render (se já configurada)
  foi atualizada - depende do responsável do produto verificar o
  dashboard do Render, sem acesso direto deste ambiente.
- Teste em celular real depois do deploy (mesma limitação de sempre) -
  também depende do Render publicar o commit, que já estava atrasado
  antes desta mudança (ver observação sobre `/pulsos/expurgar` ausente
  do `openapi.json` de produção no mesmo dia).

## Arquivos afetados

- `src/workforce_api/app.py` (`_origens_padrao`, comentário do módulo).
- `tests/test_workforce_api.py` (teste novo).

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
