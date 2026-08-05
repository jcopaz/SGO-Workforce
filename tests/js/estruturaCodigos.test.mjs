// Testes de interface_campo/js/estruturaCodigos.js
// Roda com: node --test tests/js
//
// O teste mais importante deste arquivo e o de cobertura dos 23 codigos:
// a especificacao original recebida do responsavel pelo produto (ADR-0050)
// esqueceu o EE22 num bloco - esse teste existe especificamente para
// nunca deixar isso passar batido de novo, para qualquer codigo.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  BLOCO_APOIO_PREPARACAO,
  BLOCO_EXECUCAO,
  BLOCO_INTERRUPCOES,
  ESTRUTURA_BLOCOS,
  agruparCodigosDisponiveis,
} from "../../interface_campo/js/estruturaCodigos.js";

// Os 23 codigos reais do Relatorio 1 (src/workforce_core/catalogo.py::catalogo_relatorio_1_manutencao) -
// EE17/EE21/EE23 sao pontos de entrada/desfecho de Atividade, nunca
// aparecem soltos na estrutura de blocos (ver reconciliacao no topo de
// estruturaCodigos.js) - excluidos deliberadamente da lista abaixo.
const CODIGOS_SOLTOS_ESPERADOS = [
  "EE01", "EE02", "EE03", "EE04", "EE05", "EE06", "EE07", "EE08", "EE09", "EE10",
  "EE11", "EE12", "EE13", "EE14", "EE15", "EE16", "EE18", "EE19", "EE20", "EE22",
];

function todosOsCodigosDaEstrutura() {
  const codigos = [];
  for (const bloco of ESTRUTURA_BLOCOS) {
    for (const codigo of bloco.codigos ?? []) codigos.push(codigo);
    for (const subgrupo of bloco.subgrupos ?? []) {
      for (const codigo of subgrupo.codigos) codigos.push(codigo);
    }
  }
  return codigos;
}

test("todo codigo solto esperado aparece exatamente uma vez na estrutura de blocos", () => {
  const codigos = todosOsCodigosDaEstrutura();
  const contagem = new Map();
  for (const codigo of codigos) {
    contagem.set(codigo, (contagem.get(codigo) ?? 0) + 1);
  }

  for (const esperado of CODIGOS_SOLTOS_ESPERADOS) {
    assert.equal(
      contagem.get(esperado),
      1,
      `codigo ${esperado} deveria aparecer exatamente 1 vez, apareceu ${contagem.get(esperado) ?? 0}`
    );
  }
});

test("a estrutura nao contem nenhum codigo alem dos esperados (nem EE17/21/23, nem duplicata)", () => {
  const codigos = todosOsCodigosDaEstrutura();
  const codigosUnicos = new Set(codigos);

  assert.equal(codigos.length, codigosUnicos.size, "ha codigo duplicado em mais de um bloco/subgrupo");
  assert.deepEqual([...codigosUnicos].sort(), [...CODIGOS_SOLTOS_ESPERADOS].sort());
});

function motivo(codigo, descricao = `Descricao de ${codigo}`) {
  return { codigo, descricao };
}

test("agruparCodigosDisponiveis filtra so os codigos presentes na lista informada", () => {
  const disponiveis = [motivo("EE02"), motivo("EE11"), motivo("EE22")];

  const blocos = agruparCodigosDisponiveis(disponiveis);

  // So o bloco Interrupcoes > Pausas deveria sobrar - Apoio/Preparacao e
  // Execucao ficam vazios (nenhum codigo deles esta em `disponiveis`).
  assert.equal(blocos.length, 1);
  assert.equal(blocos[0].id, BLOCO_INTERRUPCOES);
  assert.equal(blocos[0].subgrupos.length, 1);
  assert.equal(blocos[0].subgrupos[0].titulo, "Pausas");
  assert.deepEqual(
    blocos[0].subgrupos[0].itens.map((item) => item.codigo).sort(),
    ["EE02", "EE11", "EE22"]
  );
});

test("agruparCodigosDisponiveis mantem blocos de codigo solto e de subgrupo separados", () => {
  const disponiveis = [motivo("EE01"), motivo("EE16"), motivo("EE03")];

  const blocos = agruparCodigosDisponiveis(disponiveis);
  const porId = Object.fromEntries(blocos.map((b) => [b.id, b]));

  assert.deepEqual(porId[BLOCO_APOIO_PREPARACAO].itens.map((i) => i.codigo), ["EE01"]);
  assert.deepEqual(porId[BLOCO_EXECUCAO].itens.map((i) => i.codigo), ["EE16"]);
  assert.equal(porId[BLOCO_INTERRUPCOES].subgrupos[0].titulo, "Esperas");
  assert.deepEqual(porId[BLOCO_INTERRUPCOES].subgrupos[0].itens.map((i) => i.codigo), ["EE03"]);
});

test("agruparCodigosDisponiveis injeta itensExtrasPorBloco no comeco do bloco indicado", () => {
  const disponiveis = [motivo("EE16")];
  const extraAtividade = { codigo: "__ATIVIDADE__", rotulo: "Iniciar atividade (EE17)" };
  const extraFalha = { codigo: "__FALHA__", rotulo: "Atendimento de falha (EE21)" };

  const blocos = agruparCodigosDisponiveis(disponiveis, {
    [BLOCO_EXECUCAO]: [extraAtividade, extraFalha],
  });

  const execucao = blocos.find((b) => b.id === BLOCO_EXECUCAO);
  assert.deepEqual(
    execucao.itens.map((i) => i.codigo),
    ["__ATIVIDADE__", "__FALHA__", "EE16"]
  );
});

test("agruparCodigosDisponiveis com itensExtrasPorBloco cria o bloco mesmo sem nenhum codigo do catalogo", () => {
  const extraAtividade = { codigo: "__ATIVIDADE__", rotulo: "Iniciar atividade (EE17)" };

  const blocos = agruparCodigosDisponiveis([], { [BLOCO_EXECUCAO]: [extraAtividade] });

  const execucao = blocos.find((b) => b.id === BLOCO_EXECUCAO);
  assert.ok(execucao, "bloco Execucao deveria aparecer so por causa do item extra");
  assert.deepEqual(execucao.itens.map((i) => i.codigo), ["__ATIVIDADE__"]);
});

test("agruparCodigosDisponiveis coloca codigo desconhecido em Outros, nunca descarta", () => {
  const disponiveis = [motivo("EE99", "Codigo futuro desconhecido")];

  const blocos = agruparCodigosDisponiveis(disponiveis);

  assert.equal(blocos.length, 1);
  assert.equal(blocos[0].id, "outros");
  assert.deepEqual(blocos[0].itens.map((i) => i.codigo), ["EE99"]);
});

test("agruparCodigosDisponiveis com lista vazia e sem extras devolve estrutura vazia", () => {
  assert.deepEqual(agruparCodigosDisponiveis([]), []);
});
