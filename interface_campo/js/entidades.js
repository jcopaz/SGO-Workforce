// Entidades do Incremento 1, como objetos simples (facil de gravar no
// IndexedDB via structured clone, sem serializacao manual).

function gerarId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback apenas para ambientes sem crypto.randomUUID (nao deveria
  // ocorrer em navegador moderno nem em Node >= 19).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function novaPausa({ atividadeId, motivo, inicio = null }) {
  return {
    id: gerarId(),
    atividadeId,
    motivo,
    inicio,
    fim: null,
    estado: "CRIADA",
  };
}

export function novaAtividade({ inicio = null } = {}) {
  return {
    id: gerarId(),
    inicio,
    fim: null,
    estado: "CRIADA",
    pausas: [],
  };
}

export function novaJornada({ colaboradorMatricula }) {
  return {
    id: gerarId(),
    colaboradorMatricula,
    inicio: null,
    fim: null,
    estado: "NAO_INICIADA",
    atividades: [],
  };
}
