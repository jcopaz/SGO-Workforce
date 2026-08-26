# ADR-0072 | Cadastro de pátios e camada de pátios no Mapa Operacional

## Contexto

Responsável pelo produto pediu o cadastro de 2 pátios novos na
coordenação de Piaçaguera:

- `IPN` - Pátio Prainha
- `ICQ` - Pátio Casqueiro

`docs/13_MAPA_OPERACIONAL.md` já listava "ativos e pátios" como camada
prevista do mapa e "coordenação, pátio" como filtro previsto, mas
`docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md` registrava explicitamente
que nenhum dos dois foi implementado porque **o conceito não existia no
domínio do sistema** — não havia tabela, entidade nem endpoint. Não era
uma omissão, era ausência de modelo de dados (item 18 de
`docs/23_DECISOES_PENDENTES.md`).

## Decisão

1. **`wf_patios`** — cadastro dinâmico próprio, mesmo padrão do catálogo
   de motivos (ADR-0019): schema mínimo (`codigo` chave primária, `nome`,
   `coordenacao` texto livre, `latitude`, `longitude`, `ativo`), upsert
   por código, sem workflow de aprovação. `coordenacao` fica como campo
   texto no pátio (não virou entidade própria) — decisão do responsável
   pelo produto em 2026-08-26, revisitar se o volume de coordenações
   justificar uma lista própria no futuro.
2. **Backend** (`src/workforce_api/`): `RepositorioPatiosPostgres`
   (`repositorio_patios_postgres.py`) semeia a tabela vazia com os 2
   pátios reais informados pelo responsável pelo produto (coordenadas
   abaixo). `GET /patios` (só ativos) e `POST /patios` (upsert) em
   `app.py`, mesmo padrão de `/catalogo`.
3. **Painel — cadastro sem código** (`painel/telas/configuracoes_catalogo.py`):
   nova seção "Pátios" na tela de Configurações, mesma UI de
   lista + formulário de criar/editar já usada para motivos. Pedido
   explícito do responsável pelo produto: pensando em gerências futuras,
   alguém sem programar precisa conseguir cadastrar pátio/coordenadas de
   outra coordenação sem precisar de código novo.
4. **Mapa Operacional** (`painel/mapa.py`, `painel/telas/mapa_operacional.py`):
   `construir_mapa` ganha `patios`/`mostrar_patios` — marcadores fixos
   (ícone de indústria, popup com código/nome/coordenação), desenhados
   independente de jornada/pulso selecionado (inclusive sem nenhum pulso).
   Camada opcional via checkbox "🏭 Mostrar pátios", mesmo padrão dos
   toggles de trajetória/clusters do ADR-0064. Busca em `GET /patios`
   tolerante a falha (backend fora do ar não bloqueia a tela — jornada/
   pulsos continuam o propósito principal da tela).
5. **Coordenadas reais** (Piaçaguera), informadas diretamente pelo
   responsável pelo produto — nenhum valor geográfico foi inventado ou
   estimado pelo agente:
   - `IPN` - Pátio Prainha: `-23.948095774842265, -46.30579661328678`
   - `ICQ` - Pátio Casqueiro: `-23.91531040683147, -46.41890410191962`

## Achado de segurança durante a implementação

`folium.Marker(tooltip=...)`, ao contrário de `folium.Popup`, **não
escapa HTML por padrão** (confirmado isolando `folium.Marker` com
`tooltip="<script>alert(1)</script>"` — o script apareceu cru no HTML
gerado). Como `nome`/`coordenacao` do pátio vêm de formulário do painel
(dado do usuário, não constante de código), o tooltip do marcador de
pátio tinha o mesmo risco de XSS que já motivou `html.escape()` no popup
de pulso (ADR-0010). Corrigido: `html.escape()` aplicado também ao
tooltip do marcador de pátio. Coberto por
`test_popup_patio_escapa_html_de_campos_controlados_pelo_usuario`.

## Deliberadamente fora deste incremento

- **"Coordenação" como entidade própria e como filtro do mapa** — fica
  texto livre no pátio por enquanto (item 2 da Decisão); filtro de
  coordenação continua não implementado (nenhum widget novo na tela).
- **"Ativos"** (equipamento, distinto de pátio/local físico) continua sem
  modelo de dados — só a metade "pátios" da camada "ativos e pátios" de
  `docs/13` foi implementada aqui.
- **Validação visual em navegador real** — mesma limitação de ambiente já
  registrada nos ADRs 4, 9 e 10 (sem Playwright/chromium-cli disponível).

## Validação realizada

- `python -m py_compile` em todos os módulos alterados.
- `tests/test_serializacao_patio.py` (4 testes): round-trip
  `patio_de_dict`/`patio_para_dict`, defaults para campos ausentes,
  conversão para `float`.
