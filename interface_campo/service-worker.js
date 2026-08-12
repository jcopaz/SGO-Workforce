// Service worker minimo: cacheia o app shell para permitir uso offline
// (apontamento de jornada/atividade/pausa nao pode depender de rede).
//
// Estrategia: cache-first para os arquivos do app shell, sem cache de
// nenhuma chamada de rede (nao ha API real ainda - ver
// docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

const CACHE_VERSAO = "sgo-workforce-shell-v28";
// Deliberadamente SEM "./assets/logo-workforce.mp4" aqui - cache.addAll e'
// tudo ou nada, e o video (~2,8MB) e' grande demais pra arriscar derrubar
// o app shell inteiro se a rede cair no meio do download. Cacheado a parte,
// best-effort, no proprio handler de "install" abaixo.
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
    caches.open(CACHE_VERSAO).then((cache) =>
      cache.addAll(ARQUIVOS_APP_SHELL).then(() =>
        // Video do logo da tela de login (~2,8MB) e' best-effort - se
        // falhar (rede instavel, arquivo grande), nunca pode derrubar o
        // cache do resto do app shell, que E' critico pro offline-first
        // (regra de ouro 7). Sem ele em cache, a tela de login so perde a
        // animacao ate a proxima visita online - nada mais quebra.
        cache.add("./assets/logo-workforce.mp4").catch(() => {})
      )
    )
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
