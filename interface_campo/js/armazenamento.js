// Persistencia local via IndexedDB (Incremento 4).
//
// Mesma logica de workforce_storage (Incremento 2), adaptada ao ambiente
// de navegador: o IndexedDB grava objetos com Date nativamente (structured
// clone), entao nao ha necessidade de serializar timestamps manualmente
// como no lado Python (que usa arquivos JSON). O contrato de campos
// permanece o mesmo (ver docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md
// e docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

const NOME_BANCO = "sgo_workforce";
const VERSAO_BANCO = 1;
const ARMAZENAMENTO_JORNADAS = "jornadas";

function abrirBanco() {
  return new Promise((resolve, reject) => {
    const requisicao = indexedDB.open(NOME_BANCO, VERSAO_BANCO);
    requisicao.onupgradeneeded = () => {
      const db = requisicao.result;
      if (!db.objectStoreNames.contains(ARMAZENAMENTO_JORNADAS)) {
        db.createObjectStore(ARMAZENAMENTO_JORNADAS, { keyPath: "id" });
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
