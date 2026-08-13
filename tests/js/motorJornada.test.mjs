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
import { ResultadoAtividade, TipoEventoSecundario } from "../../interface_campo/js/enums.js";
import { gerarJornadaEspelho } from "../../interface_campo/js/entidades.js";

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

// Bug real de producao (2026-07-31): uma jornada gravada no IndexedDB
// antes de eventosSecundarios (ADR-0024)/ordensServico (ADR-0025)
// existirem no formato nao tem esses campos - aPartirDe quebrava com
// "Cannot read properties of undefined (reading 'filter')" ao reabrir o
// app. jornada_de_dict (lado Python) ja tinha essa retrocompatibilidade
// desde sempre (`.get(..., [])`); o lado JS nao tinha o equivalente.
test("recuperacao de estado: aPartirDe tolera jornada antiga sem eventosSecundarios/ordensServico", () => {
  const jornadaAntiga = {
    id: "jornada-formato-antigo",
    colaboradorMatricula: "12345",
    inicio: dt(8, 0),
    fim: null,
    estado: "ABERTA",
    atividades: [
      {
        id: "atividade-1",
        inicio: dt(8, 10),
        fim: null,
        estado: "ATIVA",
        pausas: [],
        // ordensServico ausente de proposito (formato anterior ao ADR-0025).
      },
    ],
    // eventosSecundarios ausente de proposito (formato anterior ao ADR-0024).
  };

  const recuperado = MotorJornada.aPartirDe(jornadaAntiga);

  assert.equal(recuperado._atividadeAtiva.id, "atividade-1");
  assert.deepEqual(recuperado.jornada.eventosSecundarios, []);
  assert.deepEqual(recuperado.jornada.atividades[0].ordensServico, []);
  // equipe ausente de proposito (formato anterior a aba Equipe, 2026-08-07)
  // - mesmo bug de producao do comentario acima, prevenido aqui desde o
  // inicio (normalizarCamposRetrocompativeis ja cobre equipe).
  assert.deepEqual(recuperado.jornada.atividades[0].equipe, []);
  // A jornada recuperada continua utilizavel normalmente depois do reparo.
  recuperado.encerrarAtividade(dt(10, 0));
  recuperado.encerrarJornada(dt(10, 0));
});

// ----------------------------------------------------------------------
// Atendimento de falha (ADR-0021, espelha tests/test_atendimento_falha.py)
// ----------------------------------------------------------------------
function motorComAtendimentoAtivo() {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtendimentoFalha(dt(8, 10));
  return motor;
}

test("atendimento de falha completo encerra normalmente", () => {
  const motor = motorComAtendimentoAtivo();
  motor.registrarDadosFalha({
    nota: "12345",
    ativo: "AT-001",
    sintoma: "33 - CIRCUITO DE VIA COM OCUP. INDEVIDA",
    objeto: "FUSÍVEL",
    observacao: "Testado apos a troca, normalizado.",
  });

  const atividade = motor.encerrarAtividade(dt(9, 0));
  motor.encerrarJornada(dt(9, 0));

  assert.equal(atividade.estado, "ENCERRADA");
  assert.equal(atividade.dadosFalha.nota, "12345");
  assert.equal(atividade.dadosFalha.objeto, "FUSÍVEL");
});

test("bloqueia encerramento de atendimento de falha sem nenhum campo", () => {
  const motor = motorComAtendimentoAtivo();
  assert.throws(() => motor.encerrarAtividade(dt(9, 0)), (erro) => {
    assert.ok(erro instanceof Erros.AtendimentoFalhaCamposObrigatoriosError);
    for (const campo of ["nota", "ativo", "sintoma", "objeto", "observacao"]) {
      assert.ok(erro.message.includes(campo), `mensagem deveria citar ${campo}`);
    }
    return true;
  });
});

test("bloqueia encerramento de atendimento de falha com campos parciais", () => {
  const motor = motorComAtendimentoAtivo();
  motor.registrarDadosFalha({ nota: "12345", ativo: "AT-001", sintoma: "Falha X" });

  assert.throws(() => motor.encerrarAtividade(dt(9, 0)), (erro) => {
    assert.ok(erro.message.includes("objeto"));
    assert.ok(erro.message.includes("observacao"));
    assert.ok(!erro.message.includes("nota"));
    return true;
  });
});

