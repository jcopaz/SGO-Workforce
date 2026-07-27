// Testes de interface_campo/js/catalogoRasf.js
// Roda com: node --test tests/js
//
// Mesmo padrao de tests/js/catalogoMotivos.test.mjs.

import { test } from "node:test";
import assert from "node:assert/strict";

import { obterCatalogoRasf, _limparCacheParaTeste } from "../../interface_campo/js/catalogoRasf.js";

test.beforeEach(() => {
  _limparCacheParaTeste();
});

test("sem configuracao e sem cache anterior, usa a lista minima embutida", async () => {
  const catalogo = await obterCatalogoRasf({ configurada: false });

  assert.ok(catalogo.sintomas.length > 0);
  assert.ok(catalogo.componentes_causadores.length > 0);
});

test("sucesso busca do backend e grava cache", async () => {
  const catalogoDoBackend = {
    sintomas: ["FALHA X", "FALHA Y"],
    componentes_causadores: ["FUSÍVEL", "RELÉ"],
  };
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });

  const catalogo = await obterCatalogoRasf({ configurada: true, fetchImpl: fetchOk });

  assert.deepEqual(catalogo, catalogoDoBackend);
});

test("falha de rede usa o cache da ultima consulta bem-sucedida", async () => {
  const catalogoDoBackend = {
    sintomas: ["FALHA X"],
    componentes_causadores: ["FUSÍVEL"],
  };
  await obterCatalogoRasf({
    configurada: true,
    fetchImpl: async () => ({ ok: true, json: async () => catalogoDoBackend }),
  });

  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };
  const catalogo = await obterCatalogoRasf({ configurada: true, fetchImpl: fetchQueFalha });

  assert.deepEqual(catalogo, catalogoDoBackend);
});

test("nao configurado mas com cache de consulta anterior usa o cache", async () => {
  const catalogoDoBackend = {
    sintomas: ["FALHA X"],
    componentes_causadores: ["FUSÍVEL"],
  };
  await obterCatalogoRasf({
    configurada: true,
    fetchImpl: async () => ({ ok: true, json: async () => catalogoDoBackend }),
  });

  const catalogo = await obterCatalogoRasf({ configurada: false });

  assert.deepEqual(catalogo, catalogoDoBackend);
});

test("envia o token no header X-Sync-Token", async () => {
  let cabecalhoRecebido = null;
  const fetchOk = async (url, opcoesFetch) => {
    cabecalhoRecebido = opcoesFetch.headers["X-Sync-Token"];
    return { ok: true, json: async () => ({ sintomas: [], componentes_causadores: [] }) };
  };

  await obterCatalogoRasf({ configurada: true, fetchImpl: fetchOk, token: "token-de-teste" });

  assert.equal(cabecalhoRecebido, "token-de-teste");
});
