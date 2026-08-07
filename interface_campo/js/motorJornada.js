// Motor de transicoes do Incremento 1, portado para JavaScript.
//
// Espelha fielmente src/workforce_core/engine.py (mesma ordem de
// validacao, mesmas excecoes) para que a interface de campo funcione
// 100% offline sem depender de nenhum backend. Qualquer alteracao de
// regra de negocio deve ser replicada nos dois lados ate existir uma
// unica fonte de verdade (ver docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

import {
  EstadoAtividade,
  EstadoEventoSecundario,
  EstadoJornada,
  EstadoPausa,
  ResultadoAtividade,
} from "./enums.js";
import * as Erros from "./erros.js";
import {
  novaAtividade,
  novaJornada,
  novaOrdemServico,
  novaPausa,
  novoDadosFalha,
  novoEventoSecundario,
  novoMembroEquipe,
} from "./entidades.js";

function validarOrdem(inicio, fim, rotulo) {
  if (fim.getTime() < inicio.getTime()) {
    throw new Erros.TimestampInvalidoError(
      `O timestamp de fim da ${rotulo} nao pode ser anterior ao inicio.`
    );
  }
}

// Mesma lista de src/workforce_core/engine.py::CAMPOS_OBRIGATORIOS_FALHA
// (revista no ADR-0021) - nota/ativo/sintoma/objeto/observacao.
const CAMPOS_OBRIGATORIOS_FALHA = ["nota", "ativo", "sintoma", "objeto", "observacao"];

function validarDadosFalhaCompletos(dados) {
  const faltantes = CAMPOS_OBRIGATORIOS_FALHA.filter((campo) => !dados[campo]);
  if (faltantes.length > 0) {
    throw new Erros.AtendimentoFalhaCamposObrigatoriosError(
      "Atendimento de falha nao pode ser encerrado sem: " + faltantes.join(", ") + "."
    );
  }
}

// Retrocompatibilidade com jornadas gravadas no IndexedDB antes de
// eventosSecundarios (ADR-0024) ou ordensServico (ADR-0025) existirem no
// formato - mesmo principio ja aplicado no lado Python
// (workforce_storage/serializacao.py, sempre `.get(..., [])`). Sem isso,
// reabrir o app com uma jornada antiga ja persistida no navegador quebra
// aPartirDe/identificarEstadoAtivo com "Cannot read properties of
// undefined (reading 'filter')" - bug real de producao encontrado em
// 2026-07-31 (usuario testando em um navegador com jornada previamente
// salva sem esses campos).
function normalizarCamposRetrocompativeis(jornada) {
  jornada.atividades = jornada.atividades ?? [];
  jornada.eventosSecundarios = jornada.eventosSecundarios ?? [];
  for (const atividade of jornada.atividades) {
    atividade.pausas = atividade.pausas ?? [];
    atividade.ordensServico = atividade.ordensServico ?? [];
    atividade.equipe = atividade.equipe ?? [];
  }
}