test("registro progressivo de campos do atendimento de falha", () => {
  const motor = motorComAtendimentoAtivo();
  motor.registrarDadosFalha({ nota: "1", ativo: "A", sintoma: "S", objeto: "O" });
  motor.registrarDadosFalha({ observacao: "Obs" });

  const dados = motor.jornada.atividades[0].dadosFalha;
  assert.deepEqual(
    [dados.nota, dados.ativo, dados.sintoma, dados.objeto, dados.observacao],
    ["1", "A", "S", "O", "Obs"]
  );

  // Um segundo registro so sobrescreve o que for explicitamente informado.
  motor.registrarDadosFalha({ nota: "1-revisado" });
  assert.equal(motor.jornada.atividades[0].dadosFalha.ativo, "A");
  assert.equal(motor.jornada.atividades[0].dadosFalha.nota, "1-revisado");
});

test("registrarDadosFalha sem atendimento ativo lanca erro dedicado", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.registrarDadosFalha({ nota: "1" }),
    Erros.AtendimentoFalhaNaoAtivoError
  );
});

test("registrarDadosFalha em atividade comum nao e permitido", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10)); // atividade comum, sem dadosFalha
  assert.throws(
    () => motor.registrarDadosFalha({ nota: "1" }),
    Erros.AtendimentoFalhaNaoAtivoError
  );
});

test("atividade comum encerra sem exigir campos de atendimento de falha", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const atividade = motor.encerrarAtividade(dt(9, 0));
  assert.equal(atividade.dadosFalha, undefined);
});

test("gps e foto sao opcionais e nunca bloqueiam o encerramento (D2/D3)", () => {
  const motor = motorComAtendimentoAtivo();
  motor.registrarDadosFalha({ nota: "1", ativo: "A", sintoma: "S", objeto: "O", observacao: "Obs" });
  const atividade = motor.encerrarAtividade(dt(9, 0));
  assert.equal(atividade.dadosFalha.gpsLatitude, null);
  assert.equal(atividade.dadosFalha.fotoCaminho, null);
});

test("registra gps e foto no atendimento de falha", () => {
  const motor = motorComAtendimentoAtivo();
  const capturadoEm = dt(8, 15);
  motor.registrarDadosFalha({
    nota: "1",
    ativo: "A",
    sintoma: "S",
    objeto: "O",
    observacao: "Obs",
    gpsLatitude: -22.9,
    gpsLongitude: -43.2,
    gpsPrecisaoMetros: 15.5,
    gpsCapturadoEm: capturadoEm,
    fotoCaminho: "atendimentos/foo.jpg",
  });
  const atividade = motor.encerrarAtividade(dt(9, 0));

  const dados = atividade.dadosFalha;
  assert.equal(dados.gpsLatitude, -22.9);
  assert.equal(dados.gpsLongitude, -43.2);
  assert.equal(dados.gpsPrecisaoMetros, 15.5);
  assert.equal(dados.gpsCapturadoEm, capturadoEm);
  assert.equal(dados.fotoCaminho, "atendimentos/foo.jpg");
});

test("transferirAtendimentoFalha encerra atividade incompleta (D4)", () => {
  const motor = motorComAtendimentoAtivo();
  motor.registrarDadosFalha({ nota: "1", ativo: "A" }); // so parcial

  const atividade = motor.transferirAtendimentoFalha(dt(8, 30));

  assert.equal(atividade.estado, "ENCERRADA");
  assert.equal(atividade.dadosFalha.nota, "1");
  assert.equal(atividade.dadosFalha.objeto, null);
  assert.equal(motor.jornada.estado, "ABERTA");
});

test("transferirAtendimentoFalha sem atendimento ativo lanca erro dedicado", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.transferirAtendimentoFalha(dt(8, 30)),
    Erros.AtendimentoFalhaNaoAtivoError
  );
});

test("transferirAtendimentoFalha em atividade comum nao e permitido", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motor.transferirAtendimentoFalha(dt(8, 30)),
    Erros.AtendimentoFalhaNaoAtivoError
  );
});

test("transferirAtendimentoFalha bloqueia com pausa aberta", () => {
  const motor = motorComAtendimentoAtivo();
  motor.iniciarPausa(dt(8, 20), "PAUSA_TESTE");
  assert.throws(
    () => motor.transferirAtendimentoFalha(dt(8, 30)),
    Erros.AtividadeEncerramentoComPausaAbertaError
  );
});

