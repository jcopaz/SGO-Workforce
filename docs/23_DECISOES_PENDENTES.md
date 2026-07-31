# Decisões pendentes

1. Intervalo padrão dos pulsos GPS e impacto em bateria.
2. ~~Política legal/corporativa de captura e retenção.~~ Resolvido em
   2026-07-27: os aparelhos são da empresa, e a MRS já rastreia o veículo
   hoje e já captava a localização do colaborador no sistema anterior —
   a LGPD já está coberta pela política corporativa existente,
   equivalente ao que o Workforce faz. Não bloqueia nenhum incremento.
3. ~~Catálogo oficial de pausas e cômputo de cada item.~~ Resolvido em
   2026-07-27: os 23 códigos do Relatório 1 tiveram `classificacao_hh`
   validada código a código pelo responsável pelo produto (também
   excluído um código duplicado — antigo EE18 — e criado um novo, EE23,
   "Manutenção Programada Não Concluída"). Ver
   `docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md`.
4. Regra de pausa: evento filho ou suspensão/fechamento.
5. ~~Escalas e fonte de capacidade bruta.~~ Escopo redefinido em
   2026-07-27: PCM não vai usar esta aplicação por enquanto — a proposta
   de valor do Workforce nesta fase é mostrar a capacidade líquida
   produtiva de HH com o mapeamento das atividades por colaborador, não
   alimentar o processo de PCM diretamente. Capacidade PCM (Incremento 12,
   ADR-0012/ADR-0015) continua existindo no código, mas não é mais
   prioridade de evolução; como entregar essa informação ao PCM fica para
   decidir depois.
6. Associação de múltiplas OS no mesmo evento.
7. ~~Obrigatoriedade de GPS para iniciar/encerrar.~~ Resolvido em
   2026-07-27 para o atendimento de falha: best-effort, nunca bloqueia
   ("Concluir atendimento" exige só nota/ativo/sintoma/objeto/observação).
   Ver `docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md`. Não
   cobre pulsos periódicos de jornada (item 1) nem obrigatoriedade fora do
   atendimento de falha.
8. ~~Evidência fotográfica em falhas.~~ Resolvido em 2026-07-27: upload
   opcional (best-effort) para Supabase Storage, mesmo ADR-0022. Exibição
   da foto no painel ainda não existe (só o endpoint).
9. Nível de detalhe do mapa por perfil.
10. ~~Hospedagem e autenticação do piloto.~~ Resolvido no escopo do piloto
    em 2026-07-26: backend FastAPI no Render + Postgres hospedado + token
    fixo (`SYNC_TOKEN`). Não é o desenho de autenticação final de
    produção — ver `docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md`.
11. ~~Critérios de catálogo novo e aprovação.~~ Resolvido em 2026-07-27:
    nenhuma política formal por enquanto — o catálogo dinâmico
    (ADR-0019) fica limitado à tela de administração já existente
    (`painel/telas/configuracoes_catalogo.py`), sem workflow de
    aprovação. Revisar se a escala de uso aumentar.
12. Forma de importação periódica do RASF.
13. Login/autenticação de usuário (painel e interface de campo). Avaliado
    em 2026-07-27 (reaproveitar a base de usuários do SGO exigiria
    depender do Postgres de produção dele, antecipando a Fase 5 do
    roadmap) — responsável pelo produto decidiu adiar por enquanto. Ver
    `docs/45_ADR_0018_FILTROS_E_GRAFICOS_DASHBOARD.md`.
14. Fonte de tempo planejado por atividade/OS para o indicador de
    Performance (Tempo Planejado / Tempo Real, ADR-0027). Nem `OrdemServico`
    nem `Atividade` têm hoje uma duração estimada — precisa de decisão do
    responsável pelo produto (ex.: vir do SGO na Fase 5, uma tabela de
    tempos padrão por tipo de atividade, etc.) antes de qualquer tela
    mostrar Performance. A fórmula já está pronta em
    `workforce_core.consolidacao.performance`.
15. Revisar classificação de `EE16` "Desmontar atividade" — hoje
    `IMPRODUTIVA` em `catalogo.py` (validado no ADR-0023), mas o manual
    original do OptJob (`Referencias/Códigos de Pausas com Figuras
    produção_Via v6`, achado em 2026-07-30 — ver
    `docs/21_APRENDIZADOS_HERDADOS_SGO.md`) classifica "Desmontar
    atividade" como "Produtiva Não Rentável", categoria mais próxima de
    produtivo do que de improdutivo. Pode ser um mismatch real ou uma
    reclassificação intencional já feita no ADR-0023 — só o responsável
    do produto pode confirmar qual das duas.
16. Adotar (ou não) uma quarta categoria em `ClassificacaoHH` equivalente
    a "Produtiva Não Rentável" do OptJob original — cobriria deslocamento,
    preparar/desmontar atividade, carregar/descarregar veículo, SMS,
    manutenção não planejada e treinamento, hoje todos simplesmente
    `PRODUTIVA` no Workforce. Sem essa distinção, o indicador de
    Utilização HH (ADR-0027) mistura produtivo-rentável com
    produtivo-não-rentável no mesmo numerador — pode ou não ser o
    resultado desejado; decisão de negócio do responsável do produto, não
    inferida pelo agente.

Nenhuma decisão deve ser inventada pelo agente. Registrar ADR após validação operacional.
