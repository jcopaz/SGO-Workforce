// Interface operacional simples para celular (Incremento 4).
//
// Piloto tecnico: apenas Jornada + Atividade + Pausa, sem autenticacao,
// sem GPS, sem RASF. Sincronizacao com o backend real existe (ver
// sincronizacao.js e docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md)
// mas e best-effort: uma falha de rede nunca impede o registro local do
// evento (offline-first).
// Motivo de pausa fixo em PAUSA_TESTE, conforme decisao provisoria do
// Incremento 1 (catalogo oficial e Incremento 5).

import { MotorJornada } from "./motorJornada.js";
import * as calculo from "./calculo.js";
import * as Erros from "./erros.js";
import { carregarJornada, listarJornadasAbertas, salvarJornada } from "./armazenamento.js";
import * as RelogioSimulado from "./relogioSimulado.js";
import * as Sincronizacao from "./sincronizacao.js";

const els = {
  matricula: document.getElementById("matricula"),
  status: document.getElementById("status"),
  statusSincronizacao: document.getElementById("statusSincronizacao"),
  mensagem: document.getElementById("mensagem"),
  resumo: document.getElementById("resumo"),
  botoes: document.getElementById("botoes"),
  faixaSimulacao: document.getElementById("faixaSimulacao"),
  simuladorStatus: document.getElementById("simuladorStatus"),
  simAvancar15m: document.getElementById("simAvancar15m"),
  simAvancar1h: document.getElementById("simAvancar1h"),
  simAvancar8h: document.getElementById("simAvancar8h"),
  simAvancar1d: document.getElementById("simAvancar1d"),
  simDataHora: document.getElementById("simDataHora"),
  simAplicarData: document.getElementById("simAplicarData"),
  simReiniciar: document.getElementById("simReiniciar"),
};

let motor = null;
// { ok: boolean|null, mensagem: string } | null - null antes de qualquer
// tentativa de sincronizacao nesta sessao do app. ok:null == "em andamento".
let ultimoStatusSincronizacao = null;

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
  dispararSincronizacao();
}

// Sincronizacao best-effort e assincrona: dispara sem bloquear a resposta
// local ao colaborador (offline-first) e so atualiza a tela de status
// quando a chamada termina. Nunca lanca (sincronizacao.js garante isso).
function dispararSincronizacao() {
  if (!motor) return;
  const jornadaNoMomento = motor.jornada;
  ultimoStatusSincronizacao = { ok: null, mensagem: "Sincronizando..." };
  renderStatusSincronizacao();
  Sincronizacao.sincronizar(jornadaNoMomento).then((resultado) => {
    // So atualiza se ainda estivermos olhando para a mesma jornada (evita
    // mostrar o resultado de uma sincronizacao antiga apos o colaborador
    // ja ter iniciado outra jornada).
    if (motor && motor.jornada === jornadaNoMomento) {
      ultimoStatusSincronizacao = resultado;
      renderStatusSincronizacao();
    }
  });
}

function renderStatusSincronizacao() {
  if (!els.statusSincronizacao) return;
  if (!ultimoStatusSincronizacao) {
    els.statusSincronizacao.textContent = "";
    els.statusSincronizacao.className = "status-sincronizacao";
    return;
  }
  els.statusSincronizacao.textContent = ultimoStatusSincronizacao.mensagem;
  const sufixo =
    ultimoStatusSincronizacao.ok === null
      ? "pendente"
      : ultimoStatusSincronizacao.ok
        ? "ok"
        : "erro";
  els.statusSincronizacao.className = `status-sincronizacao status-sincronizacao-${sufixo}`;
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
  // timestamps persistidos quando os eventos forem encerrados. O "decorrido"
  // abaixo usa o mesmo relogio (real ou simulado) que sera gravado se o
  // colaborador clicar em algum botao agora - nao e um relogio visual
  // desconectado do que fica persistido.
  const agora = RelogioSimulado.agora();
  const partes = [];
  if (motor.jornada.inicio) {
    const decorridoJornada = calculo.formatarDuracao(agora.getTime() - motor.jornada.inicio.getTime());
    partes.push(`Jornada iniciada as ${formatoHora(motor.jornada.inicio)} (decorrido: ${decorridoJornada})`);
  }
  const atividade = motor._atividadeAtiva;
  if (atividade) {
    const decorridoAtividade = calculo.formatarDuracao(agora.getTime() - atividade.inicio.getTime());
    partes.push(`Atividade iniciada as ${formatoHora(atividade.inicio)} (decorrido: ${decorridoAtividade})`);
  }
  const pausa = motor._pausaAtiva;
  if (pausa) {
    const decorridoPausa = calculo.formatarDuracao(agora.getTime() - pausa.inicio.getTime());
    partes.push(
      `Pausa iniciada as ${formatoHora(pausa.inicio)} (motivo: ${pausa.motivo}, decorrido: ${decorridoPausa})`
    );
  }
  const paragrafo = document.createElement("p");
  paragrafo.className = "em-andamento";
  paragrafo.textContent = partes.join(" · ");
  els.resumo.replaceChildren(paragrafo);
}

