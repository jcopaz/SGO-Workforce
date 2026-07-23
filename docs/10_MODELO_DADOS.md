# Modelo de dados

## Entidades
- `wf_usuarios_ref`: referência temporária de identidade.
- `wf_jornadas`: início, fim e status.
- `wf_eventos`: intervalos operacionais.
- `wf_evento_participantes`: equipe e fator HH.
- `wf_falhas`: dados técnicos do atendimento.
- `wf_gps_pulsos`: telemetria.
- `wf_catalogo_eventos`: tipos e regras de cômputo.
- `wf_catalogo_sintomas`, `wf_catalogo_causas`, `wf_catalogo_acoes`.
- `wf_ativos_ref`, `wf_os_ref`: snapshots de integração.
- `wf_sync_lotes`: diagnóstico da sincronização.
- `wf_auditoria`: alterações e correções.

## Chaves
UUID como chave interna. Matrícula, OS, nota e ativo são chaves de negócio/referência, nunca substitutos universais do UUID.

## Datas
Preferir `TIMESTAMPTZ` em UTC. Exibir em America/Sao_Paulo. Nunca armazenar data operacional principal como texto.

## Integridade
- uma jornada aberta por usuário;
- unicidade de IDs de cliente;
- fim maior ou igual ao início;
- falha vinculada a evento do tipo falha;
- pulso vinculado a jornada válida;
- auditoria para edições.
