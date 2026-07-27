// Testes de interface_campo/js/geolocalizacao.js
// Roda com: node --test tests/js
//
// `geolocationImpl` injetavel substitui navigator.geolocation (nao existe
// em Node) - mesmo padrao de fetchImpl usado nos outros modulos.

import { test } from "node:test";
import assert from "node:assert/strict";

import { capturarPosicaoAtual } from "../../interface_campo/js/geolocalizacao.js";

test("sem geolocationImpl disponivel, resolve para null (nunca lanca)", async () => {
  const resultado = await capturarPosicaoAtual({ geolocationImpl: undefined });
  assert.equal(resultado, null);
});

test("sucesso devolve latitude/longitude/precisao/capturadoEm", async () => {
  const geolocationFalso = {
    getCurrentPosition: (sucesso) => {
      sucesso({
        coords: { latitude: -22.9, longitude: -43.2, accuracy: 15.5 },
        timestamp: 1700000000000,
      });
    },
  };

  const resultado = await capturarPosicaoAtual({ geolocationImpl: geolocationFalso });

  assert.equal(resultado.latitude, -22.9);
  assert.equal(resultado.longitude, -43.2);
  assert.equal(resultado.precisaoMetros, 15.5);
  assert.equal(resultado.capturadoEm.getTime(), 1700000000000);
});

test("erro/permissao negada resolve para null, nunca rejeita", async () => {
  const geolocationFalso = {
    getCurrentPosition: (_sucesso, erro) => {
      erro(new Error("Permissao negada"));
    },
  };

  const resultado = await capturarPosicaoAtual({ geolocationImpl: geolocationFalso });
  assert.equal(resultado, null);
});