test("atendimento de falha pode ter pausa normalmente", () => {
  const motor = motorComAtendimentoAtivo();
  motor.iniciarPausa(dt(8, 30), "PAUSA_TESTE");
  motor.finalizarPausa(dt(8, 40));
  motor.registrarDadosFalha({ nota: "1", ativo: "A", sintoma: "S", objeto: "O", observacao: "Obs" });

  const atividade = motor.encerrarAtividade(dt(9, 0));

  assert.equal(calculo.duracaoPausasAtividade(atividade), 10 * 60000);
  assert.equal(calculo.duracaoAtividadeLiquida(atividade), 40 * 60000);
});

// ----------------------------------------------------------------------
// Evento secundario (ADR-0005, espelha tests/test_eventos_secundarios.py) -
// portado para JS no incremento de Evento Secundario na interface de campo.
// ----------------------------------------------------------------------
test("iniciar e encerrar deslocamento", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  const evento = motor.iniciarEventoSecundario(dt(8, 10), TipoEventoSecundario.DESLOCAMENTO, "EE12");
  assert.equal(evento.estado, "ATIVA");

  motor.encerrarEventoSecundario(dt(8, 40));
  assert.equal(evento.estado, "ENCERRADA");
  assert.equal(calculo.duracaoEventoSecundario(evento), 30 * 60000);
});

test("iniciar e encerrar espera e apoio", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));

  const espera = motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.ESPERA, "EE03");
  motor.encerrarEventoSecundario(dt(8, 15));

  const apoio = motor.iniciarEventoSecundario(dt(8, 15), TipoEventoSecundario.APOIO, "EE01");
  motor.encerrarEventoSecundario(dt(8, 45));

  assert.equal(calculo.duracaoEventoSecundario(espera), 15 * 60000);
  assert.equal(calculo.duracaoEventoSecundario(apoio), 30 * 60000);
});

test("evento secundario: tipo obrigatorio", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.iniciarEventoSecundario(dt(8, 0), null, "EE12"),
    Erros.EventoSecundarioTipoObrigatorioError
  );
});

test("evento secundario: motivo obrigatorio", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, ""),
    Erros.EventoSecundarioMotivoObrigatorioError
  );
});

test("bloqueia segundo evento secundario simultaneo", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "EE12");

  assert.throws(
    () => motor.iniciarEventoSecundario(dt(8, 5), TipoEventoSecundario.APOIO, "EE01"),
    Erros.EventoSecundarioJaAtivoError
  );
});

test("encerrar evento secundario sem nenhum ativo", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.encerrarEventoSecundario(dt(8, 10)),
    Erros.EventoSecundarioNaoAtivoError
  );
});

test("evento secundario mutuamente exclusivo: evento apos atividade", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  assert.throws(
    () => motor.iniciarEventoSecundario(dt(8, 20), TipoEventoSecundario.DESLOCAMENTO, "EE12"),
    Erros.EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError
  );
});

test("evento secundario mutuamente exclusivo: atividade apos evento", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.ESPERA, "EE03");

  assert.throws(
    () => motor.iniciarAtividade(dt(8, 20)),
    Erros.AtividadeExigeNenhumEventoSecundarioAtivoError
  );
});

test("bloqueia encerrar jornada com evento secundario aberto", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.APOIO, "EE01");

  assert.throws(
    () => motor.encerrarJornada(dt(9, 0)),
    Erros.JornadaComEventoSecundarioAbertoError
  );
});

test("timestamp invalido no evento secundario", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 30), TipoEventoSecundario.DESLOCAMENTO, "EE12");
  assert.throws(
    () => motor.encerrarEventoSecundario(dt(8, 0)),
    Erros.TimestampInvalidoError
  );
});

test("fluxo com evento secundario entra no tempo classificado", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.DESLOCAMENTO, "EE12");
  motor.encerrarEventoSecundario(dt(8, 30));

  motor.iniciarAtividade(dt(8, 30));
  motor.encerrarAtividade(dt(10, 30));

  motor.encerrarJornada(dt(10, 30));

  const resumo = calculo.resumoJornada(motor.jornada);
  assert.equal(resumo.jornadaBruta, (2 * 60 + 30) * 60000);
  assert.equal(resumo.tempoClassificado, (2 * 60 + 30) * 60000);
  assert.equal(resumo.tempoNaoClassificado, 0);
  assert.equal(resumo.eventosSecundarios.length, 1);
  assert.equal(resumo.eventosSecundarios[0].tipo, TipoEventoSecundario.DESLOCAMENTO);
  assert.equal(resumo.eventosSecundarios[0].duracao, 30 * 60000);
});

