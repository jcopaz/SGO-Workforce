// Testes de interface_campo/js/sincronizacao.js
// Roda com: node --test tests/js
//
// paraPayloadSincronizacao e pura (sem rede) e testada diretamente contra
// o contrato de workforce_storage.serializacao.jornada_para_dict.
// sincronizar() recebe um fetchImpl injetavel, entao os testes nunca fazem
// uma chamada de rede de verdade.

import { test } from "node:test";
import assert from "node:assert/strict";

import { MotorJornada } from "../../interface_campo/js/motorJornada.js";
import { novoPulsoGps } from "../../interface_campo/js/entidades.js";
import {
  paraPayloadSincronizacao,
  sincronizar,
  pulsoParaPayload,
  sincronizarPulsos,
} from "../../interface_campo/js/sincronizacao.js";

function dt(hora, minuto, dia = 1) {
  return new Date(2026, 0, dia, hora, minuto, 0, 0);
}

function jornadaEncerradaComPausa() {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  motor.iniciarPausa(dt(10, 0), "PAUSA_TESTE");
  motor.finalizarPausa(dt(10, 20));
  motor.encerrarAtividade(dt(12, 0));
  motor.encerrarJornada(dt(12, 10));
  return motor.jornada;
}

test("paraPayloadSincronizacao converte campos para o contrato do backend", () => {
  const jornada = jornadaEncerradaComPausa();
  const payload = paraPayloadSincronizacao(jornada);

  assert.equal(payload.id, jornada.id);
  assert.equal(payload.colaborador_matricula, "12345");
  assert.equal(payload.estado, "ENCERRADA");
  assert.equal(payload.inicio, dt(8, 0).toISOString());
  assert.equal(payload.fim, dt(12, 10).toISOString());
  assert.deepEqual(payload.eventos_secundarios, []);

  assert.equal(payload.atividades.length, 1);
  const atividade = payload.atividades[0];
  assert.equal(atividade.estado, "ENCERRADA");
  assert.equal(atividade.dados_falha, null);
  assert.equal(atividade.pausas.length, 1);

  const pausa = atividade.pausas[0];
  assert.equal(pausa.motivo, "PAUSA_TESTE");
  assert.equal(pausa.atividade_id, atividade.id);
  assert.equal(pausa.inicio, dt(10, 0).toISOString());
  assert.equal(pausa.fim, dt(10, 20).toISOString());
});

test("paraPayloadSincronizacao envia dados_falha de verdade quando ha atendimento de falha", () => {
  // Bug encontrado durante D2/D3: atividadeParaPayload sempre mandava
  // dados_falha: null, mesmo apos o motor JS ganhar atendimento de falha
  // no ADR-0021 - nenhum atendimento registrado no app de campo chegava
  // ao painel. Corrigido junto com GPS/foto (D2/D3).
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtendimentoFalha(dt(8, 10));
  motor.registrarDadosFalha({
    nota: "1",
    ativo: "A",
    sintoma: "S",
    objeto: "O",
    observacao: "Obs",
    gpsLatitude: -22.9,
    gpsLongitude: -43.2,
    gpsPrecisaoMetros: 15.5,
    gpsCapturadoEm: dt(8, 15),
    fotoCaminho: "atendimentos/foo.jpg",
  });
  motor.encerrarAtividade(dt(9, 0));
  motor.encerrarJornada(dt(9, 0));

  const payload = paraPayloadSincronizacao(motor.jornada);
  const dadosFalha = payload.atividades[0].dados_falha;

  assert.equal(dadosFalha.nota, "1");
  assert.equal(dadosFalha.objeto, "O");
  assert.equal(dadosFalha.gps_latitude, -22.9);
  assert.equal(dadosFalha.gps_capturado_em, dt(8, 15).toISOString());
  assert.equal(dadosFalha.foto_caminho, "atendimentos/foo.jpg");
});

test("paraPayloadSincronizacao serializa eventos_secundarios (incremento de Evento Secundario)", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarEventoSecundario(dt(8, 0), "DESLOCAMENTO", "EE12");
  motor.encerrarEventoSecundario(dt(8, 30));
  motor.iniciarAtividade(dt(8, 30));
  motor.encerrarAtividade(dt(9, 0));
  motor.encerrarJornada(dt(9, 0));

  const payload = paraPayloadSincronizacao(motor.jornada);

  assert.equal(payload.eventos_secundarios.length, 1);
  const evento = payload.eventos_secundarios[0];
  assert.equal(evento.tipo, "DESLOCAMENTO");
  assert.equal(evento.motivo, "EE12");
  assert.equal(evento.estado, "ENCERRADA");
  assert.equal(evento.inicio, dt(8, 0).toISOString());
  assert.equal(evento.fim, dt(8, 30).toISOString());
});

