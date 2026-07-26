// Testes de interface_campo/js/catalogoMotivos.js
// Roda com: node --test tests/js
//
// _limparCacheParaTeste() garante isolamento entre casos (mesmo motivo de
// RelogioSimulado.voltarParaTempoReal() em relogioSimulado.test.mjs).

import { test } from "node:test";
import assert from "node:assert/strict";

import { obterMotivosPausa, _limparCacheParaTeste } from "../../interface_campo/js/catalogoMotivos.js";

test.beforeEach(() => {
  _limparCacheParaTeste();
});

test("sem configuracao e sem cache anterior, usa a lista minima embutida", async () => {
  const motivos = await obterMotivosPausa({ configurada: false });

  assert.ok(motivos.length > 0);
  assert.ok(motivos.every((m) => m.tipo_registro === "pausa" && m.ativo));
  assert.ok(motivos.some((m) => m.codigo === "EE02"));
});

test("sucesso busca do backend, grava cache e filtra so pausa+ativo", async () => {
  const catalogoDoBackend = [
    { codigo: "EE02", descricao: "Refeição", tipo_registro: "pausa", ativo: true },
    { codigo: "EE12", descricao: "Deslocamento rodoviário", tipo_registro: "evento_secundario", ativo: true },
    { codigo: "EE07", descricao: "Reunião", tipo_registro: "pausa", ativo: false },
  ];
  const fetchOk = async () => ({
    ok: true,
    json: async () => catalogoDoBackend,
  });

  const motivos = await obterMotivosPausa({ configurada: true, fetchImpl: fetchOk });

  assert.equal(motivos.length, 1);
  assert.equal(motivos[0].codigo, "EE02");
});

test("falha de rede usa o cache da ultima consulta bem-sucedida", async () => {
  const catalogoDoBackend = [
    { codigo: "EE99", descricao: "Motivo de teste", tipo_registro: "pausa", ativo: true },
  ];
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });
  await obterMotivosPausa({ configurada: true, fetchImpl: fetchOk });

  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };
  const motivos = await obterMotivosPausa({ configurada: true, fetchImpl: fetchQueFalha });

  assert.equal(motivos.length, 1);
  assert.equal(motivos[0].codigo, "EE99");
});

test("backend respondendo erro HTTP tambem cai no cache anterior", async () => {
  const catalogoDoBackend = [
    { codigo: "EE99", descricao: "Motivo de teste", tipo_registro: "pausa", ativo: true },
  ];
  await obterMotivosPausa({
    configurada: true,
    fetchImpl: async () => ({ ok: true, json: async () => catalogoDoBackend }),
  });

  const fetchComErro = async () => ({ ok: false, status: 401 });
  const motivos = await obterMotivosPausa({ configurada: true, fetchImpl: fetchComErro });

  assert.equal(motivos.length, 1);
  assert.equal(motivos[0].codigo, "EE99");
});

test("nao configurado mas com cache de consulta anterior usa o cache, nao o fallback minimo", async () => {
  const catalogoDoBackend = [
    { codigo: "EE99", descricao: "Motivo de teste", tipo_registro: "pausa", ativo: true },
  ];
  await obterMotivosPausa({
    configurada: true,
    fetchImpl: async () => ({ ok: true, json: async () => catalogoDoBackend }),
  });

  const motivos = await obterMotivosPausa({ configurada: false });

  assert.equal(motivos.length, 1);
  assert.equal(motivos[0].codigo, "EE99");
});

test("envia o token no header X-Sync-Token", async () => {
  let cabecalhoRecebido = null;
  const fetchOk = async (url, opcoesFetch) => {
    cabecalhoRecebido = opcoesFetch.headers["X-Sync-Token"];
    return { ok: true, json: async () => [] };
  };

  await obterMotivosPausa({ configurada: true, fetchImpl: fetchOk, token: "token-de-teste" });

  assert.equal(cabecalhoRecebido, "token-de-teste");
});