test("recuperacao de estado com evento secundario ativo", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), TipoEventoSecundario.ESPERA, "EE03");

  const recuperado = MotorJornada.aPartirDe(motor.jornada);
  recuperado.encerrarEventoSecundario(dt(8, 20));
  recuperado.iniciarAtividade(dt(8, 20));
  recuperado.encerrarAtividade(dt(9, 0));
  recuperado.encerrarJornada(dt(9, 0));

  assert.equal(recuperado.jornada.eventosSecundarios[0].fim.getTime(), dt(8, 20).getTime());
});

test("estado inconsistente: evento e atividade ativos juntos", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 0));
  // Adultera diretamente a entidade para simular corrupcao/adulteracao, ja
  // que o motor nunca permite chegar a este estado por transicoes normais
  // (mesmo caso de tests/test_eventos_secundarios.py).
  motor.jornada.eventosSecundarios.push({
    id: "evento-adulterado",
    tipo: TipoEventoSecundario.APOIO,
    motivo: "EE01",
    inicio: dt(8, 0),
    fim: null,
    estado: "ATIVA",
  });

  assert.throws(
    () => MotorJornada.aPartirDe(motor.jornada),
    Erros.EstadoInconsistenteError
  );
});

// ----------------------------------------------------------------------
// Ordem de servico e resultado de encerramento (ADR-0025, espelha
// tests/test_ordem_servico.py) - portado para JS no incremento de OS em
// EE17/EE23 na interface de campo.
// ----------------------------------------------------------------------
test("adicionarOrdemServico associa a atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  const ordem = motor.adicionarOrdemServico(dt(8, 15), "111");

  assert.equal(ordem.numero, "111");
  assert.equal(ordem.excluida, false);
  assert.deepEqual(motor.jornada.atividades[0].ordensServico, [ordem]);
});

test("adicionar multiplas ordens de servico", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  motor.adicionarOrdemServico(dt(8, 15), "111");
  motor.adicionarOrdemServico(dt(8, 20), "222");

  const numeros = motor.jornada.atividades[0].ordensServico.map((o) => o.numero);
  assert.deepEqual(numeros, ["111", "222"]);
});

test("adicionarOrdemServico numero obrigatorio", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motor.adicionarOrdemServico(dt(8, 15), ""),
    Erros.OrdemServicoNumeroObrigatorioError
  );
});

test("adicionarOrdemServico sem atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.adicionarOrdemServico(dt(8, 15), "111"),
    Erros.AtividadeNaoAtivaError
  );
});

test("adicionarOrdemServico em atendimento de falha nao e permitido", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtendimentoFalha(dt(8, 10));
  assert.throws(
    () => motor.adicionarOrdemServico(dt(8, 15), "111"),
    Erros.OrdemServicoExigeAtividadeSemFalhaError
  );
});

test("excluirOrdemServico marca excluida sem remover da lista", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const ordem = motor.adicionarOrdemServico(dt(8, 15), "111");

  motor.excluirOrdemServico(ordem.id);

  const atividade = motor.jornada.atividades[0];
  assert.equal(atividade.ordensServico.length, 1);
  assert.equal(atividade.ordensServico[0].excluida, true);
});

test("excluirOrdemServico e idempotente", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const ordem = motor.adicionarOrdemServico(dt(8, 15), "111");

  motor.excluirOrdemServico(ordem.id);
  motor.excluirOrdemServico(ordem.id);

  assert.equal(motor.jornada.atividades[0].ordensServico[0].excluida, true);
});

test("excluirOrdemServico inexistente", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motor.excluirOrdemServico("id-que-nao-existe"),
    Erros.OrdemServicoNaoEncontradaError
  );
});

test("excluirOrdemServico sem atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.excluirOrdemServico("qualquer-id"),
    Erros.AtividadeNaoAtivaError
  );
});

