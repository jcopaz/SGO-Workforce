// Testes de paridade do motor JS com o motor Python (Incremento 1/4).
// Roda com: node --test tests/js
//
// Mesmos casos de tests/test_motor_jornada.py, para garantir que a
// interface de campo (que precisa funcionar offline, sem o backend
// Python) aplica exatamente as mesmas regras.

import { test } from "node:test";
import assert from "node:assert/strict";

import { MotorJornada } from "../../interface_campo/js/motorJornada.js";
import * as calculo from "../../interface_campo/js/calculo.js";
import * as Erros from "../../interface_campo/js/erros.js";

function dt(hora, minuto, dia = 1) {
  return new Date(2026, 0, dia, hora, minuto, 0, 0);
}

test("9.1 fluxo nominal - caso minimo obrigatorio", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(10, 0), "PAUSA_TESTE");
  motor.finalizarPausa(dt(10, 20));
  motor.encerrarAtividade(dt(12, 0));
  motor.encerrarJornada(dt(12, 10));

  const resumo = calculo.resumoJornada(motor.jornada);

  assert.equal(calculo.duracaoJornadaBruta(motor.jornada), (4 * 60 + 10) * 60000);
  assert.equal(resumo.atividades[0].bruta, (3 * 60 + 50) * 60000);
  assert.equal(resumo.atividades[0].pausas, 20 * 60000);
  assert.equal(resumo.atividades[0].liquida, (3 * 60 + 30) * 60000);
  assert.equal(resumo.tempoClassificado, (3 * 60 + 50) * 60000);
  assert.equal(resumo.tempoNaoClassificado, 20 * 60000);
});

test("9.2 jornada sem atividade", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.encerrarJornada(dt(9, 0));

  assert.equal(calculo.tempoClassificadoJornada(motor.jornada), 0);
  assert.equal(calculo.tempoNaoClassificado(motor.jornada), 60 * 60000);
});

test("9.3 atividade sem pausa: liquida == bruta", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.encerrarAtividade(dt(9, 10));
  motor.encerrarJornada(dt(9, 20));

  const atividade = motor.jornada.atividades[0];
  assert.equal(
    calculo.duracaoAtividadeLiquida(atividade),
    calculo.duracaoAtividadeBruta(atividade)
  );
});

test("9.4 atividade com uma pausa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 0));
  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");
  motor.finalizarPausa(dt(9, 15));
  motor.encerrarAtividade(dt(10, 0));
  motor.encerrarJornada(dt(10, 0));

  const atividade = motor.jornada.atividades[0];
  assert.equal(calculo.duracaoAtividadeBruta(atividade), 2 * 60 * 60000);
  assert.equal(calculo.duracaoPausasAtividade(atividade), 15 * 60000);
  assert.equal(calculo.duracaoAtividadeLiquida(atividade), (60 + 45) * 60000);
});

test("9.5 atividade com varias pausas sequenciais", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 0));

  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");
  motor.finalizarPausa(dt(9, 10));

  motor.iniciarPausa(dt(10, 0), "PAUSA_TESTE");
  motor.finalizarPausa(dt(10, 5));

  motor.encerrarAtividade(dt(11, 0));
  motor.encerrarJornada(dt(11, 0));

  const atividade = motor.jornada.atividades[0];
  assert.equal(calculo.duracaoPausasAtividade(atividade), 15 * 60000);
  assert.equal(calculo.duracaoAtividadeLiquida(atividade), (2 * 60 + 45) * 60000);
});

test("9.6 bloqueia segunda atividade", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  assert.throws(() => motor.iniciarAtividade(dt(8, 20)), Erros.AtividadeJaAtivaError);
});

test("9.7 bloqueia segunda pausa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");

  assert.throws(() => motor.iniciarPausa(dt(9, 5), "PAUSA_TESTE"), Erros.PausaJaAtivaError);
});

test("9.8 bloqueia encerrar atividade com pausa aberta", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");

  assert.throws(
    () => motor.encerrarAtividade(dt(9, 30)),
    Erros.AtividadeEncerramentoComPausaAbertaError
  );
});

test("9.9 bloqueia encerrar jornada com pausa aberta", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");

  assert.throws(() => motor.encerrarJornada(dt(9, 30)), Erros.JornadaComPausaAbertaError);
});

test("9.9b bloqueia encerrar jornada com atividade aberta", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  assert.throws(() => motor.encerrarJornada(dt(9, 30)), Erros.JornadaComAtividadeAbertaError);
});

