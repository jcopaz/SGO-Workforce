// Interface operacional simples para celular (Incremento 4).
//
// Piloto tecnico: apenas Jornada + Atividade + Pausa, sem autenticacao,
// sem GPS, sem RASF. Sincronizacao com o backend real existe (ver
// sincronizacao.js e docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md)
// mas e best-effort: uma falha de rede nunca impede o registro local do
// evento (offline-first). Catalogo de motivos de pausa buscado
// dinamicamente do backend (ver catalogoMotivos.js e
// docs/46_ADR_0019_CATALOGO_DINAMICO.md).

import { MotorJornada } from "./motorJornada.js";
import * as calculo from "./calculo.js";
import * as Erros from "./erros.js";
import { carregarJornada, listarJornadasAbertas, salvarJornada } from "./armazenamento.js";
import * as RelogioSimulado from "./relogioSimulado.js";
import * as Sincronizacao from "./sincronizacao.js";
import * as CatalogoMotivos from "./catalogoMotivos.js";
import * as CatalogoRasf from "./catalogoRasf.js";
import * as Geolocalizacao from "./geolocalizacao.js";
import * as FotoFalha from "./fotoFalha.js";
import * as ContinuacoesFalha from "./continuacoesFalha.js";

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
// Motivos de pausa (catalogo dinamico) - populado em iniciar() antes do
// primeiro render(). Nunca fica vazio: catalogoMotivos.js sempre devolve
// pelo menos a lista minima embutida como ultimo recurso offline.
let motivosPausa = [];
// Deslocamento/espera/apoio (catalogo dinamico, incremento de Evento
// Secundario na interface de campo) - mesmo padrao de motivosPausa.
let eventosSecundarios = [];
// Catalogo RASF (sintomas/componentes causadores) para o formulario de
// atendimento de falha - mesmo padrao de motivosPausa (populado em
// iniciar(), nunca fica vazio).
let catalogoRasf = { sintomas: [], componentes_causadores: [] };
// Controla a exibicao do formulario inline de transferencia ("Falha nao
// Concluida", D4) - resetado sempre que uma nova atividade comeca (ver
// os botoes "Iniciar atividade"/"Iniciar atendimento de falha"/"Iniciar
// nova jornada" abaixo), para nunca vazar entre atendimentos diferentes.
let mostrarTransferenciaFalha = false;

function criarSeletorMotivoPausa() {
  const select = document.createElement("select");
  select.id = "motivoPausa";
  select.className = "seletor-motivo";
  for (const motivo of motivosPausa) {
    const opcao = document.createElement("option");
    opcao.value = motivo.codigo;
    opcao.textContent = `${motivo.codigo} - ${motivo.descricao}`;
    select.appendChild(opcao);
  }
  return select;
}

// Valores sentinela (nunca colidem com um codigo EE real, que e sempre
// "EE" + 2 digitos) para as duas opcoes especiais da lista unica de
// acoes abaixo.
const VALOR_INICIAR_ATIVIDADE = "__ATIVIDADE__";
const VALOR_ATENDIMENTO_FALHA = "__FALHA__";

// Lista unica de acoes da tela "jornada aberta, sem nada em andamento"
// (ADR-0030, pedido do responsavel do produto): antes eram 2 botoes
// separados (Iniciar atividade / Iniciar atendimento de falha) mais um
// terceiro seletor+botao so para deslocamento/espera/apoio - agora e uma
// lista so, com um unico botao "Iniciar" embaixo dela (ver render()).
// Combina motivosPausa (os 5 codigos que ADR-0030 tornou tambem
// iniciaveis soltos, sem atividade ativa - EE02/EE07/EE11/EE20/EE22) com
// eventosSecundarios (os 15 codigos de deslocamento/espera/apoio,
// ADR-0005/0024), ordenados por codigo (mesma ordem do formulario em
// papel). "Iniciar atividade" e "Atendimento de falha" ficam num grupo
// separado, sempre no topo, porque abrem um formulario proprio em vez de
// simplesmente comecar a contar tempo (ver o tratamento do valor
// sentinela em render()).
function criarSeletorAcaoPrincipal() {
  const select = document.createElement("select");
  select.id = "acaoPrincipal";
  select.className = "seletor-motivo";

  const grupoPrincipal = document.createElement("optgroup");
  grupoPrincipal.label = "Ação principal";
  const opcaoAtividade = document.createElement("option");
  opcaoAtividade.value = VALOR_INICIAR_ATIVIDADE;
  opcaoAtividade.textContent = "Iniciar atividade";
  const opcaoFalha = document.createElement("option");
  opcaoFalha.value = VALOR_ATENDIMENTO_FALHA;
  opcaoFalha.textContent = "Atendimento de falha";
  grupoPrincipal.append(opcaoAtividade, opcaoFalha);
  select.appendChild(grupoPrincipal);

  const grupoPausaApoio = document.createElement("optgroup");
  grupoPausaApoio.label = "Pausa, deslocamento e apoio";
  const opcoesPausaApoio = [...motivosPausa, ...eventosSecundarios].sort((a, b) =>
    a.codigo.localeCompare(b.codigo)
  );
  for (const motivo of opcoesPausaApoio) {
    const opcao = document.createElement("option");
    opcao.value = motivo.codigo;
    opcao.textContent = `${motivo.codigo} - ${motivo.descricao}`;
    grupoPausaApoio.appendChild(opcao);
  }
  select.appendChild(grupoPausaApoio);

  return select;
}

