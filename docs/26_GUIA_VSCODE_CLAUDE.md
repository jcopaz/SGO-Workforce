# Guia VS Code e Claude Code

1. Copie o pacote para a raiz do novo repositório.
2. Mantenha `CLAUDE.md` na raiz.
3. Preserve `.github/copilot-instructions.md`.
4. Crie branch `dev`.
5. Comece pelo banco e motor de estados, não pelos dashboards.
6. Gere testes antes da interface.
7. Use dados sintéticos no desenvolvimento e catálogo RASF sanitizado.
8. Para cada sessão, registre mudança em `CHANGELOG.md` e decisão em ADR quando necessário.

## Estrutura sugerida
`app.py`, `api.py`, `src/domain`, `src/services`, `src/repositories`, `src/ui`, `pwa`, `tests`, `migrations`, `docs`.
