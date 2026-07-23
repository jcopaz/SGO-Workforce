# GitHub Copilot Instructions | SGO Workforce

Leia `CLAUDE.md` e `docs/00_INDICE.md` antes de sugerir código.

- Produto offline first em Python, Streamlit, FastAPI, PostgreSQL/Neon, IndexedDB e ECharts.
- HH é derivado de eventos. Nunca crie campo de entrada manual como fonte oficial.
- Use timestamps com timezone e IDs UUID.
- Toda gravação offline possui `client_event_id`, status de sync e operação idempotente.
- Um usuário pode ter apenas uma jornada aberta e um evento ativo principal por vez.
- Pausa fecha/suspende a atividade conforme a regra documentada, sem sobreposição silenciosa.
- Falha exige nota, ativo, sintoma, causa, ação e observação conforme catálogo/regra.
- GPS é telemetria auditável, com precisão, timestamp do dispositivo e timestamp do servidor.
- Código por sessões pequenas, funções testáveis, SQL parametrizado e transações explícitas.
- Use ECharts nos dashboards e exportações reconciliáveis em CSV/XLSX.
- Não reescreva módulos inteiros sem necessidade.