// Busca o tipo em ambas as listas (ADR-0030 fez motivosPausa tambem ter
// codigos com tipo_evento_secundario - EE02/EE07/EE11/EE20/EE22).
function tipoEventoSecundarioParaCodigo(codigo) {
  const encontrado =
    eventosSecundarios.find((evento) => evento.codigo === codigo) ??
    motivosPausa.find((motivo) => motivo.codigo === codigo);
  return encontrado?.tipo_evento_secundario;
}

// Descricao legivel de um codigo (para o status "X em andamento." -
// ADR-0030: como o evento secundario agora tambem cobre pausas avulsas,
// nao da mais pra usar um texto fixo tipo "Deslocamento/espera/apoio em
// andamento." para todos os casos).
function descricaoParaCodigo(codigo) {
  const encontrado =
    eventosSecundarios.find((evento) => evento.codigo === codigo) ??
    motivosPausa.find((motivo) => motivo.codigo === codigo);
  return encontrado?.descricao;
}

// Campos do formulario de atendimento de falha (ADR-0021). Cada um
// inicializa com o valor ja persistido (dados_falha.<campo>) para um
// re-render nao perder o que ja foi salvo, e so grava (executar ->
// registrarDadosFalha) quando o campo perde o foco/muda - nunca a cada
// tecla, para nao disparar um render completo a cada digito.
function criarCampoTexto(rotulo, valorAtual, aoSalvar) {
  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = rotulo;
  const input = document.createElement("input");
  input.type = "text";
  input.value = valorAtual || "";
  input.addEventListener("blur", () => aoSalvar(input.value.trim()));
  label.append(span, input);
  return label;
}

function criarCampoTextarea(rotulo, valorAtual, aoSalvar) {
  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = rotulo;
  const textarea = document.createElement("textarea");
  textarea.rows = 3;
  textarea.value = valorAtual || "";
  textarea.addEventListener("blur", () => aoSalvar(textarea.value.trim()));
  label.append(span, textarea);
  return label;
}

function criarCampoSelecao(rotulo, opcoes, valorAtual, aoSalvar) {
  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = rotulo;
  const select = document.createElement("select");
  select.className = "seletor-motivo";
  const opcaoVazia = document.createElement("option");
  opcaoVazia.value = "";
  opcaoVazia.textContent = "Selecione...";
  select.appendChild(opcaoVazia);
  for (const valor of opcoes) {
    const opcao = document.createElement("option");
    opcao.value = valor;
    opcao.textContent = valor;
    select.appendChild(opcao);
  }
  select.value = valorAtual || "";
  select.addEventListener("change", () => aoSalvar(select.value));
  label.append(span, select);
  return label;
}

// Formulario completo, anexado a els.botoes quando ha um atendimento de
// falha em andamento (atividade.dadosFalha existe). O aviso persistente
// fica visivel enquanto essa tela estiver aberta - nao e um toast que
// some sozinho.
function renderFormularioAtendimentoFalha(atividade) {
  const dados = atividade.dadosFalha;

  const aviso = document.createElement("p");
  aviso.className = "aviso-piloto";
  aviso.textContent =
    "Atendimento de falha em andamento: a atividade só pode ser encerrada depois de preencher nota, ativo, sintoma, objeto e observações/causa.";
  els.botoes.appendChild(aviso);

  els.botoes.appendChild(
    criarCampoTexto("Número da nota de atendimento", dados.nota, (valor) =>
      executar(() => motor.registrarDadosFalha({ nota: valor }))
    )
  );
  els.botoes.appendChild(
    criarCampoTexto("Identificação do ativo", dados.ativo, (valor) =>
      executar(() => motor.registrarDadosFalha({ ativo: valor }))
    )
  );
  els.botoes.appendChild(
    criarCampoSelecao("Sintoma", catalogoRasf.sintomas, dados.sintoma, (valor) =>
      executar(() => motor.registrarDadosFalha({ sintoma: valor }))
    )
  );
  els.botoes.appendChild(
    criarCampoSelecao(
      "Objeto (componente causador)",
      catalogoRasf.componentes_causadores,
      dados.objeto,
      (valor) => executar(() => motor.registrarDadosFalha({ objeto: valor }))
    )
  );
  els.botoes.appendChild(
    criarCampoTextarea("Observações/Causa", dados.observacao, (valor) =>
      executar(() => motor.registrarDadosFalha({ observacao: valor }))
    )
  );

  els.botoes.appendChild(criarBlocoLocalizacao(dados));
  els.botoes.appendChild(criarBlocoFoto(dados));
}