export function identificarEstadoAtivo(jornada) {
  normalizarCamposRetrocompativeis(jornada);
  const atividadesEmAndamento = jornada.atividades.filter(
    (a) => a.estado === EstadoAtividade.ATIVA || a.estado === EstadoAtividade.PAUSADA
  );
  if (atividadesEmAndamento.length > 1) {
    throw new Erros.EstadoInconsistenteError(
      "Mais de uma atividade principal ativa ou pausada na mesma jornada."
    );
  }
  const atividadeAtiva = atividadesEmAndamento[0] ?? null;

  let pausasAtivas = [];
  for (const atividade of jornada.atividades) {
    const encontradas = atividade.pausas.filter((p) => p.estado === EstadoPausa.ATIVA);
    if (encontradas.length > 0 && atividade !== atividadeAtiva) {
      throw new Erros.EstadoInconsistenteError(
        "Pausa ativa vinculada a uma atividade que nao e a atividade principal em andamento."
      );
    }
    pausasAtivas = pausasAtivas.concat(encontradas);
  }
  if (pausasAtivas.length > 1) {
    throw new Erros.EstadoInconsistenteError("Mais de uma pausa ativa na mesma jornada.");
  }
  const pausaAtiva = pausasAtivas[0] ?? null;

  if (pausaAtiva && (!atividadeAtiva || atividadeAtiva.estado !== EstadoAtividade.PAUSADA)) {
    throw new Erros.EstadoInconsistenteError(
      "Existe pausa ativa, mas a atividade vinculada nao esta com estado PAUSADA."
    );
  }
  if (atividadeAtiva && atividadeAtiva.estado === EstadoAtividade.PAUSADA && !pausaAtiva) {
    throw new Erros.EstadoInconsistenteError(
      "Atividade esta com estado PAUSADA, mas nao ha pausa ativa correspondente."
    );
  }

  const eventosAtivos = jornada.eventosSecundarios.filter(
    (e) => e.estado === EstadoEventoSecundario.ATIVA
  );
  if (eventosAtivos.length > 1) {
    throw new Erros.EstadoInconsistenteError(
      "Mais de um evento secundario (deslocamento/espera/apoio) ativo na mesma jornada."
    );
  }
  const eventoSecundarioAtivo = eventosAtivos[0] ?? null;

  if (eventoSecundarioAtivo && atividadeAtiva) {
    throw new Erros.EstadoInconsistenteError(
      "Evento secundario ativo simultaneamente com atividade principal ativa/pausada - " +
        "essas duas coisas sao mutuamente exclusivas."
    );
  }

  return { atividadeAtiva, pausaAtiva, eventoSecundarioAtivo };
}

export class MotorJornada {
  constructor({ colaboradorMatricula = null, jornada = null } = {}) {
    if (jornada) {
      this.jornada = jornada;
    } else {
      if (!colaboradorMatricula) {
        throw new TypeError("colaboradorMatricula e obrigatorio ao criar uma jornada nova.");
      }
      this.jornada = novaJornada({ colaboradorMatricula });
    }
    this._atividadeAtiva = null;
    this._pausaAtiva = null;
    this._eventoSecundarioAtivo = null;
  }

  static aPartirDe(jornada) {
    const { atividadeAtiva, pausaAtiva, eventoSecundarioAtivo } = identificarEstadoAtivo(jornada);
    const motor = new MotorJornada({ jornada });
    motor._atividadeAtiva = atividadeAtiva;
    motor._pausaAtiva = pausaAtiva;
    motor._eventoSecundarioAtivo = eventoSecundarioAtivo;
    return motor;
  }

  _garantirJornadaAberta() {
    if (this.jornada.estado !== EstadoJornada.ABERTA) {
      throw new Erros.JornadaNaoAbertaError("A operacao exige uma jornada aberta.");
    }
  }

  iniciarJornada(quando) {
    if (this.jornada.estado !== EstadoJornada.NAO_INICIADA) {
      throw new Erros.JornadaJaAbertaError(
        "Ja existe uma jornada iniciada para este colaborador."
      );
    }
    this.jornada.inicio = quando;
    this.jornada.estado = EstadoJornada.ABERTA;
    return this.jornada;
  }

  encerrarJornada(quando) {
    if (this.jornada.estado !== EstadoJornada.ABERTA) {
      throw new Erros.JornadaNaoAbertaError("Nao ha jornada aberta para encerrar.");
    }
    if (this._pausaAtiva) {
      throw new Erros.JornadaComPausaAbertaError(
        "Nao e permitido encerrar a jornada com pausa aberta."
      );
    }
    if (this._atividadeAtiva) {
      throw new Erros.JornadaComAtividadeAbertaError(
        "Nao e permitido encerrar a jornada com atividade aberta sem tratamento explicito."
      );
    }
    if (this._eventoSecundarioAtivo) {
      throw new Erros.JornadaComEventoSecundarioAbertoError(
        "Nao e permitido encerrar a jornada com deslocamento/espera/apoio aberto."
      );
    }
    validarOrdem(this.jornada.inicio, quando, "jornada");
    this.jornada.fim = quando;
    this.jornada.estado = EstadoJornada.ENCERRADA;
    return this.jornada;
  }

