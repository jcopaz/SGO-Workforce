// Motor de transicoes do Incremento 1, portado para JavaScript.
//
// Espelha fielmente src/workforce_core/engine.py (mesma ordem de
// validacao, mesmas excecoes) para que a interface de campo funcione
// 100% offline sem depender de nenhum backend. Qualquer alteracao de
// regra de negocio deve ser replicada nos dois lados ate existir uma
// unica fonte de verdade (ver docs/31_ADR_0004_INTERFACE_DE_CAMPO_PROVISORIA.md).

import { EstadoAtividade, EstadoJornada, EstadoPausa } from "./enums.js";
import * as Erros from "./erros.js";
import { novaAtividade, novaJornada, novaPausa, novoDadosFalha } from "./entidades.js";

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

export function identificarEstadoAtivo(jornada) {
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

  return { atividadeAtiva, pausaAtiva };
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
  }

  static aPartirDe(jornada) {
    const { atividadeAtiva, pausaAtiva } = identificarEstadoAtivo(jornada);
    const motor = new MotorJornada({ jornada });
    motor._atividadeAtiva = atividadeAtiva;
    motor._pausaAtiva = pausaAtiva;
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
    const atividade = novaAtividade({ inicio: quando });
    atividade.estado = EstadoAtividade.ATIVA;
    this.jornada.atividades.push(atividade);
    this._atividadeAtiva = atividade;
    return atividade;
  }

  encerrarAtividade(quando) {
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
    this._atividadeAtiva = null;
    return atividade;
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
  registrarDadosFalha({ nota, ativo, sintoma, objeto, observacao } = {}) {
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
    return dados;
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
}
