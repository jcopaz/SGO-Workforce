// Testes do relogio simulado (docs/43_ADR_0016_SIMULADOR_DE_TEMPO_PARA_TESTES.md).
// Roda com: node --test tests/js
//
// Sem localStorage disponivel em Node, o modulo cai para o fallback em
// memoria - o que estes testes exercitam diretamente.

import { test } from "node:test";
import assert from "node:assert/strict";

import * as RelogioSimulado from "../../interface_campo/js/relogioSimulado.js";

const TOLERANCIA_MS = 200; // folga para o tempo de execucao do teste em si

test.beforeEach(() => {
  RelogioSimulado.voltarParaTempoReal();
});

test("sem uso, agora() acompanha o tempo real", () => {
  const diferenca = Math.abs(RelogioSimulado.agora().getTime() - Date.now());
  assert.ok(diferenca < TOLERANCIA_MS, `diferenca ${diferenca}ms deveria ser pequena`);
  assert.equal(RelogioSimulado.estaSimulando(), false);
  assert.equal(RelogioSimulado.descreverDeslocamento(), "tempo real");
});

test("avancar(ms) desloca agora() para frente", () => {
  RelogioSimulado.avancar(RelogioSimulado.UMA_HORA_MS);
  const esperado = Date.now() + RelogioSimulado.UMA_HORA_MS;
  const diferenca = Math.abs(RelogioSimulado.agora().getTime() - esperado);
  assert.ok(diferenca < TOLERANCIA_MS, `diferenca ${diferenca}ms deveria ser pequena`);
  assert.equal(RelogioSimulado.estaSimulando(), true);
});

test("avancar() acumula em chamadas sucessivas", () => {
  RelogioSimulado.avancar(RelogioSimulado.UM_DIA_MS);
  RelogioSimulado.avancar(RelogioSimulado.UMA_HORA_MS * 3);
  const esperado = Date.now() + RelogioSimulado.UM_DIA_MS + RelogioSimulado.UMA_HORA_MS * 3;
  const diferenca = Math.abs(RelogioSimulado.agora().getTime() - esperado);
  assert.ok(diferenca < TOLERANCIA_MS, `diferenca ${diferenca}ms deveria ser pequena`);
});

test("definir(data) faz agora() coincidir com a data alvo", () => {
  const alvo = new Date(2026, 6, 30, 8, 0, 0, 0);
  RelogioSimulado.definir(alvo);
  const diferenca = Math.abs(RelogioSimulado.agora().getTime() - alvo.getTime());
  assert.ok(diferenca < TOLERANCIA_MS, `diferenca ${diferenca}ms deveria ser pequena`);
  assert.equal(RelogioSimulado.estaSimulando(), true);
});

test("voltarParaTempoReal() zera o deslocamento", () => {
  RelogioSimulado.avancar(RelogioSimulado.UM_DIA_MS * 5);
  assert.equal(RelogioSimulado.estaSimulando(), true);

  RelogioSimulado.voltarParaTempoReal();

  assert.equal(RelogioSimulado.estaSimulando(), false);
  const diferenca = Math.abs(RelogioSimulado.agora().getTime() - Date.now());
  assert.ok(diferenca < TOLERANCIA_MS, `diferenca ${diferenca}ms deveria ser pequena`);
});

test("descreverDeslocamento() formata dias, horas e minutos", () => {
  RelogioSimulado.avancar(RelogioSimulado.UM_DIA_MS + RelogioSimulado.UMA_HORA_MS * 3 + RelogioSimulado.UM_MINUTO_MS * 20);
  assert.equal(RelogioSimulado.descreverDeslocamento(), "+1d 3h 20min");
});

test("descreverDeslocamento() omite unidades zeradas", () => {
  RelogioSimulado.avancar(RelogioSimulado.UMA_HORA_MS * 2);
  assert.equal(RelogioSimulado.descreverDeslocamento(), "+2h");
});