test("paraPayloadSincronizacao serializa ordens_servico e resultado (ADR-0025)", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const ordem1 = motor.adicionarOrdemServico(dt(8, 15), "111");
  motor.adicionarOrdemServico(dt(8, 20), "222");
  motor.excluirOrdemServico(ordem1.id);
  motor.encerrarAtividadeNaoConcluida(dt(9, 0));
  motor.encerrarJornada(dt(9, 0));

  const payload = paraPayloadSincronizacao(motor.jornada);
  const atividade = payload.atividades[0];

  assert.equal(atividade.resultado, "NAO_CONCLUIDA");
  assert.equal(atividade.ordens_servico.length, 2);
  assert.equal(atividade.ordens_servico[0].numero, "111");
  assert.equal(atividade.ordens_servico[0].excluida, true);
  assert.equal(atividade.ordens_servico[0].criada_em, dt(8, 15).toISOString());
  assert.equal(atividade.ordens_servico[1].numero, "222");
  assert.equal(atividade.ordens_servico[1].excluida, false);
});

test("paraPayloadSincronizacao serializa equipe (aba Equipe, 2026-08-07)", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "12345" });
  motor.iniciarJornada(dt(8, 0));
  motor.iniciarAtividade(dt(8, 10));
  const membro1 = motor.adicionarMembroEquipe(dt(8, 15), "54321");
  motor.adicionarMembroEquipe(dt(8, 20), "67890");
  motor.excluirMembroEquipe(membro1.id);
  motor.encerrarAtividade(dt(9, 0));
  motor.encerrarJornada(dt(9, 0));

  const payload = paraPayloadSincronizacao(motor.jornada);
  const atividade = payload.atividades[0];

  assert.equal(atividade.equipe.length, 2);
  assert.equal(atividade.equipe[0].matricula, "54321");
  assert.equal(atividade.equipe[0].excluida, true);
  assert.equal(atividade.equipe[0].adicionado_em, dt(8, 15).toISOString());
  assert.equal(atividade.equipe[1].matricula, "67890");
  assert.equal(atividade.equipe[1].excluida, false);
});

test("paraPayloadSincronizacao trata jornada em andamento (fim nulo)", () => {
  const motor = new MotorJornada({ colaboradorMatricula: "99999" });
  motor.iniciarJornada(dt(8, 0));
  const payload = paraPayloadSincronizacao(motor.jornada);

  assert.equal(payload.fim, null);
  assert.equal(payload.atividades.length, 0);
});

test("sincronizar() com configurada:false nao tenta chamar fetch", async () => {
  let chamado = false;
  const fetchFalso = async () => {
    chamado = true;
    return { ok: true };
  };

  // configurada explicito (nao depende de configSincronizacao.js real ter
  // ou nao valores preenchidos - evita um teste fragil que muda de
  // resultado conforme o ambiente e configurado para producao).
  const resultado = await sincronizar(jornadaEncerradaComPausa(), {
    fetchImpl: fetchFalso,
    configurada: false,
  });

  assert.equal(chamado, false);
  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /nao configurada/i);
});

test("sincronizar() nunca lanca quando o fetch falha (offline)", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };

  const resultado = await sincronizar(jornadaEncerradaComPausa(), {
    fetchImpl: fetchQueFalha,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /offline/i);
});