  iniciarAtividade(quando) {
    this._garantirJornadaAberta();
    if (this._atividadeAtiva) {
      throw new Erros.AtividadeJaAtivaError(
        "Ja existe uma atividade principal ativa para este colaborador."
      );
    }
    if (this._eventoSecundarioAtivo) {
      throw new Erros.AtividadeExigeNenhumEventoSecundarioAtivoError(
        "Nao e permitido iniciar atividade com deslocamento/espera/apoio em andamento."
      );
    }
    const atividade = novaAtividade({ inicio: quando });
    atividade.estado = EstadoAtividade.ATIVA;
    this.jornada.atividades.push(atividade);
    this._atividadeAtiva = atividade;
    return atividade;
  }

  _finalizarAtividade(quando, resultado) {
    this._garantirJornadaAberta();
    if (this._pausaAtiva) {
      throw new Erros.AtividadeEncerramentoComPausaAbertaError(
        "Nao e permitido encerrar a atividade com pausa aberta."
      );
    }
    if (!this._atividadeAtiva) {
      throw new Erros.AtividadeNaoAtivaError("Nao ha atividade ativa para encerrar.");
    }
    const atividade = this._atividadeAtiva;
    validarOrdem(atividade.inicio, quando, "atividade");
    if (atividade.dadosFalha) {
      validarDadosFalhaCompletos(atividade.dadosFalha);
    }
    atividade.fim = quando;
    atividade.estado = EstadoAtividade.ENCERRADA;
    atividade.resultado = resultado;
    this._atividadeAtiva = null;
    return atividade;
  }

  encerrarAtividade(quando) {
    return this._finalizarAtividade(quando, ResultadoAtividade.CONCLUIDA);
  }

  // "Atividade nao concluida" (EE23, ADR-0023/0025) - contraparte de
  // encerrarAtividade quando a manutencao programada nao termina no
  // turno. So se aplica a Atividade comum: atendimento de falha usa
  // transferirAtendimentoFalha para o desfecho equivalente.
  encerrarAtividadeNaoConcluida(quando) {
    if (this._atividadeAtiva && this._atividadeAtiva.dadosFalha) {
      throw new Erros.AtividadeNaoConcluidaExigeSemDadosFalhaError(
        "Atendimento de falha usa transferirAtendimentoFalha, nao encerrarAtividadeNaoConcluida."
      );
    }
    return this._finalizarAtividade(quando, ResultadoAtividade.NAO_CONCLUIDA);
  }

  // Ordens de servico associadas a Atividade comum (ADR-0025).
  adicionarOrdemServico(quando, numero) {
    this._garantirJornadaAberta();
    if (!this._atividadeAtiva) {
      throw new Erros.AtividadeNaoAtivaError("Nao ha atividade ativa para associar uma OS.");
    }
    if (this._atividadeAtiva.dadosFalha) {
      throw new Erros.OrdemServicoExigeAtividadeSemFalhaError(
        "OS so se associa a atividade comum, nao a atendimento de falha."
      );
    }
    if (!numero) {
      throw new Erros.OrdemServicoNumeroObrigatorioError("O numero da OS e obrigatorio.");
    }
    const ordem = novaOrdemServico({ numero, criadaEm: quando });
    this._atividadeAtiva.ordensServico.push(ordem);
    return ordem;
  }

  // Exclusao parcial de OS nao concluidas (ADR-0023): soft-delete, nunca
  // remove da lista - reenviar a mesma exclusao e idempotente.
  excluirOrdemServico(ordemId) {
    this._garantirJornadaAberta();
    if (!this._atividadeAtiva) {
      throw new Erros.AtividadeNaoAtivaError("Nao ha atividade ativa para excluir uma OS.");
    }
    const ordem = this._atividadeAtiva.ordensServico.find((o) => o.id === ordemId);
    if (!ordem) {
      throw new Erros.OrdemServicoNaoEncontradaError(`Nenhuma OS com id ${ordemId} na atividade ativa.`);
    }
    ordem.excluida = true;
    return ordem;
  }