// Faixa de aviso sempre visivel (fora do <details> do simulador) quando o
// relogio esta adiantado - nunca deve ficar escondido que o app esta fora
// do tempo real, mesmo com o painel do simulador recolhido.
function renderFaixaSimulacao() {
  if (RelogioSimulado.estaSimulando()) {
    els.faixaSimulacao.textContent = `Simulacao de tempo ativa (${RelogioSimulado.descreverDeslocamento()}) - isto NAO e o relogio real.`;
    els.faixaSimulacao.hidden = false;
  } else {
    els.faixaSimulacao.textContent = "";
    els.faixaSimulacao.hidden = true;
  }
  if (els.simuladorStatus) {
    els.simuladorStatus.textContent = `Relogio efetivo: ${formatoHora(RelogioSimulado.agora())} (${RelogioSimulado.descreverDeslocamento()})`;
  }
}

function render() {
  els.botoes.replaceChildren();
  els.resumo.replaceChildren();
  renderFaixaSimulacao();
  renderStatusSincronizacao();

  if (!motor || motor.jornada.estado === "NAO_INICIADA") {
    els.status.textContent = "Nenhuma jornada em andamento.";
    els.matricula.disabled = false;
    els.botoes.appendChild(
      botao(
        "Iniciar jornada",
        () => {
          if (!prepararMotorComMatricula()) return;
          executar(() => motor.iniciarJornada(RelogioSimulado.agora()));
        },
        { destaque: true }
      )
    );
    return;
  }

  els.matricula.disabled = true;
  els.botoes.appendChild(botao("Sincronizar agora", () => dispararSincronizacao()));

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
      botao("Finalizar pausa", () => executar(() => motor.finalizarPausa(RelogioSimulado.agora())), {
        destaque: true,
      })
    );
  } else if (atividade) {
    els.status.textContent = "Atividade em andamento.";
    const seletorMotivo = criarSeletorMotivoPausa();
    els.botoes.appendChild(seletorMotivo);
    els.botoes.appendChild(
      botao("Iniciar pausa", () =>
        executar(() => motor.iniciarPausa(RelogioSimulado.agora(), seletorMotivo.value))
      )
    );
    els.botoes.appendChild(
      botao("Encerrar atividade", () => executar(() => motor.encerrarAtividade(RelogioSimulado.agora())), {
        destaque: true,
      })
    );
  } else {
    els.status.textContent = "Jornada aberta, sem atividade em andamento.";
    els.botoes.appendChild(
      botao("Iniciar atividade", () => executar(() => motor.iniciarAtividade(RelogioSimulado.agora())), {
        destaque: true,
      })
    );
    els.botoes.appendChild(
      botao("Encerrar jornada", () => executar(() => motor.encerrarJornada(RelogioSimulado.agora())))
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

// Liga os controles do painel "Simulador de tempo (somente teste)". So
// mexe no relogio (RelogioSimulado) - nunca chama o motor de dominio
// diretamente, entao funciona independente de haver ou nao jornada aberta.
function configurarSimulador() {
  if (!els.simAvancar15m) return; // painel nao presente no HTML (defensivo)

  els.simAvancar15m.addEventListener("click", () => {
    RelogioSimulado.avancar(15 * RelogioSimulado.UM_MINUTO_MS);
    render();
  });
  els.simAvancar1h.addEventListener("click", () => {
    RelogioSimulado.avancar(RelogioSimulado.UMA_HORA_MS);
    render();
  });
  els.simAvancar8h.addEventListener("click", () => {
    RelogioSimulado.avancar(8 * RelogioSimulado.UMA_HORA_MS);
    render();
  });
  els.simAvancar1d.addEventListener("click", () => {
    RelogioSimulado.avancar(RelogioSimulado.UM_DIA_MS);
    render();
  });
  els.simAplicarData.addEventListener("click", () => {
    const valor = els.simDataHora.value;
    if (!valor) {
      mostrarAviso("Informe uma data e hora antes de aplicar.");
      return;
    }
    const dataAlvo = new Date(valor);
    if (Number.isNaN(dataAlvo.getTime())) {
      mostrarAviso("Data/hora invalida.");
      return;
    }
    limparMensagem();
    RelogioSimulado.definir(dataAlvo);
    render();
  });
  els.simReiniciar.addEventListener("click", () => {
    RelogioSimulado.voltarParaTempoReal();
    render();
  });
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

configurarSimulador();
iniciar();
