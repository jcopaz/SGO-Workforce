// Testes de interface_campo/js/integracaoSgo.js
// Roda com: node --test tests/js
//
// validarLoginSgo() recebe um fetchImpl injetavel, entao os testes nunca
// fazem uma chamada de rede de verdade (mesmo padrao de sincronizacao.js).
// linkApontamentoSgo() e' pura, sem rede.

import { test } from "node:test";
import assert from "node:assert/strict";

import { CHAVE_API_SGO, URL_API_SGO, URL_APP_SGO } from "../../interface_campo/js/configSgo.js";
import { validarLoginSgo, linkApontamentoSgo } from "../../interface_campo/js/integracaoSgo.js";

test("validarLoginSgo com configurada:false nao tenta chamar fetch", async () => {
  let chamado = false;
  const fetchFalso = async () => {
    chamado = true;
    return { ok: true };
  };

  const resultado = await validarLoginSgo("12345", "senha", {
    fetchImpl: fetchFalso,
    configurada: false,
  });

  assert.equal(chamado, false);
  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /nao configurada/i);
});

test("validarLoginSgo nunca lanca quando o fetch falha (offline)", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };

  const resultado = await validarLoginSgo("12345", "senha", {
    fetchImpl: fetchQueFalha,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /offline/i);
});

test("validarLoginSgo com HTTP 401 reporta usuario/senha incorretos", async () => {
  const fetchNaoAutorizado = async () => ({ status: 401, ok: false });

  const resultado = await validarLoginSgo("12345", "senha-errada", {
    fetchImpl: fetchNaoAutorizado,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /incorretas/i);
});

test("validarLoginSgo com HTTP 403 repassa o detail do backend (ex.: senha pendente de troca)", async () => {
  const fetchBloqueado = async () => ({
    status: 403,
    ok: false,
    json: async () => ({ detail: "Senha pendente de troca. Acesse o SGO para definir uma nova senha." }),
  });

  const resultado = await validarLoginSgo("12345", "senha", {
    fetchImpl: fetchBloqueado,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.equal(resultado.mensagem, "Senha pendente de troca. Acesse o SGO para definir uma nova senha.");
});

test("validarLoginSgo com HTTP 403 sem corpo JSON usa mensagem generica", async () => {
  const fetchBloqueadoSemCorpo = async () => ({
    status: 403,
    ok: false,
    json: async () => {
      throw new SyntaxError("corpo vazio");
    },
  });

  const resultado = await validarLoginSgo("12345", "senha", {
    fetchImpl: fetchBloqueadoSemCorpo,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /negado/i);
});

test("validarLoginSgo reporta HTTP de erro generico com o status", async () => {
  const fetchErro500 = async () => ({ status: 500, ok: false });

  const resultado = await validarLoginSgo("12345", "senha", {
    fetchImpl: fetchErro500,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /500/);
});

test("validarLoginSgo com sucesso envia username/senha no corpo e a chave no header", async () => {
  let urlChamada = null;
  let corpoEnviado = null;
  let cabecalhoChave = null;
  const fetchOk = async (url, opcoesFetch) => {
    urlChamada = url;
    corpoEnviado = opcoesFetch.body;
    cabecalhoChave = opcoesFetch.headers["x-api-key"];
    return {
      ok: true,
      status: 200,
      json: async () => ({
        username: "12345",
        nome: "Colaborador Teste",
        perfil: "Técnico",
        escopo: "Paranapiacaba",
        governanca: ["Mapa de Campo"],
        sid: "token-assinado-de-teste",
      }),
    };
  };

  const resultado = await validarLoginSgo("12345", "minhasenha", {
    fetchImpl: fetchOk,
    configurada: true,
  });

  assert.equal(resultado.ok, true);
  assert.equal(resultado.username, "12345");
  assert.equal(resultado.nome, "Colaborador Teste");
  assert.equal(resultado.perfil, "Técnico");
  assert.equal(resultado.sid, "token-assinado-de-teste");
  assert.ok(resultado.obtidoEm instanceof Date);

  assert.equal(urlChamada, `${URL_API_SGO}/auth/validar`);
  assert.equal(cabecalhoChave, CHAVE_API_SGO);
  assert.equal(corpoEnviado.get("username"), "12345");
  assert.equal(corpoEnviado.get("senha"), "minhasenha");
});

test("linkApontamentoSgo sem sessao (null) devolve null", () => {
  assert.equal(linkApontamentoSgo(null), null);
});

test("linkApontamentoSgo com sessao sem sid devolve null", () => {
  assert.equal(linkApontamentoSgo({ ok: true, sid: null }), null);
});

test("linkApontamentoSgo com sid monta a URL do app do SGO", () => {
  const link = linkApontamentoSgo({ ok: true, sid: "abc123" });
  assert.equal(link, `${URL_APP_SGO}/?sid=abc123`);
});
