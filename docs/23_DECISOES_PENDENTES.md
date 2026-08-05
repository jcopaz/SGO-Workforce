# Decisões pendentes

1. ~~Intervalo padrão dos pulsos GPS.~~ Resolvido em 2026-07-31 (ADR-0043):
   1 pulso por minuto durante a jornada ativa, best-effort, nunca bloqueia.
   Impacto real em bateria/consumo continua **não validado** — só teste em
   celular real ao longo de um turno inteiro resolve isso, nenhum ADR
   decidiu nada sobre limitar/ajustar o intervalo por enquanto.
   ~~Limiares de qualidade (precisão/velocidade plausível)~~ resolvidos em
   2026-08-05 (ADR-0054): precisão máxima 100m, velocidade máxima 50 m/s —
   ver `docs/81_ADR_0054_QUALIDADE_GPS_FOTO_FALHA_E_EXPURGO_PULSOS.md`.
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
4. ~~Regra de pausa: evento filho ou suspensão/fechamento.~~ Já
   implementado como evento filho: `Pausa.atividade_id` amarra a pausa à
   atividade que a contém, e `calculo.duracao_atividade_liquida` desconta
   o tempo de pausa do total da atividade (não fecha/suspende a atividade
   como um evento independente). Nunca tinha sido registrado aqui como
   decisão porque foi implementado direto, sem ADR dedicado.
5. ~~Escalas e fonte de capacidade bruta.~~ Escopo redefinido em
   2026-07-27: PCM não vai usar esta aplicação por enquanto — a proposta
   de valor do Workforce nesta fase é mostrar a capacidade líquida
   produtiva de HH com o mapeamento das atividades por colaborador, não
   alimentar o processo de PCM diretamente. Capacidade PCM (Incremento 12,
   ADR-0012/ADR-0015) continua existindo no código, mas não é mais
   prioridade de evolução; como entregar essa informação ao PCM fica para
   decidir depois.
6. ~~Associação de múltiplas OS no mesmo evento.~~ Já implementado:
   `Atividade.ordens_servico: List[OrdemServico]` (ADR-0025) — uma
   atividade pode ter mais de uma OS. Nunca tinha sido registrado aqui
   como decisão porque foi implementado direto, sem passar por este
   arquivo.
7. ~~Obrigatoriedade de GPS para iniciar/encerrar.~~ Resolvido em
   2026-07-27 para o atendimento de falha: best-effort, nunca bloqueia
   ("Concluir atendimento" exige só nota/ativo/sintoma/objeto/observação).
   Ver `docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md`. Não
   cobre pulsos periódicos de jornada (item 1) nem obrigatoriedade fora do
   atendimento de falha.
8. ~~Evidência fotográfica em falhas.~~ Resolvido em 2026-07-27: upload
   opcional (best-effort) para Supabase Storage, mesmo ADR-0022. Exibição
   no painel implementada em 2026-08-05 (ADR-0054) — aba Falhas, coluna
   "Foto" + seção com carregamento sob demanda via URL assinada.
9. Nível de detalhe do mapa por perfil. Bloqueado pelo item 13
   (login/autenticação) — sem usuário autenticado não existe "perfil" pra
   diferenciar o que cada um vê. Deliberadamente adiado junto com o item 13.
10. ~~Hospedagem e autenticação do piloto.~~ Resolvido no escopo do piloto
    em 2026-07-26: backend FastAPI no Render + Postgres hospedado + token
    fixo (`SYNC_TOKEN`). Não é o desenho de autenticação final de
    produção — ver `docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md`.
11. ~~Critérios de catálogo novo e aprovação.~~ Resolvido em 2026-07-27:
    nenhuma política formal por enquanto — o catálogo dinâmico
    (ADR-0019) fica limitado à tela de administração já existente
    (`painel/telas/configuracoes_catalogo.py`), sem workflow de
    aprovação. Revisar se a escala de uso aumentar.
12. ~~Forma de importação periódica do RASF.~~ Decidido em 2026-08-05
    (ADR-0053): continuar manual, do jeito que já é feito hoje, por
    enquanto. Nenhuma automação de importação entra no escopo agora.
13. Login/autenticação de usuário (painel e interface de campo). Avaliado
    em 2026-07-27 (reaproveitar a base de usuários do SGO exigiria
    depender do Postgres de produção dele, antecipando a Fase 5 do
    roadmap) — responsável pelo produto decidiu adiar por enquanto. Ver
    `docs/45_ADR_0018_FILTROS_E_GRAFICOS_DASHBOARD.md`.
14. Fonte de tempo planejado por atividade/OS para o indicador de
    Performance (Tempo Planejado / Tempo Real, ADR-0027). Decidido em
    2026-08-05 (ADR-0053): esperar a Fase 5 (integração com o SGO) — o
    tempo planejado deve vir de lá, sem inventar uma tabela própria de
    tempos padrão agora. Nem `OrdemServico` nem `Atividade` têm hoje uma
    duração estimada; a fórmula já está pronta em
    `workforce_core.consolidacao.performance`, só sem fonte de dado até a
    Fase 5.
15. ~~Revisar classificação de `EE16` "Desmontar atividade".~~ Resolvido
    em 2026-07-31: responsável do produto confirmou "Pode classificar
    como Produtiva Não Rentável". Ver
    `docs/55_ADR_0028_PRODUTIVA_NAO_RENTAVEL.md`.
16. ~~Adotar (ou não) uma quarta categoria em `ClassificacaoHH`
    equivalente a "Produtiva Não Rentável".~~ Resolvido em 2026-07-31,
    mesma decisão do item 15 — `ClassificacaoHH.PRODUTIVA_NAO_RENTAVEL`
    criada e aplicada a `EE11`-`EE16`, `EE18`-`EE20`, `EE22`. `EE17`/`EE21`
    continuam `PRODUTIVA` (correspondência com "Ordem de Serviço" do
    original é a única inequívoca) — ver ADR-0028 para o detalhe do que
    ficou de fora.
17. ~~Se `EE21` "Atendimento de Falha" deveria ser `PRODUTIVA` (rentável,
    como estava) ou `PRODUTIVA_NAO_RENTAVEL`.~~ Decidido em 2026-08-05
    (ADR-0053): `PRODUTIVA_NAO_RENTAVEL`, confirmando a leitura já
    registrada como provável (manutenção não planejada no OptJob original
    era não rentável). `EE23` (Manutenção Programada Não Concluída) NÃO
    foi incluída nesta decisão — continua `PRODUTIVA`, não foi perguntada.

Nenhuma decisão deve ser inventada pelo agente. Registrar ADR após validação operacional.
