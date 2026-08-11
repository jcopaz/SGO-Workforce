// Entidades do Incremento 1, como objetos simples (facil de gravar no
// IndexedDB via structured clone, sem serializacao manual).

export function gerarId() {
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
    equipe: [],
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

// Colaborador (matricula, texto livre) que trabalhou junto numa Atividade -
// aba "Equipe" (pedido do responsavel pelo produto em 2026-08-07). Mesmo
// espirito de novaOrdemServico: excluida e soft-delete, nunca remove da
// lista. Nao afeta calculo de HH - so registro de quem estava presente.
export function novoMembroEquipe({ matricula, adicionadoEm = null }) {
  return {
    id: gerarId(),
    matricula,
    adicionadoEm,
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

// modoApontamentoSgo/pacoteOfflineUrlSgo (integracao SGO, 2026-08-11): decisao
// tomada ANTES de "Iniciar jornada" (nunca digitada depois, ver app.js) sobre
// como o colaborador vai acessar o SGO pra apontar OS - "online" (SSO via
// ?sid=, mesmo mecanismo ja existente) ou "offline" (pacote PWA do SGO,
// gerado e aberto 1x online pelo proprio colaborador antes de sair do
// sinal - a URL fica guardada aqui pra abrir offline depois, no EE17). Nao
// afeta HH (nunca entra em sincronizacao.js::paraPayloadSincronizacao) - e
// so a referencia de qual link abrir quando a atividade começar.
export function novaJornada({ colaboradorMatricula, modoApontamentoSgo = null, pacoteOfflineUrlSgo = null }) {
  return {
    id: gerarId(),
    colaboradorMatricula,
    inicio: null,
    fim: null,
    estado: "NAO_INICIADA",
    atividades: [],
    eventosSecundarios: [],
    modoApontamentoSgo,
    pacoteOfflineUrlSgo,
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

// Pulso de GPS (Fase 2 da captacao de geolocalizacao, ADR-0043/0045) -
// mesmo contrato de workforce_core.entities.PulsoGps, em camelCase. Gravado
// localmente por captura periodica ou pela trava de "GPS obrigatorio" antes
// de iniciar/encerrar jornada/atividade (app.js). `sincronizado` e um
// controle so local (nao existe no lado Python) para saber o que ainda
// falta enviar no proximo gatilho de sincronizacao.
export function novoPulsoGps({
  jornadaId,
  colaboradorMatricula,
  latitude,
  longitude,
  precisaoMetros,
  timestampDispositivo,
  velocidadeMetrosSegundo = null,
  direcaoGraus = null,
}) {
  return {
    id: gerarId(),
    jornadaId,
    colaboradorMatricula,
    latitude,
    longitude,
    precisaoMetros,
    timestampDispositivo,
    velocidadeMetrosSegundo,
    direcaoGraus,
    sincronizado: false,
  };
}
