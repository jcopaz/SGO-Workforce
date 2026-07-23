# ADR-0004 | Interface de campo provisória (Incremento 4)

## Contexto

O Incremento 4 exige uma interface operacional simples para celular
(`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 11), e a
arquitetura alvo (seção 4.1) define essa interface como um PWA instalável
em HTML/CSS/JavaScript, com Service Worker, IndexedDB, geolocalização do
navegador e fila local de sincronização.

A seção 15.3 lista como pendente, "antes do Incremento 4": identidade
visual inicial, sequência exata dos botões, mensagens operacionais,
confirmação de encerramento e dispositivo/navegador de referência do
piloto. Nenhuma dessas decisões de produto foi tomada pelo responsável
ainda — o que segue são escolhas técnicas mínimas para ter algo funcional
e testável, não decisões de UX definitivas.

## Decisão

1. **Duplicação deliberada do motor de domínio em JavaScript**
   (`interface_campo/js/motorJornada.js` e `calculo.js`): o PWA precisa
   funcionar 100% offline, sem nenhum backend (não existe API real ainda —
   ver ADR-0003). Isso torna inevitável ter a mesma máquina de estados e o
   mesmo motor de cálculo em dois lugares (Python e JavaScript) até que
   exista uma única fonte de verdade (por exemplo, um backend que a
   interface sempre consulta, ou compilação de um motor único para os dois
   ambientes). O JS foi escrito espelhando `src/workforce_core/` linha a
   linha (mesma ordem de validação, mesmas mensagens, mesmos nomes de
   exceção traduzidos) e validado por
   `tests/js/motorJornada.test.mjs`, que replica os mesmos 13 casos da
   seção 9 do alinhamento oficial (todos passando: `node --test
   tests/js/motorJornada.test.mjs`).
   **Risco aceito**: qualquer mudança de regra de negócio no motor Python
   precisa ser replicada manualmente no motor JS enquanto essa duplicação
   existir. Isso deve ser resolvido antes de produção (ver Consequências).
2. **IndexedDB como armazenamento local** (`interface_campo/js/armazenamento.js`):
   um único object store `jornadas`, chave primária `id` (mesmo UUID
   gerado pelo `crypto.randomUUID()` do navegador), um registro por
   jornada com atividades e pausas aninhadas. Ao contrário do lado Python
   (arquivo JSON, ADR-0002), o IndexedDB grava objetos `Date` nativamente
   via structured clone — não há serialização manual de timestamp aqui.
   O contrato de campos (nomes em português, camelCase) é o que precisará
   ser reconciliado com o formato Python quando a sincronização real for
   implementada.
3. **Recuperação de estado**: ao carregar o app, ele busca jornadas com
   `estado === "ABERTA"` no IndexedDB. Se encontrar exatamente uma,
   reconstrói o motor via `MotorJornada.aPartirDe`, que recalcula
   atividade/pausa ativas a partir dos estados persistidos (mesma lógica
   do Python) e recusa estados inconsistentes. Se encontrar mais de uma
   (o que nunca deveria acontecer), o app **não decide sozinho** qual é a
   válida — exibe erro e pede contato com o suporte técnico, em vez de
   escolher silenciosamente.
4. **Fluxo de botões (provisório)**: sem jornada → "Iniciar jornada"; com
   jornada aberta sem atividade → "Iniciar atividade" / "Encerrar
   jornada"; com atividade ativa → "Iniciar pausa (PAUSA_TESTE)" /
   "Encerrar atividade"; com pausa ativa → apenas "Finalizar pausa" (os
   demais botões ficam indisponíveis, refletindo as restrições do motor).
   Não há confirmação extra antes de encerrar jornada/atividade neste
   incremento — decisão de UX ainda pendente.
5. **Motivo de pausa fixo em `PAUSA_TESTE`**: não há campo de escolha,
   porque o catálogo oficial é decisão do Incremento 5. O aviso "piloto
   técnico" fica visível na tela o tempo todo, para não passar a impressão
   de produto finalizado.
6. **Sem autenticação, sem GPS, sem RASF, sem sincronização real**: a tela
   pede apenas a matrícula (texto livre, sem validação contra uma base de
   usuários — isso é decisão de integração/autenticação futura). Não há
   nenhuma chamada de rede no app; a fila de sincronização do Incremento 3
   (Python) ainda não está conectada a esta interface, porque não existe
   uma API real para ela conversar.
7. **Sanitização de saída**: toda renderização de conteúdo dinâmico usa
   `textContent`/DOM seguro, nunca `innerHTML` com interpolação de string
   — decisão preventiva, já que os próximos incrementos (atendimento de
   falhas, RASF) trarão campos de texto livre digitados pelo usuário
   (sintoma, causa, ação, observação).

## Validação de qualidade realizada

- `node --test tests/js/motorJornada.test.mjs`: 17/17 testes, paridade
  completa com os 13 casos obrigatórios da seção 9 do alinhamento oficial
  mais as regras estruturais e a recuperação de estado.
- `node --check` em todos os arquivos JS do app: sintaxe válida.
- Servidor estático real (`python -m http.server`) servindo
  `interface_campo/`: todos os arquivos referenciados (HTML, CSS, JS,
  manifest, service worker, ícone) respondem HTTP 200, com `Content-Type`
  correto para módulos ES (`text/javascript`) e para o manifest
  (`application/manifest+json`).

## Validação NÃO realizada — limitação explícita deste ambiente

**Não foi possível abrir a interface em um navegador real nem simular
cliques/toques nela.** Não há `chromium-cli` nem Playwright instalados
neste ambiente, e a tentativa de instalação falhou por bloqueio de rede
(erro de verificação de certificado consistente com proxy corporativo — o
mesmo tipo de causa do erro `ENOTFOUND` relatado pelo responsável pelo
produto durante esta sessão). Portanto:

- O fluxo completo (iniciar jornada → iniciar atividade → iniciar pausa →
  finalizar pausa → encerrar atividade → encerrar jornada) **não foi
  clicado de ponta a ponta em um navegador**.
- IndexedDB, Service Worker e geolocalização **não foram exercitados em
  tempo de execução real** (só revisados por leitura de código e
  validados indiretamente pelos testes de lógica em Node).
- Instalação como PWA, comportamento offline real e uso em celular físico
  **não foram testados**.

Isso mantém em aberto, exatamente como o CLAUDE.md exige, a validação
mínima "teste offline/online em celular real" e "teste unitário não
substitui teste em celular real". **Este item continua pendente e precisa
ser feito manualmente** por alguém com acesso a um navegador (abrir
`interface_campo/index.html` via um servidor local, ex.:
`python -m http.server` dentro da pasta `interface_campo/`, e acessar
`http://localhost:8000` do próprio computador ou de um celular na mesma
rede) antes de qualquer piloto real com colaboradores.

