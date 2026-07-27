// Catalogo dinamico de motivos de pausa (docs/46_ADR_0019_CATALOGO_DINAMICO.md).
//
// Antes deste incremento, os motivos de pausa ficavam hardcoded em
// app.js. Agora o app busca o catalogo do backend (GET /catalogo,
// workforce_api) e guarda uma copia em cache local para continuar
// funcionando offline - mesmo principio de offline-first do resto do
// app (ADR-0004): uma falha de rede aqui nunca pode impedir o
// colaborador de registrar uma pausa.

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

const CHAVE_CACHE = "sgo_workforce_catalogo_motivos_cache";

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

function gravarCache(lista) {
  const bruto = JSON.stringify(lista);
  if (armazenamentoDisponivel()) {
    localStorage.setItem(CHAVE_CACHE, bruto);
  } else {
    memoriaFallback.set(CHAVE_CACHE, bruto);
  }
}

// Ultimo recurso: so usado se o app nunca conseguiu buscar o catalogo do
// backend nem tem cache de uma consulta anterior (ex.: primeiro uso, ja
// offline). Sao os mesmos 5 motivos que ja estavam fixos no codigo antes
// deste incremento - garante que o seletor de pausa nunca fica vazio.
// Renumerado em 2026-07-27 (ADR-0023): antigo EE21 "SMS" -> EE20 "DDS / APR",
// antigo EE23 "Treinamento" -> EE22 (mesmo nome).
const CATALOGO_MINIMO_OFFLINE = [
  { codigo: "EE02", descricao: "Refeição 1 hora", tipo_registro: "pausa", ativo: true },
  { codigo: "EE07", descricao: "Reunião ou ADM", tipo_registro: "pausa", ativo: true },
  { codigo: "EE11", descricao: "Consulta à documentação técnica", tipo_registro: "pausa", ativo: true },
  { codigo: "EE20", descricao: "DDS / APR", tipo_registro: "pausa", ativo: true },
  { codigo: "EE22", descricao: "Treinamento", tipo_registro: "pausa", ativo: true },
];

function filtrarMotivosPausa(lista) {
  return lista.filter((motivo) => motivo.tipo_registro === "pausa" && motivo.ativo);
}

// Busca o catalogo completo do backend, com fallback em cascata:
// 1. GET /catalogo bem-sucedido -> grava cache, retorna motivos de pausa.
// 2. Falha de rede ou sincronizacao nao configurada -> usa o cache da
//    ultima consulta bem-sucedida, se existir.
// 3. Nunca teve cache (primeiro uso ja offline) -> lista minima embutida.
// `opcoes` permite substituir fetch/URL/token/configurada em teste, sem
// tocar nos valores reais de configSincronizacao.js - mesmo padrao de
// sincronizacao.js::sincronizar(). Por padrao usa exatamente o que o app
// real usa.
export async function obterMotivosPausa(opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (configurada) {
    try {
      const resposta = await fetchImpl(`${urlBase}/catalogo`, {
        headers: { "X-Sync-Token": token },
      });
      if (resposta.ok) {
        const lista = await resposta.json();
        gravarCache(lista);
        return filtrarMotivosPausa(lista);
      }
    } catch (erro) {
      // Sem conexao - cai no cache/fallback abaixo, nunca trava o app.
    }
  }
  const cache = lerCache();
  if (cache) {
    return filtrarMotivosPausa(cache);
  }
  return CATALOGO_MINIMO_OFFLINE;
}

// So para os testes isolarem o cache entre casos - o app real nunca
// chama isso (nao existe um botao "esquecer catalogo salvo" na interface).
export function _limparCacheParaTeste() {
  if (armazenamentoDisponivel()) {
    localStorage.removeItem(CHAVE_CACHE);
  }
  memoriaFallback.delete(CHAVE_CACHE);
}
