# ADR-0024 | Evento Secundário (deslocamento/espera/apoio) na interface de campo

## Contexto

Desde o ADR-0005 (Incremento 5), o motor de domínio em Python
(`src/workforce_core/`) implementa `EventoSecundario` por completo:
entidade vinculada diretamente à Jornada, mutuamente exclusiva com a
Atividade principal, transições `iniciar_evento_secundario`/
`encerrar_evento_secundario`, cálculo de duração e testes (17 casos em
`tests/test_eventos_secundarios.py`). O ADR-0014 catalogou os 15 códigos
reais do Relatório 1 que são `evento_secundario`, mas nunca portou nada
disso para `interface_campo/js/` — os dois ADRs registram isso
explicitamente como "um trabalho do tamanho de um incremento próprio".

O responsável pelo produto pediu para avançar nessa frente nesta sessão.
Este ADR fecha essa lacuna: portar o motor para JavaScript e dar à
interface de campo uma tela para deslocamento/espera/apoio.

## Decisão

### 1. Mapeamento código → tipo do motor

O motor só conhece 3 tipos genéricos (`TipoEventoSecundario.DESLOCAMENTO`/
`ESPERA`/`APOIO`), mas o catálogo real tem 15 códigos. O ADR-0014 já
descrevia o mapeamento em prosa para 14 deles; o 15º (`EE01`, "Preparação
para jornada") não tinha tipo atribuído. Classificado como `APOIO` por
decisão do responsável pelo produto nesta sessão. Mapeamento final:

| Tipo | Códigos |
|---|---|
| `DESLOCAMENTO` | EE12, EE13, EE14 |
| `ESPERA` | EE03, EE04, EE05, EE06, EE09, EE10 |
| `APOIO` | EE01, EE08, EE15, EE16, EE18, EE19 |

`EntradaCatalogo` (`src/workforce_core/catalogo.py`) ganha o campo
`tipo_evento_secundario: Optional[TipoEventoSecundario] = None`, populado
para os 15 códigos acima em `_RELATORIO_1_ENTRADAS`. Mesmo espírito de
`tipo_registro` (ADR-0019): a interface de campo não precisa de um
segundo mapeamento manual, o catálogo dinâmico já entrega o tipo junto
com cada motivo.

### 2. Catálogo dinâmico (Postgres/Render) estendido, sem endpoint novo

`GET`/`POST /catalogo` já recebem `Dict[str, Any]` genérico e delegam
para `entrada_catalogo_de_dict`/`entrada_catalogo_para_dict`
(`src/workforce_storage/serializacao.py`) — nenhuma rota nem schema
Pydantic novo foi necessário, só estender os serializadores.
`repositorio_catalogo_postgres.py` ganhou a coluna
`tipo_evento_secundario TEXT NULL`. Como a tabela `motivos_catalogo` já
existe em produção (mesma lição do ADR-0023), a coluna nova entra via
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, idempotente, rodado toda vez
que o repositório inicializa — não basta o `CREATE TABLE IF NOT EXISTS`.

### 3. Motor JavaScript ganha paridade completa com o Python

Mirror 1:1 de `entities.py`/`enums.py`/`engine.py`/`exceptions.py`/
`calculo.py`:

- `enums.js`: `EstadoEventoSecundario`, `TipoEventoSecundario`.
- `entidades.js`: `novoEventoSecundario`; `novaJornada()` ganha
  `eventosSecundarios: []`.
- `erros.js`: as 7 exceções (`EventoSecundarioJaAtivoError`,
  `EventoSecundarioNaoAtivoError`,
  `EventoSecundarioTipoObrigatorioError`,
  `EventoSecundarioMotivoObrigatorioError`,
  `EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError`,
  `AtividadeExigeNenhumEventoSecundarioAtivoError`,
  `JornadaComEventoSecundarioAbertoError`).
- `motorJornada.js`: `identificarEstadoAtivo` passa a derivar também
  `eventoSecundarioAtivo` (validando a mesma invariante de exclusão mútua
  na recuperação de estado); `iniciarEventoSecundario`/
  `encerrarEventoSecundario`; `iniciarAtividade` e `encerrarJornada`
  passam a checar o evento secundário ativo, nos dois sentidos.
- `calculo.js`: `duracaoEventoSecundario`/`duracaoEventosSecundarios`;
  `tempoClassificadoJornada` e `resumoJornada` passam a incluir a duração
  de eventos secundários (Regra de Ouro nº 12 - a soma exibida no resumo
  de jornada encerrada continua reconciliando).
- `sincronizacao.js`: `paraPayloadSincronizacao` agora serializa
  `eventos_secundarios` de verdade (antes sempre enviava `[]`, mesmo
  formato que `workforce_storage.serializacao.jornada_para_dict` já
  aceita desde o ADR-0005 via `.get("eventos_secundarios", [])`).
- `catalogoMotivos.js`: nova `obterEventosSecundarios()`, mesmo
  cache/fallback offline de `obterMotivosPausa()` (refatorado para
  compartilhar a busca do catálogo completo, `buscarCatalogoCompleto`, e
  só divergir no filtro por `tipo_registro`). `CATALOGO_MINIMO_OFFLINE`
  estendido dos 5 códigos de pausa para os 20 códigos de
  pausa+evento_secundario (com `tipo_evento_secundario`), para o seletor
  de evento secundário também nunca ficar vazio no primeiro uso offline.

### 4. Tela na interface de campo

`app.js`: na tela "jornada aberta, sem atividade em andamento" (antes só
"Iniciar atividade"/"Iniciar atendimento de falha"/"Encerrar jornada"),
novo seletor com os 15 códigos e botão "Iniciar deslocamento/espera/
apoio". Enquanto ativo: "Deslocamento/espera/apoio em andamento." +
botão "Encerrar evento" (ramo próprio do `if/else if`, mutuamente
exclusivo por construção com os ramos de pausa/atividade). Resumo da
jornada em andamento (`renderResumoEmAndamento`) ganha uma linha para o
evento secundário ativo, mesmo padrão já usado para pausa.

## Deliberadamente fora deste incremento

- **Associação de OS a EE17/EE23**: incremento separado, já com decisões
  de negócio tomadas no ADR-0023 mas ainda não desenhado/construído.
- **Exportações (CSV/XLSX/GeoJSON)**: eventos secundários já entravam no
  cálculo de tempo classificado do lado Python desde o ADR-0005; nenhuma
  mudança de exportação foi necessária ou feita aqui.
- **Governança do catálogo dinâmico**: continua sem processo de
  aprovação/vigência (mesma lacuna do ADR-0019).

## Arquivos afetados

- `src/workforce_core/catalogo.py`, `src/workforce_storage/serializacao.py`,
  `src/workforce_api/repositorio_catalogo_postgres.py`.
- `interface_campo/js/enums.js`, `entidades.js`, `erros.js`,
  `motorJornada.js`, `calculo.js`, `sincronizacao.js`, `catalogoMotivos.js`,
  `app.js`.
- `tests/test_catalogo_relatorio_1.py`, `tests/test_serializacao_catalogo.py`,
  `tests/js/motorJornada.test.mjs`, `tests/js/catalogoMotivos.test.mjs`,
  `tests/js/sincronizacao.test.mjs`.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados: OK.
- `pytest` completo: 230/230 (era 226 antes deste incremento).
- `node --check` em todos os arquivos de `interface_campo/js/`: sintaxe
  válida.
- `node --test tests/js`: 89/89 (era 72 antes deste incremento).
- Casos novos cobrem: round-trip de `tipo_evento_secundario` no catálogo,
  mapeamento completo código→tipo, todas as transições/exclusões mútuas
  do motor JS (mesmos 13 casos de `test_eventos_secundarios.py`),
  recuperação de estado e estado inconsistente via `aPartirDe`,
  serialização do payload de sincronização, e fallback/cache do catálogo
  dinâmico para os dois seletores (pausa e evento secundário) a partir da
  mesma busca.

## Validação NÃO realizada

- Teste manual em navegador/celular real da nova tela — mesma limitação
  registrada em todos os ADRs anteriores da interface de campo (nunca
  realizado neste ambiente).
- Migração da coluna `tipo_evento_secundario` no Postgres de produção
  (Render) e reseed dos 15 códigos via `POST /catalogo` — ação manual
  pendente, a ser feita com o responsável pelo produto após o próximo
  deploy (mesma dor operacional do ADR-0023).

## Data e responsáveis

- Data de registro: 2026-07-28.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com), que classificou EE01 como `APOIO` nesta sessão.