// GPS best-effort (D2): nunca bloqueia nada, so registra se a captura der
// certo. Acao explicita do colaborador (botao), nao automatica - assim o
// prompt de permissao do navegador so aparece quando ele sabe por que.
function textoStatusLocalizacao(dados) {
  if (dados.gpsLatitude == null || dados.gpsLongitude == null) {
    return "Localização não capturada (opcional).";
  }
  const precisao =
    dados.gpsPrecisaoMetros != null ? ` (±${Math.round(dados.gpsPrecisaoMetros)}m)` : "";
  return `Localização capturada às ${formatoHora(dados.gpsCapturadoEm)}${precisao}.`;
}

function criarBlocoLocalizacao(dados) {
  const bloco = document.createElement("div");
  bloco.className = "bloco-localizacao";

  const status = document.createElement("p");
  status.className = "status-localizacao";
  status.textContent = textoStatusLocalizacao(dados);
  bloco.appendChild(status);

  bloco.appendChild(
    botao("Capturar localização", async () => {
      limparMensagem();
      const posicao = await Geolocalizacao.capturarPosicaoAtual();
      if (!posicao) {
        mostrarAviso(
          "Não foi possível capturar a localização agora (sinal fraco ou permissão negada) - isso não impede concluir o atendimento."
        );
        return;
      }
      await executar(() =>
        motor.registrarDadosFalha({
          gpsLatitude: posicao.latitude,
          gpsLongitude: posicao.longitude,
          gpsPrecisaoMetros: posicao.precisaoMetros,
          gpsCapturadoEm: posicao.capturadoEm,
        })
      );
      mostrarAviso(`Localização capturada às ${formatoHora(posicao.capturadoEm)}.`);
    })
  );

  return bloco;
}

// Foto best-effort (D3): nunca bloqueia nada, so registra fotoCaminho se
// o envio ao backend (que repassa ao Supabase Storage) der certo.
function textoStatusFoto(dados) {
  return dados.fotoCaminho ? "Foto enviada." : "Nenhuma foto enviada (opcional).";
}

function criarBlocoFoto(dados) {
  const bloco = document.createElement("div");
  bloco.className = "bloco-foto";

  const status = document.createElement("p");
  status.className = "status-foto";
  status.textContent = textoStatusFoto(dados);
  bloco.appendChild(status);

  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = "Foto do atendimento";
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.capture = "environment";
  input.addEventListener("change", async () => {
    const arquivo = input.files[0];
    if (!arquivo) return;
    limparMensagem();
    mostrarAviso("Enviando foto...");
    const resultado = await FotoFalha.enviarFoto(arquivo);
    if (!resultado.ok) {
      mostrarAviso(`${resultado.mensagem} Isso não impede concluir o atendimento.`);
      return;
    }
    await executar(() => motor.registrarDadosFalha({ fotoCaminho: resultado.caminho }));
    mostrarAviso("Foto enviada.");
  });
  label.append(span, input);
  bloco.appendChild(label);

  return bloco;
}