  // Equipe (aba Equipe, pedido do responsavel pelo produto em 2026-08-07) -
  // mesmo espirito de adicionarOrdemServico/excluirOrdemServico, sem a
  // restricao de "so atividade comum" (equipe se aplica tambem a
  // atendimento de falha - quem esta presente independe de ser falha ou
  // atividade normal).
  adicionarMembroEquipe(quando, matricula) {
    this._garantirJornadaAberta();
    if (!this._atividadeAtiva) {
      throw new Erros.AtividadeNaoAtivaError("Nao ha atividade ativa para associar um membro de equipe.");
    }
    if (!matricula) {
      throw new Erros.MembroEquipeMatriculaObrigatoriaError("A matricula do membro de equipe e obrigatoria.");
    }
    const membro = novoMembroEquipe({ matricula, adicionadoEm: quando });
    this._atividadeAtiva.equipe.push(membro);
    return membro;
  }

  // Exclusao (soft-delete) de membro de equipe - reenviar a mesma exclusao
  // e idempotente, mesmo padrao de excluirOrdemServico.
  excluirMembroEquipe(membroId) {
    this._garantirJornadaAberta();
    if (!this._atividadeAtiva) {
      throw new Erros.AtividadeNaoAtivaError("Nao ha atividade ativa para excluir um membro de equipe.");
    }
    const membro = this._atividadeAtiva.equipe.find((m) => m.id === membroId);
    if (!membro) {
      throw new Erros.MembroEquipeNaoEncontradoError(`Nenhum membro de equipe com id ${membroId} na atividade ativa.`);
    }
    membro.excluida = true;
    return membro;
  }

  // Atendimento de falha (ADR-0021, espelhando
  // src/workforce_core/engine.py::iniciar_atendimento_falha).
  iniciarAtendimentoFalha(quando) {
    const atividade = this.iniciarAtividade(quando);
    atividade.dadosFalha = novoDadosFalha();
    return atividade;
  }

  // Atualizacao parcial - so sobrescreve o que for explicitamente
  // informado (mesmo padrao de registrar_dados_falha no Python).
  // gpsLatitude/gpsLongitude/gpsPrecisaoMetros/gpsCapturadoEm/fotoCaminho
  // sao best-effort (D2/D3) - nunca entram em CAMPOS_OBRIGATORIOS_FALHA.
  registrarDadosFalha({
    nota,
    ativo,
    sintoma,
    objeto,
    observacao,
    gpsLatitude,
    gpsLongitude,
    gpsPrecisaoMetros,
    gpsCapturadoEm,
    fotoCaminho,
  } = {}) {
    this._garantirJornadaAberta();
    if (!this._atividadeAtiva || !this._atividadeAtiva.dadosFalha) {
      throw new Erros.AtendimentoFalhaNaoAtivoError(
        "Nao ha atendimento de falha ativo para registrar dados."
      );
    }
    const dados = this._atividadeAtiva.dadosFalha;
    if (nota !== undefined) dados.nota = nota;
    if (ativo !== undefined) dados.ativo = ativo;
    if (sintoma !== undefined) dados.sintoma = sintoma;
    if (objeto !== undefined) dados.objeto = objeto;
    if (observacao !== undefined) dados.observacao = observacao;
    if (gpsLatitude !== undefined) dados.gpsLatitude = gpsLatitude;
    if (gpsLongitude !== undefined) dados.gpsLongitude = gpsLongitude;
    if (gpsPrecisaoMetros !== undefined) dados.gpsPrecisaoMetros = gpsPrecisaoMetros;
    if (gpsCapturadoEm !== undefined) dados.gpsCapturadoEm = gpsCapturadoEm;
    if (fotoCaminho !== undefined) dados.fotoCaminho = fotoCaminho;
    return dados;
  }

  // Transferencia de atendimento de falha ("Falha nao Concluida", D4) -
  // espelha src/workforce_core/engine.py::transferir_atendimento_falha.
  // Pula validarDadosFalhaCompletos de proposito: e o unico jeito de uma
  // atividade com dadosFalha terminar ENCERRADA incompleta.
  transferirAtendimentoFalha(quando) {
    this._garantirJornadaAberta();
    if (this._pausaAtiva) {
      throw new Erros.AtividadeEncerramentoComPausaAbertaError(
        "Nao e permitido encerrar a atividade com pausa aberta."
      );
    }
    if (!this._atividadeAtiva || !this._atividadeAtiva.dadosFalha) {
      throw new Erros.AtendimentoFalhaNaoAtivoError(
        "Nao ha atendimento de falha ativo para transferir."
      );
    }
    const atividade = this._atividadeAtiva;
    validarOrdem(atividade.inicio, quando, "atividade");
    atividade.fim = quando;
    atividade.estado = EstadoAtividade.ENCERRADA;
    this._atividadeAtiva = null;
    return atividade;
  }