- `tests/test_workforce_api.py` (6 testes novos, seção `/patios`): sem
  token → 401, criar/aparecer no GET, upsert não duplica, inativo omitido
  do GET, payload malformado → 400.
- `tests/test_mapa.py` (5 testes novos): pátios aparecem sem nenhum
  pulso, mapa sem `patios` informado não quebra e não desenha nada,
  `mostrar_patios=False` esconde os marcadores, popup/tooltip escapam
  HTML de campo controlado pelo usuário.
- Suíte completa: `python -m pytest -q` → 451 testes passando.

## Validação NÃO realizada

- **Postgres real** — mesma limitação de ambiente do
  `RepositorioCatalogoPostgres` (sem servidor Postgres disponível), só
  validado por leitura de código.
- **Navegador real** — não foi possível confirmar visualmente o ícone do
  marcador nem o popup renderizado.
- **Confirmação do nome "Casqueiro"** — grafia exatamente como recebida
  do responsável pelo produto; se for erro de digitação (ex.:
  "Cascalheiro"), corrigir com um `POST /patios` (upsert, não precisa de
  migração) antes do primeiro deploy em produção com dado real.

## Correção pós-registro (2026-08-26, mesmo dia)

Responsável pelo produto confirmou, em conversa com um líder de campo, que
o código correto do Pátio Casqueiro é **`ICQ`**, não `IQC` como
originalmente informado — bate com o prefixo real dos ativos de campo
(`S-ICQ005E1`, `S-ICQ005D1`, "SINALEIRO PN") e com o código já usado no
Gestão_OS (`COORDENADAS_FIXAS["ICQ"]`, app irmão, projeto separado). O
código `IQC` na verdade se refere a outra coisa — "Extensão Cubatão 1" —
que **não foi cadastrada** neste incremento (sem coordenadas informadas
ainda). Todas as ocorrências de `IQC` neste ADR, no cadastro semente
(`repositorio_patios_postgres.py`) e nos testes foram corrigidas para
`ICQ`. Coordenadas mantidas como originalmente informadas (decisão
explícita do responsável pelo produto, mesmo existindo um `ICQ` com
coordenadas diferentes — ~2,1 km — no Gestão_OS; pode ser um ponto de
referência antigo/aproximado lá, não necessariamente mais correto).

**`IQC` cadastrado separadamente**: é um local real e distinto —
"Extensão Cubatão 1" —, coordenada informada pelo responsável pelo
produto (`-23.91530182548477, -46.41890965645514`), a ~1 metro da
coordenada do `ICQ` acima. Confirmado como esperado (extensão colada ao
pátio principal), não erro de cópia/cola — os dois marcadores ficam
sobrepostos no mapa.

**Achado relacionado, fora deste repositório**: o líder também reportou
que os mesmos ativos (`S-ICQ005E1`/`S-ICQ005D1`) aparecem classificados
como pátio `IPG` no **Gestão_OS** (app separado, `c:\Users\30028203\Documents\Gestão_OS`).
Investigação de código (só leitura, sem acesso ao Postgres de produção
daquele app neste sandbox) aponta a causa raiz: `_resolver_patio()`
(`Gestão_OS/app.py`, região 5.1) tenta primeiro um match exato contra a
tabela `mapeamento_patios` (populada por upload de planilha em
"Governança → Mapeamento de Ativos → Pátios") antes de qualquer
prefixo/substring — como `"IPG"` nem aparece como substring de
`"S-ICQ005E1"`, a lógica de resolução não erraria sozinha para IPG; a
linha desses `ativo_chave` na tabela já deve estar gravada com
`patio='IPG'`, herdado da planilha original importada. Fora de escopo do
SGO Workforce (regra de ouro 1 do `CLAUDE.md` deste repositório — nunca
acoplar Workforce ao código do SGO/Gestão_OS); correção proposta ao
responsável pelo produto para rodar diretamente no Postgres daquele app:

```sql
-- Rodar no Postgres do Gestão_OS (fora deste repositorio) - verificar antes de aplicar:
SELECT ativo_chave, patio, tipo FROM mapeamento_patios
WHERE ativo_chave IN ('S-ICQ005E1', 'S-ICQ005D1');

UPDATE mapeamento_patios
SET patio = 'ICQ'
WHERE ativo_chave IN ('S-ICQ005E1', 'S-ICQ005D1')
  AND patio = 'IPG';
```

## Data e responsáveis

- Data de registro: 2026-08-26.
- Registrado por: Claude Code, a pedido direto do responsável pelo
  produto (j.copaz@hotmail.com).
- Revisão pendente: confirmar grafia de "Casqueiro", validar visual em
  navegador real, aplicar a migração (`CREATE TABLE IF NOT EXISTS
  wf_patios`, automática na primeira subida do backend) em produção.
