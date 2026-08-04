// Testes de interface_campo/js/geolocalizacao.js
// Roda com: node --test tests/js
//
// `geolocationImpl` injetavel substitui navigator.geolocation (nao existe
// em Node) - mesmo padrao de fetchImpl usado nos outros modulos.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  capturarPosicaoAtual,
  iniciarCapturaPeriodica,
  pararCapturaPeriodica,
} from "../../interface_campo/js/geolocalizacao.js";

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

test("sucesso inclui velocidade/direcao quando o navegador fornece (Fase 2, ADR-0045)", async () => {
  const geolocationFalso = {
    getCurrentPosition: (sucesso) => {
      sucesso({
        coords: { latitude: -22.9, longitude: -43.2, accuracy: 15.5, speed: 3.2, heading: 90 },
        timestamp: 1700000000000,
      });
    },
  };

  const resultado = await capturarPosicaoAtual({ geolocationImpl: geolocationFalso });

  assert.equal(resultado.velocidadeMetrosSegundo, 3.2);
  assert.equal(resultado.direcaoGraus, 90);
});

test("sucesso sem velocidade/direcao do navegador vira null, nunca undefined", async () => {
  const geolocationFalso = {
    getCurrentPosition: (sucesso) => {
      sucesso({
        coords: { latitude: -22.9, longitude: -43.2, accuracy: 15.5 },
        timestamp: 1700000000000,
      });
    },
  };

  const resultado = await capturarPosicaoAtual({ geolocationImpl: geolocationFalso });

  assert.equal(resultado.velocidadeMetrosSegundo, null);
  assert.equal(resultado.direcaoGraus, null);
});

test("iniciarCapturaPeriodica chama aoCapturar a cada intervalo, so quando a captura da certo", async () => {
  let chamadas = 0;
  const geolocationFalso = {
    getCurrentPosition: (sucesso) => {
      sucesso({
        coords: { latitude: -22.9, longitude: -43.2, accuracy: 15.5 },
        timestamp: 1700000000000,
      });
    },
  };

  const idIntervalo = iniciarCapturaPeriodica(
    () => {
      chamadas += 1;
    },
    { intervaloMs: 20, geolocationImpl: geolocationFalso }
  );

  await new Promise((resolve) => setTimeout(resolve, 70));
  pararCapturaPeriodica(idIntervalo);

  assert.ok(chamadas >= 2, `esperava pelo menos 2 chamadas, teve ${chamadas}`);
});

test("iniciarCapturaPeriodica nunca chama aoCapturar quando a captura falha (best-effort)", async () => {
  let chamadas = 0;
  const geolocationQueFalha = {
    getCurrentPosition: (_sucesso, erro) => erro(new Error("sem sinal")),
  };

  const idIntervalo = iniciarCapturaPeriodica(
    () => {
      chamadas += 1;
    },
    { intervaloMs: 15, geolocationImpl: geolocationQueFalha }
  );

  await new Promise((resolve) => setTimeout(resolve, 40));
  pararCapturaPeriodica(idIntervalo);

  assert.equal(chamadas, 0);
});

test("pararCapturaPeriodica interrompe novas chamadas", async () => {
  let chamadas = 0;
  const geolocationFalso = {
    getCurrentPosition: (sucesso) => {
      sucesso({
        coords: { latitude: 0, longitude: 0, accuracy: 1 },
        timestamp: 1700000000000,
      });
    },
  };

  const idIntervalo = iniciarCapturaPeriodica(
    () => {
      chamadas += 1;
    },
    { intervaloMs: 15, geolocationImpl: geolocationFalso }
  );

  await new Promise((resolve) => setTimeout(resolve, 20));
  pararCapturaPeriodica(idIntervalo);
  const chamadasAoParar = chamadas;

  await new Promise((resolve) => setTimeout(resolve, 40));
  assert.equal(chamadas, chamadasAoParar);
});
