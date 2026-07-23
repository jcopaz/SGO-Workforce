-- SGO Workforce | esquema conceitual inicial
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS wf_jornadas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_jornada_id UUID UNIQUE NOT NULL,
  usuario_matricula TEXT NOT NULL,
  inicio_em TIMESTAMPTZ NOT NULL,
  fim_em TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('ABERTA','ENCERRADA','CORRIGIDA')),
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_wf_jornada_aberta_usuario
ON wf_jornadas(usuario_matricula) WHERE status='ABERTA';

CREATE TABLE IF NOT EXISTS wf_eventos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_event_id UUID UNIQUE NOT NULL,
  jornada_id UUID NOT NULL REFERENCES wf_jornadas(id),
  tipo_codigo TEXT NOT NULL,
  motivo_codigo TEXT,
  os_referencia TEXT,
  os_ciclo_referencia TEXT,
  ativo_referencia TEXT,
  inicio_em TIMESTAMPTZ NOT NULL,
  fim_em TIMESTAMPTZ,
  status TEXT NOT NULL,
  observacao TEXT,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (fim_em IS NULL OR fim_em >= inicio_em)
);

CREATE TABLE IF NOT EXISTS wf_falhas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evento_id UUID UNIQUE NOT NULL REFERENCES wf_eventos(id),
  numero_nota TEXT NOT NULL,
  ativo_referencia TEXT NOT NULL,
  sintoma_codigo TEXT NOT NULL,
  causa_codigo TEXT NOT NULL,
  acao_codigo TEXT NOT NULL,
  observacao TEXT NOT NULL,
  sistema TEXT,
  componente_causador TEXT,
  impacto TEXT,
  pendente BOOLEAN DEFAULT FALSE,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wf_gps_pulsos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_pulse_id UUID UNIQUE NOT NULL,
  jornada_id UUID NOT NULL REFERENCES wf_jornadas(id),
  usuario_matricula TEXT NOT NULL,
  capturado_em TIMESTAMPTZ NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  precisao_m DOUBLE PRECISION,
  velocidade_ms DOUBLE PRECISION,
  recebido_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wf_gps_jornada_tempo ON wf_gps_pulsos(jornada_id,capturado_em);

CREATE TABLE IF NOT EXISTS wf_auditoria (
  id BIGSERIAL PRIMARY KEY,
  entidade TEXT NOT NULL,
  entidade_id TEXT NOT NULL,
  acao TEXT NOT NULL,
  usuario_matricula TEXT NOT NULL,
  antes JSONB,
  depois JSONB,
  justificativa TEXT,
  registrado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