// ----------------------------------------------------------------------
// Equipe (aba Equipe, pedido do responsavel pelo produto em 2026-08-07,
// espelha tests/test_equipe.py) - mesmo padrao de ordem de servico acima,
// exceto que TAMBEM e permitida em atendimento de falha (quem estava
// presente independe do tipo de atividade).
// ----------------------------------------------------------------------
test("adicionarMembroEquipe associa a atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  const membro = motor.adicionarMembroEquipe(dt(8, 15), "54321");

  assert.equal(membro.matricula, "54321");
  assert.equal(membro.excluida, false);
  assert.deepEqual(motor.jornada.atividades[0].equipe, [membro]);
});

test("adicionar multiplos membros de equipe", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));

  motor.adicionarMembroEquipe(dt(8, 15), "54321");
  motor.adicionarMembroEquipe(dt(8, 20), "67890");

  const matriculas = motor.jornada.atividades[0].equipe.map((m) => m.matricula);
  assert.deepEqual(matriculas, ["54321", "67890"]);
});

test("adicionarMembroEquipe matricula obrigatoria", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motor.adicionarMembroEquipe(dt(8, 15), ""),
    Erros.MembroEquipeMatriculaObrigatoriaError
  );
});

test("adicionarMembroEquipe sem atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.adicionarMembroEquipe(dt(8, 15), "54321"),
    Erros.AtividadeNaoAtivaError
  );
});

test("adicionarMembroEquipe e permitido em atendimento de falha", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtendimentoFalha(dt(8, 10));

  const membro = motor.adicionarMembroEquipe(dt(8, 15), "54321");

  assert.equal(membro.matricula, "54321");
});

test("excluirMembroEquipe marca excluida sem remover da lista", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const membro = motor.adicionarMembroEquipe(dt(8, 15), "54321");

  motor.excluirMembroEquipe(membro.id);

  const atividade = motor.jornada.atividades[0];
  assert.equal(atividade.equipe.length, 1);
  assert.equal(atividade.equipe[0].excluida, true);
});

test("excluirMembroEquipe e idempotente", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const membro = motor.adicionarMembroEquipe(dt(8, 15), "54321");

  motor.excluirMembroEquipe(membro.id);
  motor.excluirMembroEquipe(membro.id);

  assert.equal(motor.jornada.atividades[0].equipe[0].excluida, true);
});

test("excluirMembroEquipe inexistente", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  assert.throws(
    () => motor.excluirMembroEquipe("id-que-nao-existe"),
    Erros.MembroEquipeNaoEncontradoError
  );
});

test("excluirMembroEquipe sem atividade ativa", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  assert.throws(
    () => motor.excluirMembroEquipe("qualquer-id"),
    Erros.AtividadeNaoAtivaError
  );
});

test("encerrarAtividade grava resultado CONCLUIDA", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.adicionarOrdemServico(dt(8, 15), "111");

  const atividade = motor.encerrarAtividade(dt(9, 0));

  assert.equal(atividade.resultado, ResultadoAtividade.CONCLUIDA);
  assert.equal(atividade.ordensServico[0].numero, "111");
});

test("encerrarAtividadeNaoConcluida grava resultado e preserva OS excluidas", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const ordem1 = motor.adicionarOrdemServico(dt(8, 15), "111");
  motor.adicionarOrdemServico(dt(8, 20), "222");
  motor.excluirOrdemServico(ordem1.id);

  const atividade = motor.encerrarAtividadeNaoConcluida(dt(9, 0));

  assert.equal(atividade.resultado, ResultadoAtividade.NAO_CONCLUIDA);
  assert.equal(atividade.ordensServico.length, 2);
  assert.equal(atividade.ordensServico[0].excluida, true);
  assert.equal(atividade.ordensServico[1].excluida, false);
});

test("encerrarAtividadeNaoConcluida em atendimento de falha nao e permitido", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtendimentoFalha(dt(8, 10));
  assert.throws(
    () => motor.encerrarAtividadeNaoConcluida(dt(9, 0)),
    Erros.AtividadeNaoConcluidaExigeSemDadosFalhaError
  );
});

// modoApontamentoSgo/pacoteOfflineUrlSgo (integracao SGO, 2026-08-11): a
// decisao de como o colaborador vai acessar o SGO (online via SSO, ou
// offline via pacote PWA ja confirmado) e' tomada ao criar a jornada, nunca
// depois - ver app.js (clique de "Iniciar jornada") e criarBlocoOrdensServico.
test("MotorJornada novo sem modo/pacote informado usa null (jornada antiga/compatibilidade)", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  assert.equal(motor.jornada.modoApontamentoSgo, null);
  assert.equal(motor.jornada.pacoteOfflineUrlSgo, null);
});

