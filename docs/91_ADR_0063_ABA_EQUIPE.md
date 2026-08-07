# ADR-0063 | Aba Equipe (múltiplos colaboradores por Atividade)

## Contexto

Pedido original do responsável pelo produto (mensagem que abriu a
integração com o SGO, 2026-08-07): depois da tela de login por matrícula,
"é importante ter uma Aba de Equipe, para selecionar mais de uma pessoa".
Ficou pendente enquanto a integração de login/SSO com o SGO (ADR-0062) era
resolvida - retomado agora a pedido explícito ("pode seguir com as
pendências").

## Decisão

Equipe é **metadado anexado à Atividade**, não uma mudança no modelo de
Jornada: `Jornada.colaborador_matricula` continua sendo o único dono/HH
(regra de ouro 4 - nunca dois eventos ativos incompatíveis para o mesmo
colaborador; uma Jornada compartilhada por várias pessoas exigiria
repensar isso do zero). Cada membro da equipe é só uma matrícula (texto
livre) registrada como "esteve presente nesta atividade" - não gera HH
próprio, não vira uma segunda Jornada.

Implementação espelha **exatamente** o padrão já usado por Ordem de
Serviço (ADR-0025) nos dois lados do domínio (Python e JS): lista anexada
a `Atividade`, adicionar/excluir com soft-delete (nunca remove da lista),
serialização com compatibilidade retroativa (`.get(..., [])`).

**Única diferença de regra em relação a OS**: Equipe é permitida também em
atendimento de falha (`OrdemServico` exige atividade sem `dados_falha`;
`MembroEquipe` não tem essa restrição) - quem estava presente independe do
tipo de atividade.

### Pontos tocados

- `src/workforce_core/entities.py`: `MembroEquipe` (novo) +
  `Atividade.equipe`.
- `src/workforce_core/engine.py`: `adicionar_membro_equipe`/
  `excluir_membro_equipe`.
- `src/workforce_core/exceptions.py`:
  `MembroEquipeMatriculaObrigatoriaError`/`MembroEquipeNaoEncontradoError`.
- `src/workforce_storage/serializacao.py`: `membro_equipe_para_dict`/
  `membro_equipe_de_dict`, `equipe` em `atividade_para_dict`/
  `atividade_de_dict`. `FORMATO_VERSAO` 5 → 6.
- `interface_campo/js/entidades.js`: `novoMembroEquipe`, `equipe: []` em
  `novaAtividade`.
- `interface_campo/js/motorJornada.js`: `adicionarMembroEquipe`/
  `excluirMembroEquipe`. **Corrigido também**:
  `normalizarCamposRetrocompativeis` (a mesma função que já existia para
  proteger contra o bug real de produção de 2026-07-31 com
  `ordensServico` ausente) ganhou `atividade.equipe = atividade.equipe ?? []`
  - sem isso, reabrir o app com uma jornada local antiga a esta mudança
    quebraria com o mesmo erro já corrigido uma vez.
- `interface_campo/js/erros.js`: as duas exceções novas.
- `interface_campo/js/sincronizacao.js`: `membroEquipeParaPayload`,
  `equipe` em `atividadeParaPayload`.
- `interface_campo/js/app.js`: `criarBlocoEquipe` (lista + adicionar +
  excluir, mesmo padrão visual de `criarBlocoOrdensServico`) - renderizado
  tanto em atividade comum quanto em atendimento de falha.
- `interface_campo/service-worker.js`: `CACHE_VERSAO` v25 → v26.
- Backend (`src/workforce_api`) e painel: **nenhuma mudança necessária** -
  a jornada inteira é persistida como um único `JSONB` (`jornadas.dados`,
  ver `src/workforce_api/repositorio_postgres.py`), sem coluna própria por
  campo; `equipe` já viaja dentro do JSON existente assim que
  `atividade_para_dict`/`atividade_de_dict` sabem lidar com ele.

## O que fica pendente

- Exibição de Equipe no **painel** (dashboard/tabelas) - hoje só é
  registrada e sincronizada, sem tela própria de visualização.
- `governanca` (Gestão_OS) não é o mesmo conceito de Equipe aqui - se um
  dia a integração de login também quiser validar que a matrícula
  informada existe de verdade no SGO, isso é decisão nova, não
  implementada agora (hoje aceita qualquer texto, igual à própria
  matrícula do colaborador logado).

## Validação de qualidade realizada

- `python -m py_compile`: OK.
- `node --check` em todos os arquivos tocados: OK.
- `pytest` completo: 419 passed (12 testes novos, `tests/test_equipe.py`).
- `node --test tests/js`: 146 passed (10 testes novos, em
  `motorJornada.test.mjs` e `sincronizacao.test.mjs`).

## Validação NÃO realizada

- Teste em celular real (mesma limitação de sempre).

## Data e responsáveis

- Data de registro: 2026-08-07.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com).
