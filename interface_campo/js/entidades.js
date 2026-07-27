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
    ordensServico: [],
    // null ate a atividade ser encerrada (ADR-0025) - encerrarAtividade
    // grava CONCLUIDA, encerrarAtividadeNaoConcluida grava NAO_CONCLUIDA.
    resultado: null,
  };
}

// Numero de OS (texto livre) associado a uma Atividade comum (EE17/EE23,
// ADR-0025). excluida e soft-delete (nunca remove da lista) - "conclusao
// parcial de OS" do ADR-0023.
export function novaOrdemServico({ numero, criadaEm = null }) {
  return {
    id: gerarId(),
    numero,
    criadaEm,
    excluida: false,
  };
}

// Campos revistos no ADR-0021 a pedido do responsavel pelo produto:
// nota/ativo/sintoma/objeto/observacao (objeto = componente causador do
// RASF). causa/acao existem no lado Python por compatibilidade mas nao
// aparecem no formulario da interface de campo - por isso nao tem
// equivalente aqui. gps_*/fotoCaminho sao best-effort (D2/D3, nunca
// exigidos para concluir o atendimento - ver motorJornada.js).
export function novoDadosFalha() {
  return {
    nota: null,
    ativo: null,
    sintoma: null,
    objeto: null,
    observacao: null,
    gpsLatitude: null,
    gpsLongitude: null,
    gpsPrecisaoMetros: null,
    gpsCapturadoEm: null,
    fotoCaminho: null,
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
    eventosSecundarios: [],
  };
}

// Deslocamento, espera ou apoio (ADR-0005) - vinculado direto a Jornada,
// mutuamente exclusivo com a Atividade principal (ver motorJornada.js).
export function novoEventoSecundario({ tipo, motivo, inicio = null }) {
  return {
    id: gerarId(),
    tipo,
    motivo,
    inicio,
    fim: null,
    estado: "CRIADA",
  };
}
