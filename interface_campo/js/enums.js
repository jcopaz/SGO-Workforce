// Estados do dominio, espelhando src/workforce_core/enums.py
// (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 8).

export const EstadoJornada = Object.freeze({
  NAO_INICIADA: "NAO_INICIADA",
  ABERTA: "ABERTA",
  ENCERRADA: "ENCERRADA",
});

export const EstadoAtividade = Object.freeze({
  CRIADA: "CRIADA",
  ATIVA: "ATIVA",
  PAUSADA: "PAUSADA",
  ENCERRADA: "ENCERRADA",
});

export const EstadoPausa = Object.freeze({
  CRIADA: "CRIADA",
  ATIVA: "ATIVA",
  ENCERRADA: "ENCERRADA",
});