test("9.10 bloqueia timestamp invalido (atividade, pausa, jornada)", () => {
  const motorA = new MotorJornada({ colaboradorMatricula: "12345" });
  motorA.iniciarJornada(dt(8, 0));
  motorA.iniciarAtividade(dt(8, 10));
  assert.throws(() => motorA.encerrarAtividade(dt(8, 0)), Erros.TimestampInvalidoError);

  const motorP = new MotorJornada({ colaboradorMatricula: "12345" });
  motorP.iniciarJornada(dt(8, 0));
  motorP.iniciarAtividade(dt(8, 10));
  motorP.iniciarPausa(dt(9, 0), "PAUSA_TESTE");
  assert.throws(() => motorP.finalizarPausa(dt(8, 50)), Erros.TimestampInvalidoError);

  const motorJ = new MotorJornada({ colaboradorMatricula: "12345" });
  motorJ.iniciarJornada(dt(8, 0));
  assert.throws(() => motorJ.encerrarJornada(dt(7, 0)), Erros.TimestampInvalidoError);
});

test("9.11 bloqueia pausa iniciada antes da atividade", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  assert.throws(() => motor.iniciarPausa(dt(8, 0), "PAUSA_TESTE"), Erros.TimestampInvalidoError);
});

test("9.11 bloqueia pausa encerrada depois da atividade (validado no calculo)", () => {
  const atividade = { id: "a1", inicio: dt(8, 0), fim: dt(9, 0), estado: "ENCERRADA", pausas: [] };
  const pausa = {
    id: "p1",
    atividadeId: "a1",
    motivo: "PAUSA_TESTE",
    inicio: dt(8, 30),
    fim: dt(9, 30),
    estado: "ENCERRADA",
  };
  atividade.pausas.push(pausa);

  assert.throws(() => calculo.duracaoPausasAtividade(atividade), Erros.PausaForaDoIntervaloError);
});

test("9.12 evento atravessando meia-noite", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(22, 0, 1));
  motor.iniciarAtividade(dt(22, 30, 1));
  motor.iniciarPausa(dt(23, 30, 1), "PAUSA_TESTE");
  motor.finalizarPausa(dt(0, 0, 2));
  motor.encerrarAtividade(dt(2, 0, 2));
  motor.encerrarJornada(dt(2, 30, 2));

  const resumo = calculo.resumoJornada(motor.jornada);

  assert.equal(calculo.duracaoJornadaBruta(motor.jornada), (4 * 60 + 30) * 60000);
  assert.equal(resumo.atividades[0].bruta, (3 * 60 + 30) * 60000);
  assert.equal(resumo.atividades[0].pausas, 30 * 60000);
  assert.equal(resumo.atividades[0].liquida, 3 * 60 * 60000);
});

test("9.13 duplicidade de comando nao corrompe estado", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));

  assert.throws(() => motor.iniciarJornada(dt(8, 5)), Erros.JornadaJaAbertaError);
  assert.equal(motor.jornada.inicio.getTime(), dt(8, 0).getTime());

  motor.encerrarJornada(dt(9, 0));
  assert.throws(() => motor.encerrarJornada(dt(10, 0)), Erros.JornadaNaoAbertaError);
  assert.equal(motor.jornada.fim.getTime(), dt(9, 0).getTime());
});

test("regras estruturais: jornada/atividade/motivo obrigatorios", () => {
  const motorSemJornada = new MotorJornada({ colaboradorMatricula: "12345" });
  assert.throws(() => motorSemJornada.iniciarAtividade(dt(8, 0)), Erros.JornadaNaoAbertaError);

  const motorSemAtividade = new MotorJornada({ colaboradorMatricula: "12345" });
  motorSemAtividade.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motorSemAtividade.iniciarPausa(dt(8, 30), "PAUSA_TESTE"),
    Erros.PausaExigeAtividadeAtivaError
  );

  const motorSemMotivo = new MotorJornada({ colaboradorMatricula: "12345" });
  motorSemMotivo.iniciarJornada(dt(8, 0));
  motorSemMotivo.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motorSemMotivo.iniciarPausa(dt(9, 0), ""),
    Erros.PausaMotivoObrigatorioError
  );
});

test("recuperacao de estado: MotorJornada.aPartirDe reconstroi ativos corretamente", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(9, 0), "PAUSA_TESTE");

  const recuperado = MotorJornada.aPartirDe(motor.jornada);
  recuperado.finalizarPausa(dt(9, 20));
  recuperado.encerrarAtividade(dt(10, 0));
  recuperado.encerrarJornada(dt(10, 0));

  const atividade = recuperado.jornada.atividades[0];
  assert.equal(calculo.duracaoPausasAtividade(atividade), 20 * 60000);
});
