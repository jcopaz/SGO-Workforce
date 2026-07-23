# Regras de integridade do banco

O SQL inicial é conceitual. Antes da produção, adicionar catálogos referenciados por FK, política de RLS/escopo, índices de consulta, retenção, particionamento de GPS e migrations versionadas.

A exclusão física de eventos operacionais não deve ser permitida no fluxo comum. Use correção auditada e estados.