test("MotorJornada novo propaga modoApontamentoSgo 'online' para a jornada", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345", modoApontamentoSgo: "online" });
  assert.equal(motor.jornada.modoApontamentoSgo, "online");
  assert.equal(motor.jornada.pacoteOfflineUrlSgo, null);
});

test("MotorJornada novo propaga modoApontamentoSgo 'offline' e a URL do pacote", () => {
  const motor = new MotorJornada({
    colaboradorMatricula: "12345",
    modoApontamentoSgo: "offline",
    pacoteOfflineUrlSgo: "https://api-sgo-mrs.onrender.com/pacote/abc123",
  });
  assert.equal(motor.jornada.modoApontamentoSgo, "offline");
  assert.equal(motor.jornada.pacoteOfflineUrlSgo, "https://api-sgo-mrs.onrender.com/pacote/abc123");
});

test("MotorJornada.aPartirDe preserva modoApontamentoSgo/pacoteOfflineUrlSgo ja gravados", () => {
  const original = new MotorJornada({
    colaboradorMatricula: "12345",
    modoApontamentoSgo: "offline",
    pacoteOfflineUrlSgo: "https://api-sgo-mrs.onrender.com/pacote/xyz789",
  });
  original.iniciarJornada(dt(8, 0));

  const recuperado = MotorJornada.aPartirDe(original.jornada);
  assert.equal(recuperado.jornada.modoApontamentoSgo, "offline");
  assert.equal(recuperado.jornada.pacoteOfflineUrlSgo, "https://api-sgo-mrs.onrender.com/pacote/xyz789");
});

// equipeJornada/espelhoDe/gerarJornadaEspelho (2026-08-12): "Equipe da
// jornada" com replicacao de HH - decisao consciente do responsavel do
// produto apos eu apontar os riscos (HH por declaracao, sem captura
// propria de evento do colega - ver docs/96_ADR_0068...md).
test("MotorJornada novo sem equipeJornada informada usa lista vazia", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  assert.deepEqual(motor.jornada.equipeJornada, []);
  assert.equal(motor.jornada.espelhoDe, null);
});

test("MotorJornada novo propaga equipeJornada informada", () => {
  const equipe = [{ matricula: "11111", nome: "Fulano" }];
  const motor = new MotorJornada({ colaboradorMatricula: "12345", equipeJornada: equipe });
  assert.deepEqual(motor.jornada.equipeJornada, equipe);
});

test("gerarJornadaEspelho clona a jornada com id novo e matricula do colega", () => {
  const original = new MotorJornada({
    colaboradorMatricula: "12345",
    equipeJornada: [{ matricula: "11111", nome: "Fulano" }],
  });
  original.iniciarJornada(dt(8, 0));
  original.iniciarAtividade(dt(8, 10));
  original.encerrarAtividade(dt(9, 0));
  original.encerrarJornada(dt(9, 10));

  const espelho = gerarJornadaEspelho(original.jornada, "11111");

  assert.notEqual(espelho.id, original.jornada.id);
  assert.equal(espelho.colaboradorMatricula, "11111");
  assert.equal(espelho.espelhoDe, "12345");
  assert.deepEqual(espelho.equipeJornada, []);
  // Mesmos timestamps/eventos - e' um clone fiel, so' troca dono.
  assert.equal(espelho.inicio.getTime(), original.jornada.inicio.getTime());
  assert.equal(espelho.fim.getTime(), original.jornada.fim.getTime());
  assert.equal(espelho.atividades.length, original.jornada.atividades.length);
  assert.equal(espelho.atividades[0].id, original.jornada.atividades[0].id);
});

test("gerarJornadaEspelho nao compartilha referencia com a jornada original (clone de verdade)", () => {
  const original = new MotorJornada({ colaboradorMatricula: "12345" });
  original.iniciarJornada(dt(8, 0));
  original.iniciarAtividade(dt(8, 10));

  const espelho = gerarJornadaEspelho(original.jornada, "11111");
  espelho.atividades[0].resultado = "MEXIDO_NO_ESPELHO";

  assert.notEqual(original.jornada.atividades[0].resultado, "MEXIDO_NO_ESPELHO");
});
