// Testes de interface_campo/js/continuacoesFalha.js
// Roda com: node --test tests/js
//
// Todas as funcoes recebem fetchImpl injetavel e nunca lancam - mesmo
// padrao de sincronizacao.js/fotoFalha.js.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  buscarPendente,
  criarContinuacao,
  marcarConsumida,
} from "../../interface_campo/js/continuacoesFalha.js";

const dadosFalhaDeExemplo = {
  nota: "1",
  ativo: "A",
  sintoma: "S",
  objeto: "O",
  observacao: "Obs",
  gpsLatitude: -22.9, // nao deve viajar no payload (so os 5 campos do D1)
  fotoCaminho: "atendimentos/foo.jpg",
};

test("criarContinuacao nao configurado nao tenta chamar fetch", async () => {
  let chamado = false;
  const resultado = await criarContinuacao(dadosFalhaDeExemplo, "99999", {
    fetchImpl: async () => {
      chamado = true;
      return { ok: true };
    },
    configurada: false,
  });
  assert.equal(chamado, false);
  assert.equal(resultado.ok, false);
});

test("criarContinuacao envia so os campos do D1 (sem gps/foto)", async () => {
  let corpoEnviado = null;
  const fetchOk = async (url, opcoes) => {
    corpoEnviado = JSON.parse(opcoes.body);
    return { ok: true };
  };

  await criarContinuacao(dadosFalhaDeExemplo, "99999", { fetchImpl: fetchOk, configurada: true });

  assert.equal(corpoEnviado.matricula_destino, "99999");
  assert.deepEqual(corpoEnviado.dados, {
    nota: "1",
    ativo: "A",
    sintoma: "S",
    objeto: "O",
    observacao: "Obs",
  });
});

test("criarContinuacao nunca lanca quando o fetch falha", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };
  const resultado = await criarContinuacao(dadosFalhaDeExemplo, "99999", {
    fetchImpl: fetchQueFalha,
    configurada: true,
  });
  assert.equal(resultado.ok, false);
});

test("buscarPendente sem matricula devolve null sem chamar fetch", async () => {
  let chamado = false;
  const resultado = await buscarPendente("", {
    fetchImpl: async () => {
      chamado = true;
      return { ok: true, json: async () => [] };
    },
    configurada: true,
  });
  assert.equal(chamado, false);
  assert.equal(resultado, null);
});

test("buscarPendente devolve a primeira pendencia da lista", async () => {
  const fetchOk = async () => ({
    ok: true,
    json: async () => [{ id: "abc", dados: { nota: "1" } }],
  });
  const resultado = await buscarPendente("99999", { fetchImpl: fetchOk, configurada: true });
  assert.deepEqual(resultado, { id: "abc", dados: { nota: "1" } });
});

test("buscarPendente devolve null quando a lista vem vazia", async () => {
  const fetchOk = async () => ({ ok: true, json: async () => [] });
  const resultado = await buscarPendente("99999", { fetchImpl: fetchOk, configurada: true });
  assert.equal(resultado, null);
});

test("buscarPendente nunca lanca quando o fetch falha", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };
  const resultado = await buscarPendente("99999", { fetchImpl: fetchQueFalha, configurada: true });
  assert.equal(resultado, null);
});

test("marcarConsumida chama o endpoint de consumo com o id certo", async () => {
  let urlChamada = null;
  const fetchOk = async (url) => {
    urlChamada = url;
    return { ok: true };
  };
  const resultado = await marcarConsumida("abc", { fetchImpl: fetchOk, configurada: true });
  assert.equal(resultado.ok, true);
  assert.match(urlChamada, /\/continuacoes-falha\/abc\/consumir$/);
});
