// Testes de interface_campo/js/fotoFalha.js
// Roda com: node --test tests/js
//
// enviarFoto() recebe fetchImpl injetavel, mesmo padrao de
// sincronizacao.js - nenhum teste faz chamada de rede real.

import { test } from "node:test";
import assert from "node:assert/strict";

import { enviarFoto } from "../../interface_campo/js/fotoFalha.js";

const arquivoFalso = { name: "foto.jpg" };

test("nao configurado nao tenta chamar fetch", async () => {
  let chamado = false;
  const fetchFalso = async () => {
    chamado = true;
    return { ok: true, json: async () => ({ caminho: "x" }) };
  };

  const resultado = await enviarFoto(arquivoFalso, { fetchImpl: fetchFalso, configurada: false });

  assert.equal(chamado, false);
  assert.equal(resultado.ok, false);
});

test("sucesso devolve o caminho retornado pelo backend", async () => {
  const fetchOk = async () => ({ ok: true, json: async () => ({ caminho: "abc-foto.jpg" }) });

  const resultado = await enviarFoto(arquivoFalso, { fetchImpl: fetchOk, configurada: true });

  assert.equal(resultado.ok, true);
  assert.equal(resultado.caminho, "abc-foto.jpg");
});

test("falha de rede nunca lanca (best-effort)", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };

  const resultado = await enviarFoto(arquivoFalso, { fetchImpl: fetchQueFalha, configurada: true });

  assert.equal(resultado.ok, false);
});

test("erro HTTP reporta o status na mensagem", async () => {
  const fetchComErro = async () => ({ ok: false, status: 500 });

  const resultado = await enviarFoto(arquivoFalso, { fetchImpl: fetchComErro, configurada: true });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /500/);
});

test("envia o token no header X-Sync-Token", async () => {
  let cabecalhoRecebido = null;
  const fetchOk = async (url, opcoesFetch) => {
    cabecalhoRecebido = opcoesFetch.headers["X-Sync-Token"];
    return { ok: true, json: async () => ({ caminho: "x" }) };
  };

  await enviarFoto(arquivoFalso, { fetchImpl: fetchOk, configurada: true, token: "token-de-teste" });

  assert.equal(cabecalhoRecebido, "token-de-teste");
});
