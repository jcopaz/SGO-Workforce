// Service worker minimo: cacheia o app shell para permitir uso offline
// (apontamento de jornada/atividade/pausa nao pode depender de rede).
//
// Estrategia: cache-first para os arquivos do app shell, sem cache de
// nenhuma chamada de rede (nao ha API real ainda - ver
// docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

const CACHE_VERSAO = "sgo-workforce-shell-v27";
const ARQUIVOS_APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/estilo.css",
  "./js/app.js",
  "./js/motorJornada.js",
  "./js/calculo.js",
  "./js/entidades.js",
  "./js/enums.js",
  "./js/erros.js",
  "./js/armazenamento.js",
  "./js/relogioSimulado.js",
  "./js/configSincronizacao.js",
  "./js/sincronizacao.js",
  "./js/catalogoMotivos.js",
  "./js/catalogoRasf.js",
  "./js/geolocalizacao.js",
  "./js/fotoFalha.js",
  "./js/continuacoesFalha.js",
  "./js/estruturaCodigos.js",
  "./js/configSgo.js",
  "./js/integracaoSgo.js",
  "./icons/icone.svg",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE_VERSAO).then((cache) => cache.addAll(ARQUIVOS_APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((chaves) =>
        Promise.all(
          chaves
            .filter((chave) => chave !== CACHE_VERSAO)
            .map((chave) => caches.delete(chave))
        )
      )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  if (evento.request.method !== "GET") {
    return;
  }
  evento.respondWith(
    caches.match(evento.request).then((respostaEmCache) => {
      if (respostaEmCache) {
        return respostaEmCache;
      }
      return fetch(evento.request).catch(() => respostaEmCache);
    })
  );
});
