// Persistencia local via IndexedDB (Incremento 4).
//
// Mesma logica de workforce_storage (Incremento 2), adaptada ao ambiente
// de navegador: o IndexedDB grava objetos com Date nativamente (structured
// clone), entao nao ha necessidade de serializar timestamps manualmente
// como no lado Python (que usa arquivos JSON). O contrato de campos
// permanece o mesmo (ver docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md
// e docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

const NOME_BANCO = "sgo_workforce";
// v2 (Fase 2 da captacao de geolocalizacao, ADR-0045): acrescenta o object
// store `pulsos`. Upgrade e aditivo - quem ja tinha o banco na v1 mantem a
// jornada gravada, so ganha o store novo.
const VERSAO_BANCO = 2;
const ARMAZENAMENTO_JORNADAS = "jornadas";
const ARMAZENAMENTO_PULSOS = "pulsos";

function abrirBanco() {
  return new Promise((resolve, reject) => {
    const requisicao = indexedDB.open(NOME_BANCO, VERSAO_BANCO);
    requisicao.onupgradeneeded = () => {
      const db = requisicao.result;
      if (!db.objectStoreNames.contains(ARMAZENAMENTO_JORNADAS)) {
        db.createObjectStore(ARMAZENAMENTO_JORNADAS, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(ARMAZENAMENTO_PULSOS)) {
        db.createObjectStore(ARMAZENAMENTO_PULSOS, { keyPath: "id" });
      }
    };
    requisicao.onsuccess = () => resolve(requisicao.result);
    requisicao.onerror = () => reject(requisicao.error);
  });
}

// Grava o estado inteiro da jornada de forma atomica (uma unica transacao
// IndexedDB `put`, que ou aplica por completo ou nao aplica nada). Deve ser
// chamada apos cada transicao confirmada localmente, para que um
// fechamento abrupto do navegador nunca perca eventos ja confirmados.
export async function salvarJornada(jornada) {
  const db = await abrirBanco();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARMAZENAMENTO_JORNADAS, "readwrite");
    tx.objectStore(ARMAZENAMENTO_JORNADAS).put(jornada);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

export async function carregarJornada(id) {
  const db = await abrirBanco();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARMAZENAMENTO_JORNADAS, "readonly");
    const requisicao = tx.objectStore(ARMAZENAMENTO_JORNADAS).get(id);
    requisicao.onsuccess = () => resolve(requisicao.result ?? null);
    requisicao.onerror = () => reject(requisicao.error);
  });
}

export async function listarJornadas() {
  const db = await abrirBanco();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARMAZENAMENTO_JORNADAS, "readonly");
    const requisicao = tx.objectStore(ARMAZENAMENTO_JORNADAS).getAll();
    requisicao.onsuccess = () => resolve(requisicao.result || []);
    requisicao.onerror = () => reject(requisicao.error);
  });
}

// Recuperacao de estado apos fechamento/reinicio: procura a jornada aberta
// mais recente, se existir. So deveria existir no maximo uma (regra de
// ouro: um colaborador so pode ter uma jornada aberta por vez), mas a
// funcao nao assume isso silenciosamente - retorna a lista completa para
// quem chama decidir o que fazer se encontrar mais de uma.
export async function listarJornadasAbertas() {
  const todas = await listarJornadas();
  return todas.filter((jornada) => jornada.estado === "ABERTA");
}

// Fila local de pulsos de GPS (Fase 2 da captacao de geolocalizacao,
// ADR-0045) - mesmo espirito de salvarJornada: um `put` atomico por pulso,
// nunca perde um pulso ja capturado se o navegador fechar antes da proxima
// sincronizacao.
export async function salvarPulso(pulso) {
  const db = await abrirBanco();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARMAZENAMENTO_PULSOS, "readwrite");
    tx.objectStore(ARMAZENAMENTO_PULSOS).put(pulso);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

async function listarPulsos() {
  const db = await abrirBanco();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARMAZENAMENTO_PULSOS, "readonly");
    const requisicao = tx.objectStore(ARMAZENAMENTO_PULSOS).getAll();
    requisicao.onsuccess = () => resolve(requisicao.result || []);
    requisicao.onerror = () => reject(requisicao.error);
  });
}

// Filtro em memoria (mesmo estilo de listarJornadasAbertas) - o volume por
// jornada (no maximo alguns milhares de pulsos por turno, a 1/minuto) nao
// justifica um indice novo no object store.
export async function listarPulsosPendentes(jornadaId) {
  const todos = await listarPulsos();
  return todos.filter((pulso) => pulso.jornadaId === jornadaId && !pulso.sincronizado);
}

export async function marcarPulsosSincronizados(ids) {
  const db = await abrirBanco();
  const tx = db.transaction(ARMAZENAMENTO_PULSOS, "readwrite");
  const armazenamento = tx.objectStore(ARMAZENAMENTO_PULSOS);
  for (const id of ids) {
    const pulso = await new Promise((resolve, reject) => {
      const requisicao = armazenamento.get(id);
      requisicao.onsuccess = () => resolve(requisicao.result);
      requisicao.onerror = () => reject(requisicao.error);
    });
    if (pulso) {
      armazenamento.put({ ...pulso, sincronizado: true });
    }
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}