  iniciarPausa(quando, motivo) {
    this._garantirJornadaAberta();
    if (!motivo) {
      throw new Erros.PausaMotivoObrigatorioError("O motivo da pausa e obrigatorio.");
    }
    if (this._pausaAtiva) {
      throw new Erros.PausaJaAtivaError("Ja existe uma pausa ativa para este colaborador.");
    }
    if (!this._atividadeAtiva || this._atividadeAtiva.estado !== EstadoAtividade.ATIVA) {
      throw new Erros.PausaExigeAtividadeAtivaError(
        "Pausa somente pode ser iniciada com atividade principal ativa."
      );
    }
    const atividade = this._atividadeAtiva;
    validarOrdem(atividade.inicio, quando, "pausa");
    const pausa = novaPausa({ atividadeId: atividade.id, motivo, inicio: quando });
    pausa.estado = EstadoPausa.ATIVA;
    atividade.pausas.push(pausa);
    atividade.estado = EstadoAtividade.PAUSADA;
    this._pausaAtiva = pausa;
    return pausa;
  }

  finalizarPausa(quando) {
    this._garantirJornadaAberta();
    if (!this._pausaAtiva) {
      throw new Erros.PausaNaoAtivaError("Nao ha pausa ativa para finalizar.");
    }
    const pausa = this._pausaAtiva;
    validarOrdem(pausa.inicio, quando, "pausa");
    pausa.fim = quando;
    pausa.estado = EstadoPausa.ENCERRADA;
    this._pausaAtiva = null;
    this._atividadeAtiva.estado = EstadoAtividade.ATIVA;
    return pausa;
  }

  // Deslocamento, espera ou apoio (ADR-0005) - espelha
  // src/workforce_core/engine.py::iniciar_evento_secundario /
  // encerrar_evento_secundario. Vinculado direto a Jornada, mutuamente
  // exclusivo com a Atividade principal (validado nos dois sentidos:
  // aqui e em iniciarAtividade).
  iniciarEventoSecundario(quando, tipo, motivo) {
    this._garantirJornadaAberta();
    if (!tipo) {
      throw new Erros.EventoSecundarioTipoObrigatorioError(
        "O tipo do evento secundario (DESLOCAMENTO/ESPERA/APOIO) e obrigatorio."
      );
    }
    if (!motivo) {
      throw new Erros.EventoSecundarioMotivoObrigatorioError(
        "O motivo do evento secundario e obrigatorio."
      );
    }
    if (this._eventoSecundarioAtivo) {
      throw new Erros.EventoSecundarioJaAtivoError(
        "Ja existe um deslocamento/espera/apoio ativo para este colaborador."
      );
    }
    if (this._atividadeAtiva) {
      throw new Erros.EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError(
        "Nao e permitido iniciar deslocamento/espera/apoio com atividade principal em andamento."
      );
    }
    const evento = novoEventoSecundario({ tipo, motivo, inicio: quando });
    evento.estado = EstadoEventoSecundario.ATIVA;
    this.jornada.eventosSecundarios.push(evento);
    this._eventoSecundarioAtivo = evento;
    return evento;
  }

  encerrarEventoSecundario(quando) {
    this._garantirJornadaAberta();
    if (!this._eventoSecundarioAtivo) {
      throw new Erros.EventoSecundarioNaoAtivoError(
        "Nao ha deslocamento/espera/apoio ativo para encerrar."
      );
    }
    const evento = this._eventoSecundarioAtivo;
    validarOrdem(evento.inicio, quando, "evento secundario");
    evento.fim = quando;
    evento.estado = EstadoEventoSecundario.ENCERRADA;
    this._eventoSecundarioAtivo = null;
    return evento;
  }
}