// Formulario inline de transferencia ("Falha nao Concluida", D4): pede a
// matricula de destino sem usar prompt() do navegador (mesmo padrao dos
// outros campos da tela). Confirmar encerra a atividade localmente
// (transferirAtendimentoFalha, nunca exige campos completos) e so depois
// avisa o backend, best-effort - a transferencia local nunca depende de
// rede.
function criarFormularioTransferenciaFalha(atividade) {
  const bloco = document.createElement("div");
  bloco.className = "bloco-transferencia-falha";

  const aviso = document.createElement("p");
  aviso.className = "aviso-piloto";
  aviso.textContent =
    "Informe a matrícula de quem vai continuar este atendimento. Os dados já preenchidos serão levados para ela.";
  bloco.appendChild(aviso);

  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = "Matrícula de destino";
  const input = document.createElement("input");
  input.type = "text";
  label.append(span, input);
  bloco.appendChild(label);

  bloco.appendChild(
    botao(
      "Confirmar transferência",
      async () => {
        const matriculaDestino = input.value.trim();
        if (!matriculaDestino) {
          mostrarAviso("Informe a matrícula de destino antes de confirmar.");
          return;
        }
        const dadosFalhaAtual = atividade.dadosFalha;
        mostrarTransferenciaFalha = false;
        await executar(() => motor.transferirAtendimentoFalha(RelogioSimulado.agora()));
        const resultado = await ContinuacoesFalha.criarContinuacao(dadosFalhaAtual, matriculaDestino);
        if (resultado.ok) {
          mostrarAviso(`Atendimento transferido para a matrícula ${matriculaDestino}.`);
        } else {
          mostrarAviso(
            `Atendimento encerrado aqui, mas ${resultado.mensagem.toLowerCase()} Avise ${matriculaDestino} manualmente.`
          );
        }
      },
      { destaque: true }
    )
  );
  bloco.appendChild(
    botao("Cancelar", () => {
      mostrarTransferenciaFalha = false;
      render();
    })
  );

  return bloco;
}