test("sincronizar() reporta falha quando o backend responde erro HTTP", async () => {
  const fetchComErro = async () => ({ ok: false, status: 401 });

  const resultado = await sincronizar(jornadaEncerradaComPausa(), {
    fetchImpl: fetchComErro,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /401/);
});

test("sincronizar() reporta sucesso quando o backend aceita", async () => {
  let corpoEnviado = null;
  let cabecalhoToken = null;
  const fetchOk = async (url, opcoesFetch) => {
    corpoEnviado = JSON.parse(opcoesFetch.body);
    cabecalhoToken = opcoesFetch.headers["X-Sync-Token"];
    return { ok: true, status: 200 };
  };

  const jornada = jornadaEncerradaComPausa();
  const resultado = await sincronizar(jornada, {
    fetchImpl: fetchOk,
    configurada: true,
    urlBase: "https://backend-de-teste.invalido",
    token: "token-de-teste",
  });

  assert.equal(resultado.ok, true);
  assert.equal(cabecalhoToken, "token-de-teste");
  assert.equal(corpoEnviado.id, jornada.id);
});

// Fase 2 da captacao de geolocalizacao (ADR-0043/0045): pulsoParaPayload +
// sincronizarPulsos, mesmo padrao de paraPayloadSincronizacao/sincronizar.

function pulsoExemplo(jornadaId) {
  return novoPulsoGps({
    jornadaId,
    colaboradorMatricula: "12345",
    latitude: -22.9,
    longitude: -43.2,
    precisaoMetros: 15.5,
    timestampDispositivo: dt(8, 30),
    velocidadeMetrosSegundo: 2.1,
    direcaoGraus: 180,
  });
}

test("pulsoParaPayload converte campos para o contrato do backend", () => {
  const pulso = pulsoExemplo("jornada-1");
  const payload = pulsoParaPayload(pulso);

  assert.equal(payload.id, pulso.id);
  assert.equal(payload.jornada_id, "jornada-1");
  assert.equal(payload.colaborador_matricula, "12345");
  assert.equal(payload.latitude, -22.9);
  assert.equal(payload.longitude, -43.2);
  assert.equal(payload.precisao_metros, 15.5);
  assert.equal(payload.timestamp_dispositivo, dt(8, 30).toISOString());
  assert.equal(payload.velocidade_metros_segundo, 2.1);
  assert.equal(payload.direcao_graus, 180);
});

test("sincronizarPulsos com lote vazio nao chama fetch e reporta sucesso", async () => {
  let chamado = false;
  const fetchFalso = async () => {
    chamado = true;
    return { ok: true };
  };

  const resultado = await sincronizarPulsos([], { fetchImpl: fetchFalso, configurada: true });

  assert.equal(chamado, false);
  assert.equal(resultado.ok, true);
});

test("sincronizarPulsos com configurada:false nao tenta chamar fetch", async () => {
  let chamado = false;
  const fetchFalso = async () => {
    chamado = true;
    return { ok: true };
  };

  const resultado = await sincronizarPulsos([pulsoExemplo("jornada-1")], {
    fetchImpl: fetchFalso,
    configurada: false,
  });

  assert.equal(chamado, false);
  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /nao configurada/i);
});

test("sincronizarPulsos nunca lanca quando o fetch falha (offline)", async () => {
  const fetchQueFalha = async () => {
    throw new TypeError("Failed to fetch");
  };

  const resultado = await sincronizarPulsos([pulsoExemplo("jornada-1")], {
    fetchImpl: fetchQueFalha,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /offline/i);
});

test("sincronizarPulsos reporta falha quando o backend responde erro HTTP", async () => {
  const fetchComErro = async () => ({ ok: false, status: 401 });

  const resultado = await sincronizarPulsos([pulsoExemplo("jornada-1")], {
    fetchImpl: fetchComErro,
    configurada: true,
  });

  assert.equal(resultado.ok, false);
  assert.match(resultado.mensagem, /401/);
});

test("sincronizarPulsos reporta sucesso e envia o lote inteiro no corpo", async () => {
  let corpoEnviado = null;
  let cabecalhoToken = null;
  const fetchOk = async (url, opcoesFetch) => {
    corpoEnviado = JSON.parse(opcoesFetch.body);
    cabecalhoToken = opcoesFetch.headers["X-Sync-Token"];
    return { ok: true, status: 200 };
  };

  const pulsos = [pulsoExemplo("jornada-1"), pulsoExemplo("jornada-1")];
  const resultado = await sincronizarPulsos(pulsos, {
    fetchImpl: fetchOk,
    configurada: true,
    urlBase: "https://backend-de-teste.invalido",
    token: "token-de-teste",
  });

  assert.equal(resultado.ok, true);
  assert.equal(cabecalhoToken, "token-de-teste");
  assert.equal(corpoEnviado.length, 2);
  assert.equal(corpoEnviado[0].id, pulsos[0].id);
  assert.equal(corpoEnviado[0].jornada_id, "jornada-1");
});
