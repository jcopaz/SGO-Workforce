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
// equipeJornada/espelhoDe (2026-08-12): "Equipe da jornada" - quem mais
// participou, escolhido logo apos a pergunta Online/Offline (nao mais
// digitado por atividade como a aba Equipe do ADR-0063). Diferente daquela,
// AQUI o HH e' replicado de verdade: ao encerrar, o app gera uma jornada
// "espelho" por colega (mesmos timestamps/eventos, colaboradorMatricula
// trocada) e sincroniza cada uma - ver app.js::gerarJornadasEspelho.
// `equipeJornada` so' existe na jornada REAL (a do dono, quem logou); uma
// jornada espelho SEMPRE nasce com equipeJornada=[] (nunca re-espelha) e
// `espelhoDe` preenchido com a matricula de quem originou - marca de
// auditoria LOCAL (fica no IndexedDB do aparelho), pra pelo menos ali
// sempre dar pra distinguir "HH capturado por evento real" de "HH
// replicado por declaracao de colega" (regra de ouro 2/3 do CLAUDE.md).
// LIMITACAO CONHECIDA: `espelhoDe`/`equipeJornada` NAO entram no payload
// de sincronizacao (mesmo motivo de modoApontamentoSgo - o backend
// (`workforce_storage.serializacao.jornada_de_dict`) so' reconhece campos
// fixos do dataclass Jornada em Python, ignoraria esses dois sem
// persistir) - uma vez sincronizada, a jornada espelho fica
// indistinguivel de uma jornada real no backend/painel. Persistir essa
// marca de verdade no servidor exigiria mudanca no dominio Python
// tambem (workforce_core.entities.Jornada + serializacao + repositorio),
// fora do escopo desta rodada - ver ADR-0068.
export function novaJornada({
  colaboradorMatricula,
  modoApontamentoSgo = null,
  pacoteOfflineUrlSgo = null,
  equipeJornada = [],
  espelhoDe = null,
}) {
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
    equipeJornada,
    espelhoDe,
  };
}

// Gera uma jornada "espelho" pra um colega da equipe, a partir da jornada
// JA ENCERRADA do dono (2026-08-12, decisao explicita do responsavel do
// produto apos eu apontar os riscos: HH replicado sem captura propria de
// GPS/evento do colega - aceito conscientemente). Clona tudo (atividades,
// pausas, eventos secundarios, com os MESMOS ids e timestamps - seguro
// porque cada Jornada e' um documento JSONB proprio no backend, sem
// unicidade de id entre jornadas diferentes) e troca so' o que precisa:
// id novo (senao colide com a jornada original na hora de sincronizar),
// colaboradorMatricula do colega, `espelhoDe` marcando a origem, e
// `equipeJornada` zerada (uma jornada espelho nunca gera outro espelho).
// Chamada uma vez por colega em app.js, so' quando a jornada original ja
// esta ENCERRADA (nunca no meio do turno - ver docstring de
// gerarJornadasEspelho em app.js).
export function gerarJornadaEspelho(jornadaOriginal, matriculaColega) {
  const clone = structuredClone(jornadaOriginal);
  return {
    ...clone,
    id: gerarId(),
    colaboradorMatricula: matriculaColega,
    equipeJornada: [],
    espelhoDe: jornadaOriginal.colaboradorMatricula,
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
