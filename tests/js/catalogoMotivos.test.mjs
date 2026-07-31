// Testes de interface_campo/js/catalogoMotivos.js
// Roda com: node --test tests/js
//
// _limparCacheParaTeste() garante isolamento entre casos (mesmo motivo de
// RelogioSimulado.voltarParaTempoReal() em relogioSimulado.test.mjs).

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  obterMotivosPausa,
  obterEventosSecundarios,
  _limparCacheParaTeste,
} from "../../interface_campo/js/catalogoMotivos.js";

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

// ----------------------------------------------------------------------
// Pausas avulsas (ADR-0030): EE02/EE07/EE11/EE20/EE22 continuam
// tipo_registro "pausa", mas ganham tipo_evento_secundario (sempre
// APOIO) para poderem ser iniciadas soltas, sem atividade ativa, na
// lista unica de acoes da tela de topo (app.js).
// ----------------------------------------------------------------------
test("obterMotivosPausa sem configuracao ja traz tipo_evento_secundario nos 5 codigos avulsos", async () => {
  const motivos = await obterMotivosPausa({ configurada: false });

  const codigosAvulsos = ["EE02", "EE07", "EE11", "EE20", "EE22"];
  for (const codigo of codigosAvulsos) {
    const motivo = motivos.find((m) => m.codigo === codigo);
    assert.ok(motivo, `codigo ${codigo} deveria estar na lista minima embutida`);
    assert.equal(motivo.tipo_evento_secundario, "APOIO", codigo);
  }
});

test("obterMotivosPausa repara tipo_evento_secundario nulo vindo do backend (coluna nao migrada)", async () => {
  const catalogoDoBackend = [
    {
      codigo: "EE20",
      descricao: "DDS / APR",
      tipo_registro: "pausa",
      ativo: true,
      tipo_evento_secundario: null,
    },
  ];
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });

  const motivos = await obterMotivosPausa({ configurada: true, fetchImpl: fetchOk });

  assert.equal(motivos[0].tipo_evento_secundario, "APOIO");
});

// ----------------------------------------------------------------------
// obterEventosSecundarios (incremento de Evento Secundario na interface
// de campo) - mesmo cache/fallback de obterMotivosPausa, so muda o filtro.
// ----------------------------------------------------------------------
test("obterEventosSecundarios sem configuracao usa a lista minima embutida", async () => {
  const eventos = await obterEventosSecundarios({ configurada: false });

  assert.ok(eventos.length > 0);
  assert.ok(eventos.every((e) => e.tipo_registro === "evento_secundario" && e.ativo));
  assert.ok(eventos.every((e) => e.tipo_evento_secundario));
  assert.ok(eventos.some((e) => e.codigo === "EE12" && e.tipo_evento_secundario === "DESLOCAMENTO"));
  assert.ok(eventos.some((e) => e.codigo === "EE01" && e.tipo_evento_secundario === "APOIO"));
});

test("obterEventosSecundarios filtra so evento_secundario+ativo do backend", async () => {
  const catalogoDoBackend = [
    { codigo: "EE02", descricao: "Refeição", tipo_registro: "pausa", ativo: true },
    {
      codigo: "EE12",
      descricao: "Deslocamento rodoviário",
      tipo_registro: "evento_secundario",
      ativo: true,
      tipo_evento_secundario: "DESLOCAMENTO",
    },
    {
      codigo: "EE03",
      descricao: "Aguardando CCO",
      tipo_registro: "evento_secundario",
      ativo: false,
      tipo_evento_secundario: "ESPERA",
    },
  ];
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });

  const eventos = await obterEventosSecundarios({ configurada: true, fetchImpl: fetchOk });

  assert.equal(eventos.length, 1);
  assert.equal(eventos[0].codigo, "EE12");
  assert.equal(eventos[0].tipo_evento_secundario, "DESLOCAMENTO");
});

// Bug real de producao (2026-07-29): o backend criou a coluna
// tipo_evento_secundario via ALTER TABLE (ADR-0024) sem preencher dado
// retroativo, entao GET /catalogo respondia os 15 codigos evento_secundario
// com tipo_evento_secundario NULL ate o backend ser reparado/reiniciado -
// motor.iniciarEventoSecundario travava com EventoSecundarioTipoObrigatorioError
// toda vez que o colaborador tentava iniciar deslocamento/espera/apoio.
// obterEventosSecundarios precisa reparar isso no cliente, sem esperar o
// proximo deploy do backend.
test("obterEventosSecundarios repara tipo_evento_secundario nulo vindo do backend (coluna nao migrada)", async () => {
  const catalogoDoBackend = [
    {
      codigo: "EE01",
      descricao: "Preparação para jornada",
      tipo_registro: "evento_secundario",
      ativo: true,
      tipo_evento_secundario: null,
    },
    {
      codigo: "EE12",
      descricao: "Deslocamento rodoviário",
      tipo_registro: "evento_secundario",
      ativo: true,
      tipo_evento_secundario: null,
    },
  ];
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });

  const eventos = await obterEventosSecundarios({ configurada: true, fetchImpl: fetchOk });

  assert.equal(eventos.length, 2);
  assert.ok(eventos.every((e) => e.tipo_evento_secundario), "nenhum evento deveria ficar sem tipo");
  assert.equal(eventos.find((e) => e.codigo === "EE01").tipo_evento_secundario, "APOIO");
  assert.equal(eventos.find((e) => e.codigo === "EE12").tipo_evento_secundario, "DESLOCAMENTO");
});

test("obterEventosSecundarios nao sobrescreve tipo_evento_secundario ja preenchido pelo backend", async () => {
  // EE01 e mapeado como APOIO no reparo local - se o backend um dia vier
  // com outro valor (reclassificacao futura via painel), o reparo local
  // nunca deve competir com o dado que ja veio preenchido.
  const catalogoDoBackend = [
    {
      codigo: "EE01",
      descricao: "Preparação para jornada",
      tipo_registro: "evento_secundario",
      ativo: true,
      tipo_evento_secundario: "ESPERA",
    },
  ];
  const fetchOk = async () => ({ ok: true, json: async () => catalogoDoBackend });

  const eventos = await obterEventosSecundarios({ configurada: true, fetchImpl: fetchOk });

  assert.equal(eventos[0].tipo_evento_secundario, "ESPERA");
});

test("obterMotivosPausa e obterEventosSecundarios compartilham o mesmo cache do backend", async () => {
  const catalogoDoBackend = [
    { codigo: "EE02", descricao: "Refeição", tipo_registro: "pausa", ativo: true },
    {
      codigo: "EE12",
      descricao: "Deslocamento rodoviário",
      tipo_registro: "evento_secundario",
      ativo: true,
      tipo_evento_secundario: "DESLOCAMENTO",
    },
  ];
  await obterMotivosPausa({
    configurada: true,
    fetchImpl: async () => ({ ok: true, json: async () => catalogoDoBackend }),
  });

  // Sem nova chamada de fetch (configurada: false) - deve ler do mesmo
  // cache gravado pela chamada acima.
  const eventos = await obterEventosSecundarios({ configurada: false });

  assert.equal(eventos.length, 1);
  assert.equal(eventos[0].codigo, "EE12");
});