// Bloco de OS (ADR-0025) - texto livre, múltiplas OS por atividade,
// exclusão individual soft-delete (a OS some da lista visível mas nunca é
// removida do registro, ver motorJornada.js::excluirOrdemServico).
function criarBlocoOrdensServico(atividade) {
  const bloco = document.createElement("div");
  bloco.className = "bloco-ordens-servico";

  const ativas = atividade.ordensServico.filter((ordem) => !ordem.excluida);
  if (ativas.length > 0) {
    const lista = document.createElement("ul");
    lista.className = "lista-ordens-servico";
    for (const ordem of ativas) {
      const item = document.createElement("li");
      const texto = document.createElement("span");
      texto.textContent = ordem.numero;
      item.appendChild(texto);
      item.appendChild(
        botao("Excluir", () => executar(() => motor.excluirOrdemServico(ordem.id)))
      );
      lista.appendChild(item);
    }
    bloco.appendChild(lista);
  }

  const label = document.createElement("label");
  label.className = "campo";
  const span = document.createElement("span");
  span.textContent = "Número da OS";
  const input = document.createElement("input");
  input.type = "text";
  label.append(span, input);
  bloco.appendChild(label);

  bloco.appendChild(
    botao("Adicionar OS", () => {
      const numero = input.value.trim();
      if (!numero) {
        mostrarAviso("Informe o número da OS antes de adicionar.");
        return;
      }
      executar(() => motor.adicionarOrdemServico(RelogioSimulado.agora(), numero));
    })
  );

  return bloco;
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

// Formato dd/mm/aaaa hh:mm:ss, mesmo padrao adotado no painel
// (painel/dados.py::formatar_data_hora) - construido manualmente (nao
// toLocaleString) para o formato nao variar entre navegadores/locales.
// Mostrar a data completa (nao so a hora) importa desde que o simulador
// de tempo permite testar jornadas que atravessam dias (ADR-0016).
function formatoHora(data) {
  if (!data) return "--";
  const dois = (n) => String(n).padStart(2, "0");
  const dataStr = `${dois(data.getDate())}/${dois(data.getMonth() + 1)}/${data.getFullYear()}`;
  const horaStr = `${dois(data.getHours())}:${dois(data.getMinutes())}:${dois(data.getSeconds())}`;
  return `${dataStr} ${horaStr}`;
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
  const eventoSecundario = motor._eventoSecundarioAtivo;
  if (eventoSecundario) {
    const decorridoEvento = calculo.formatarDuracao(agora.getTime() - eventoSecundario.inicio.getTime());
    partes.push(
      `Evento iniciado as ${formatoHora(eventoSecundario.inicio)} (motivo: ${eventoSecundario.motivo}, decorrido: ${decorridoEvento})`
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
        async () => {
          if (!prepararMotorComMatricula()) return;
          const matricula = motor.jornada.colaboradorMatricula;
          const pendente = await ContinuacoesFalha.buscarPendente(matricula);
          if (pendente) {
            await executar(() => {
              motor.iniciarJornada(RelogioSimulado.agora());
              motor.iniciarAtendimentoFalha(RelogioSimulado.agora());
              motor.registrarDadosFalha(pendente.dados);
            });
            mostrarAviso(
              "Havia um atendimento de falha em aberto para você - retomado automaticamente com os dados já preenchidos."
            );
            ContinuacoesFalha.marcarConsumida(pendente.id);
          } else {
            executar(() => motor.iniciarJornada(RelogioSimulado.agora()));
          }
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
    // "Sincronizar agora" so aparece aqui (jornada encerrada) - pedido do
    // responsavel do produto em 2026-07-31: durante a jornada em
    // andamento o app ja sincroniza sozinho apos cada transicao
    // (persistir() -> dispararSincronizacao(), best-effort), o botao
    // manual so faz sentido como conferencia final antes de fechar o app.
    els.botoes.appendChild(botao("Sincronizar agora", () => dispararSincronizacao()));
    els.botoes.appendChild(
      botao(
        "Iniciar nova jornada",
        () => {
          motor = null;
          mostrarTransferenciaFalha = false;
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
  const eventoSecundario = motor._eventoSecundarioAtivo;

  if (pausa) {
    els.status.textContent = "Em pausa.";
    els.botoes.appendChild(
      botao("Finalizar pausa", () => executar(() => motor.finalizarPausa(RelogioSimulado.agora())), {
        destaque: true,
      })
    );
  } else if (atividade) {
    if (atividade.dadosFalha) {
      els.status.textContent = "Atendimento de falha em andamento.";
      renderFormularioAtendimentoFalha(atividade);
    } else {
      els.status.textContent = "Atividade em andamento.";
      els.botoes.appendChild(criarBlocoOrdensServico(atividade));
    }
    const seletorMotivo = criarSeletorMotivoPausa();
    els.botoes.appendChild(seletorMotivo);
    els.botoes.appendChild(
      botao("Iniciar pausa", () =>
        executar(() => motor.iniciarPausa(RelogioSimulado.agora(), seletorMotivo.value))
      )
    );
    if (atividade.dadosFalha) {
      els.botoes.appendChild(
        botao(
          "Concluir atendimento",
          () => executar(() => motor.encerrarAtividade(RelogioSimulado.agora())),
          { destaque: true }
        )
      );
    } else {
      // Dois desfechos de encerramento (ADR-0023/0025): "Concluir
      // atividade" grava EE17 (resultado CONCLUIDA), "Atividade não
      // concluída" grava EE23 (resultado NAO_CONCLUIDA) - as OS já
      // adicionadas continuam na lista nos dois casos.
      els.botoes.appendChild(
        botao(
          "Concluir atividade",
          () => executar(() => motor.encerrarAtividade(RelogioSimulado.agora())),
          { destaque: true }
        )
      );
      els.botoes.appendChild(
        botao("Atividade não concluída", () =>
          executar(() => motor.encerrarAtividadeNaoConcluida(RelogioSimulado.agora()))
        )
      );
    }
    if (atividade.dadosFalha) {
      if (mostrarTransferenciaFalha) {
        els.botoes.appendChild(criarFormularioTransferenciaFalha(atividade));
      } else {
        els.botoes.appendChild(
          botao("Falha não concluída", () => {
            mostrarTransferenciaFalha = true;
            render();
          })
        );
      }
    }
  } else if (eventoSecundario) {
    const descricaoEvento = descricaoParaCodigo(eventoSecundario.motivo) ?? "Evento";
    els.status.textContent = `${descricaoEvento} em andamento.`;
    els.botoes.appendChild(
      botao(
        "Encerrar evento",
        () => executar(() => motor.encerrarEventoSecundario(RelogioSimulado.agora())),
        { destaque: true }
      )
    );
  } else {
    els.status.textContent = "Jornada aberta, sem atividade em andamento.";
    const seletorAcao = criarSeletorAcaoPrincipal();
    els.botoes.appendChild(seletorAcao);
    els.botoes.appendChild(
      botao(
        "Iniciar",
        () => {
          const valor = seletorAcao.value;
          mostrarTransferenciaFalha = false;
          if (valor === VALOR_INICIAR_ATIVIDADE) {
            executar(() => motor.iniciarAtividade(RelogioSimulado.agora()));
          } else if (valor === VALOR_ATENDIMENTO_FALHA) {
            executar(() => motor.iniciarAtendimentoFalha(RelogioSimulado.agora()));
          } else {
            const tipo = tipoEventoSecundarioParaCodigo(valor);
            executar(() => motor.iniciarEventoSecundario(RelogioSimulado.agora(), tipo, valor));
          }
        },
        { destaque: true }
      )
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
  const [abertas, motivos, eventos, rasf] = await Promise.all([
    listarJornadasAbertas(),
    CatalogoMotivos.obterMotivosPausa(),
    CatalogoMotivos.obterEventosSecundarios(),
    CatalogoRasf.obterCatalogoRasf(),
  ]);
  motivosPausa = motivos;
  eventosSecundarios = eventos;
  catalogoRasf = rasf;
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
