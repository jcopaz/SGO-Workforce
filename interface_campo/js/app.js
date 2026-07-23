// Interface operacional simples para celular (Incremento 4).
//
// Piloto tecnico: apenas Jornada + Atividade + Pausa, sem autenticacao,
// sem GPS, sem RASF, sem sincronizacao com servidor (nao existe API real
// ainda - ver docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).
// Motivo de pausa fixo em PAUSA_TESTE, conforme decisao provisoria do
// Incremento 1 (catalogo oficial e Incremento 5).

import { MotorJornada } from "./motorJornada.js";
import * as calculo from "./calculo.js";
import * as Erros from "./erros.js";
import { carregarJornada, listarJornadasAbertas, salvarJornada } from "./armazenamento.js";

const els = {
  matricula: document.getElementById("matricula"),
  status: document.getElementById("status"),
  mensagem: document.getElementById("mensagem"),
  resumo: document.getElementById("resumo"),
  botoes: document.getElementById("botoes"),
};

let motor = null;

// Motivos de pausa do "Relatorio de Atividades Diarias de Manutencao"
// (Relatorio 1, codigos EE01-EE23), o formulario em papel que a equipe
// realmente usa hoje - fornecido pelo responsavel pelo produto em
// 2026-07-23 (ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md).
// Sao os 5 codigos que, no motor de dominio, interrompem uma atividade em
// andamento (equivalente a workforce_core.catalogo.codigos_relatorio_1_por_tipo_registro("pausa")).
// Os demais 16 codigos do Relatorio 1 sao "evento secundario"
// (deslocamento/espera/apoio) e ainda nao tem tela propria aqui - ver ADR.
// classificacao produtiva/improdutiva continua NAO_DEFINIDO (nao validada).
const MOTIVOS_PAUSA_RELATORIO_1 = [
  { codigo: "EE02", rotulo: "Refeição 1 hora" },
  { codigo: "EE07", rotulo: "Reunião ou ADM" },
  { codigo: "EE11", rotulo: "Consulta à documentação técnica" },
  { codigo: "EE21", rotulo: "SMS" },
  { codigo: "EE23", rotulo: "Treinamento" },
];

function criarSeletorMotivoPausa() {
  const select = document.createElement("select");
  select.id = "motivoPausa";
  select.className = "seletor-motivo";
  for (const motivo of MOTIVOS_PAUSA_RELATORIO_1) {
    const opcao = document.createElement("option");
    opcao.value = motivo.codigo;
    opcao.textContent = `${motivo.codigo} - ${motivo.rotulo}`;
    select.appendChild(opcao);
  }
  return select;
}

function botao(texto, aoClicar, { destaque = false } = {}) {
  const b = document.createElement("button");
  b.textContent = texto;
  b.className = destaque ? "botao botao-destaque" : "botao";
  b.addEventListener("click", aoClicar);
  return b;
}

function limparMensagem() {
  els.mensagem.textContent = "";
  els.mensagem.className = "mensagem";
}

function mostrarErro(erro) {
  els.mensagem.textContent = erro.message || String(erro);
  els.mensagem.className = "mensagem mensagem-erro";
}

function mostrarAviso(texto) {
  els.mensagem.textContent = texto;
  els.mensagem.className = "mensagem mensagem-aviso";
}

async function persistir() {
  await salvarJornada(motor.jornada);
}

