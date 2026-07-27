// Catalogo RASF (sintomas e componentes causadores) para o formulario de
// atendimento de falha (docs/48_ADR_0021_ATENDIMENTO_DE_FALHA_CAMPO.md).
//
// Mesmo padrao de cache offline de catalogoMotivos.js: busca uma vez do
// backend (GET /catalogo-rasf), guarda em cache local, e cai num
// fallback minimo se nunca conseguiu buscar - nunca trava o
// preenchimento do atendimento de falha por falta de rede.

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

const CHAVE_CACHE = "sgo_workforce_catalogo_rasf_cache";

const memoriaFallback = new Map();

function armazenamentoDisponivel() {
  return typeof localStorage !== "undefined";
}

function lerCache() {
  const bruto = armazenamentoDisponivel()
    ? localStorage.getItem(CHAVE_CACHE)
    : memoriaFallback.get(CHAVE_CACHE) ?? null;
  if (!bruto) return null;
  try {
    return JSON.parse(bruto);
  } catch (erro) {
    return null;
  }
}

function gravarCache(catalogo) {
  const bruto = JSON.stringify(catalogo);
  if (armazenamentoDisponivel()) {
    localStorage.setItem(CHAVE_CACHE, bruto);
  } else {
    memoriaFallback.set(CHAVE_CACHE, bruto);
  }
}

// Ultimo recurso: so usado se o app nunca conseguiu buscar o catalogo do
// backend nem tem cache de uma consulta anterior. Poucas opcoes so para
// os campos nao ficarem vazios - deixa claro que nao e a lista real (53
// sintomas, 148 componentes catalogados no RASF).
const CATALOGO_MINIMO_OFFLINE = {
  sintomas: ["(lista RASF não carregada - sincronize quando tiver conexão)"],
  componentes_causadores: ["(lista RASF não carregada - sincronize quando tiver conexão)"],
};

// `opcoes` permite substituir fetch/URL/token/configurada em teste, mesmo
// padrao de catalogoMotivos.js::obterMotivosPausa.
export async function obterCatalogoRasf(opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (configurada) {
    try {
      const resposta = await fetchImpl(`${urlBase}/catalogo-rasf`, {
        headers: { "X-Sync-Token": token },
      });
      if (resposta.ok) {
        const catalogo = await resposta.json();
        gravarCache(catalogo);
        return catalogo;
      }
    } catch (erro) {
      // Sem conexao - cai no cache/fallback abaixo, nunca trava o app.
    }
  }
  const cache = lerCache();
  if (cache) {
    return cache;
  }
  return CATALOGO_MINIMO_OFFLINE;
}

// So para os testes isolarem o cache entre casos - o app real nunca
// chama isso.
export function _limparCacheParaTeste() {
  if (armazenamentoDisponivel()) {
    localStorage.removeItem(CHAVE_CACHE);
  }
  memoriaFallback.delete(CHAVE_CACHE);
}
