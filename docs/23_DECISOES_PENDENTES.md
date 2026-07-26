# Decisões pendentes

1. Intervalo padrão dos pulsos GPS e impacto em bateria.
2. Política legal/corporativa de captura e retenção.
3. Catálogo oficial de pausas e cômputo de cada item.
4. Regra de pausa: evento filho ou suspensão/fechamento.
5. Escalas e fonte de capacidade bruta.
6. Associação de múltiplas OS no mesmo evento.
7. Obrigatoriedade de GPS para iniciar/encerrar.
8. Evidência fotográfica em falhas.
9. Nível de detalhe do mapa por perfil.
10. ~~Hospedagem e autenticação do piloto.~~ Resolvido no escopo do piloto
    em 2026-07-26: backend FastAPI no Render + Postgres hospedado + token
    fixo (`SYNC_TOKEN`). Não é o desenho de autenticação final de
    produção — ver `docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md`.
11. Critérios de catálogo novo e aprovação.
12. Forma de importação periódica do RASF.

Nenhuma decisão deve ser inventada pelo agente. Registrar ADR após validação operacional.