## Alternativas consideradas

- **Esperar a API real existir antes de construir qualquer interface**:
  rejeitado porque o Incremento 4 está explicitamente no roadmap antes de
  qualquer incremento de API/backend, e o produto exige operação offline
  mesmo quando a API existir — a interface precisa de motor local de
  qualquer forma.
- **Gerar o JS a partir do Python (transpilação) para eliminar a
  duplicação**: mais robusto a longo prazo, mas adiciona complexidade de
  build antes de o contrato de regras estar maduro; adiado.
- **Framework de UI (React, Vue, etc.)**: rejeitado por ora — "simples
  para o campo" (CLAUDE.md) e o escopo de 6 botões não justificam a
  complexidade de build/toolchain adicional neste incremento.

## Consequências

- Enquanto o motor existir duplicado (Python + JS), toda mudança de regra
  de negócio no domínio precisa de uma micro-sessão espelhada nos dois
  lados, com os dois conjuntos de testes rodando. Isso deve ser sinalizado
  explicitamente em qualquer PR/patch futuro que altere `workforce_core`.
- A ausência de teste em navegador/celular real é um risco conhecido e
  registrado, não uma omissão silenciosa — precisa ser fechado antes de
  qualquer uso com colaboradores reais.
- O contrato de campos do IndexedDB (nomes em camelCase) diverge do
  contrato JSON do lado Python (snake_case/português com underscore) —
  isso precisará de um mapeamento explícito quando a sincronização real
  for implementada (Incremento 3 ainda não está conectado a este
  Incremento 4).

## Validação operacional

Ainda não realizada. Decisão provisória, sujeita a revisão do responsável
pelo produto quanto a identidade visual, sequência de botões, mensagens
operacionais e confirmação de encerramento — e sujeita a teste manual em
navegador/celular real antes de qualquer piloto.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (identidade visual, fluxo de
  botões, mensagens) e teste manual em navegador/celular real por qualquer
  pessoa com acesso a um dispositivo.