function formatoHora(data) {
  if (!data) return "--:--";
  return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function linhaResumo(rotulo, valor) {
  const tr = document.createElement("tr");
  const tdRotulo = document.createElement("td");
  tdRotulo.textContent = rotulo;
  const tdValor = document.createElement("td");
  tdValor.textContent = valor;
  tr.append(tdRotulo, tdValor);
  return tr;
}

function renderResumoEncerrado() {
  const resumo = calculo.resumoJornada(motor.jornada);
  const tabela = document.createElement("table");
  tabela.className = "tabela-resumo";
  tabela.append(
    linhaResumo("Jornada bruta", calculo.formatarDuracao(resumo.jornadaBruta)),
    linhaResumo("Tempo classificado", calculo.formatarDuracao(resumo.tempoClassificado)),
    linhaResumo("Tempo nao classificado", calculo.formatarDuracao(resumo.tempoNaoClassificado))
  );
  els.resumo.replaceChildren(tabela);
}

function renderResumoEmAndamento() {
  // Indicativo apenas: a duracao oficial e sempre recalculada a partir dos
  // timestamps persistidos quando os eventos forem encerrados. Isto aqui
  // e so para o colaborador ter uma nocao de tempo decorrido em tela.
  const agora = new Date();
  const partes = [];
  if (motor.jornada.inicio) {
    partes.push(`Jornada iniciada as ${formatoHora(motor.jornada.inicio)}`);
  }
  const atividade = motor._atividadeAtiva;
  if (atividade) {
    partes.push(`Atividade iniciada as ${formatoHora(atividade.inicio)}`);
  }
  const pausa = motor._pausaAtiva;
  if (pausa) {
    partes.push(`Pausa iniciada as ${formatoHora(pausa.inicio)} (motivo: ${pausa.motivo})`);
  }
  const paragrafo = document.createElement("p");
  paragrafo.className = "em-andamento";
  paragrafo.textContent = partes.join(" · ");
  els.resumo.replaceChildren(paragrafo);
}

function render() {
  els.botoes.replaceChildren();
  els.resumo.replaceChildren();

  if (!motor || motor.jornada.estado === "NAO_INICIADA") {
    els.status.textContent = "Nenhuma jornada em andamento.";
    els.matricula.disabled = false;
    els.botoes.appendChild(
      botao(
        "Iniciar jornada",
        () => {
          if (!prepararMotorComMatricula()) return;
          executar(() => motor.iniciarJornada(new Date()));
        },
        { destaque: true }
      )
    );
    return;
  }

  els.matricula.disabled = true;

  if (motor.jornada.estado === "ENCERRADA") {
    els.status.textContent = `Jornada encerrada as ${formatoHora(motor.jornada.fim)}.`;
    renderResumoEncerrado();
    els.botoes.appendChild(
      botao(
        "Iniciar nova jornada",
        () => {
          motor = null;
          limparMensagem();
          render();
        },
        { destaque: true }
      )
    );
    return;
  }

  // ABERTA
  const pausa = motor._pausaAtiva;
  const atividade = motor._atividadeAtiva;

  if (pausa) {
    els.status.textContent = "Em pausa.";
    els.botoes.appendChild(
      botao("Finalizar pausa", () => executar(() => motor.finalizarPausa(new Date())), {
        destaque: true,
      })
    );
  } else if (atividade) {
    els.status.textContent = "Atividade em andamento.";
    const seletorMotivo = criarSeletorMotivoPausa();
    els.botoes.appendChild(seletorMotivo);
    els.botoes.appendChild(
      botao("Iniciar pausa", () =>
        executar(() => motor.iniciarPausa(new Date(), seletorMotivo.value))
      )
    );
    els.botoes.appendChild(
      botao("Encerrar atividade", () => executar(() => motor.encerrarAtividade(new Date())), {
        destaque: true,
      })
    );
  } else {
    els.status.textContent = "Jornada aberta, sem atividade em andamento.";
    els.botoes.appendChild(
      botao("Iniciar atividade", () => executar(() => motor.iniciarAtividade(new Date())), {
        destaque: true,
      })
    );
    els.botoes.appendChild(
      botao("Encerrar jornada", () => executar(() => motor.encerrarJornada(new Date())))
    );
  }

  renderResumoEmAndamento();
}

async function executar(transicao) {
  limparMensagem();
  try {
    transicao();
    await persistir();
  } catch (erro) {
    if (erro instanceof Erros.ErroDominio) {
      mostrarErro(erro);
    } else {
      mostrarErro(new Error("Falha inesperada ao registrar o evento. Tente novamente."));
      // eslint-disable-next-line no-console
      console.error(erro);
    }
  }
  render();
}

// Cria o motor a partir da matricula digitada, se ainda nao existir um
// motor para uma jornada nao iniciada. Chamado no clique de "Iniciar
// jornada" - nao no carregamento da pagina - para sempre usar o valor mais
// recente do campo de matricula.
function prepararMotorComMatricula() {
  const matricula = els.matricula.value.trim();
  if (!matricula) {
    mostrarAviso("Informe a matricula antes de iniciar a jornada.");
    return false;
  }
  if (!motor || motor.jornada.estado === "NAO_INICIADA") {
    motor = new MotorJornada({ colaboradorMatricula: matricula });
  }
  return true;
}

async function iniciar() {
  const abertas = await listarJornadasAbertas();
  if (abertas.length > 1) {
    // Nunca deveria acontecer (regra de ouro: uma jornada aberta por vez).
    // Se acontecer, e sinal de dado corrompido/adulterado - nao decide
    // sozinho qual e a valida.
    mostrarErro(
      new Error(
        "Mais de uma jornada aberta encontrada localmente. Contate o suporte tecnico antes de continuar."
      )
    );
    return;
  }
  if (abertas.length === 1) {
    const jornada = abertas[0];
    try {
      motor = MotorJornada.aPartirDe(jornada);
      els.matricula.value = jornada.colaboradorMatricula;
      mostrarAviso("Jornada em andamento recuperada apos reabertura do aplicativo.");
    } catch (erro) {
      mostrarErro(erro);
      return;
    }
  }
  render();
}

iniciar();
