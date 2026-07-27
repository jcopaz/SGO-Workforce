// Motor de calculo de HH, portado de src/workforce_core/calculo.py
// (formulas em docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 7.4/7.5).

import * as Erros from "./erros.js";

export function duracaoPausa(pausa) {
  if (!pausa.inicio || !pausa.fim) {
    throw new Erros.TimestampInvalidoError(
      "Pausa sem inicio e fim definidos nao pode ser calculada."
    );
  }
  if (pausa.fim.getTime() < pausa.inicio.getTime()) {
    throw new Erros.TimestampInvalidoError("Pausa com fim anterior ao inicio.");
  }
  return pausa.fim.getTime() - pausa.inicio.getTime();
}

export function duracaoAtividadeBruta(atividade) {
  if (!atividade.inicio || !atividade.fim) {
    throw new Erros.TimestampInvalidoError(
      "Atividade sem inicio e fim definidos nao pode ser calculada."
    );
  }
  if (atividade.fim.getTime() < atividade.inicio.getTime()) {
    throw new Erros.TimestampInvalidoError("Atividade com fim anterior ao inicio.");
  }
  return atividade.fim.getTime() - atividade.inicio.getTime();
}

function validarPausaContida(pausa, atividade) {
  if (pausa.inicio.getTime() < atividade.inicio.getTime()) {
    throw new Erros.PausaForaDoIntervaloError(
      "Pausa iniciada antes do inicio da atividade a qual pertence."
    );
  }
  if (atividade.fim && pausa.fim && pausa.fim.getTime() > atividade.fim.getTime()) {
    throw new Erros.PausaForaDoIntervaloError(
      "Pausa encerrada depois do fim da atividade a qual pertence."
    );
  }
}

export function duracaoPausasAtividade(atividade) {
  let total = 0;
  for (const pausa of atividade.pausas) {
    validarPausaContida(pausa, atividade);
    total += duracaoPausa(pausa);
  }
  return total;
}

export function duracaoAtividadeLiquida(atividade) {
  return duracaoAtividadeBruta(atividade) - duracaoPausasAtividade(atividade);
}

export function duracaoEventoSecundario(evento) {
  if (!evento.inicio || !evento.fim) {
    throw new Erros.TimestampInvalidoError(
      "Evento secundario sem inicio e fim definidos nao pode ser calculado."
    );
  }
  if (evento.fim.getTime() < evento.inicio.getTime()) {
    throw new Erros.TimestampInvalidoError("Evento secundario com fim anterior ao inicio.");
  }
  return evento.fim.getTime() - evento.inicio.getTime();
}

export function duracaoEventosSecundarios(jornada) {
  let total = 0;
  for (const evento of jornada.eventosSecundarios) {
    total += duracaoEventoSecundario(evento);
  }
  return total;
}

export function duracaoJornadaBruta(jornada) {
  if (!jornada.inicio || !jornada.fim) {
    throw new Erros.TimestampInvalidoError(
      "Jornada sem inicio e fim definidos nao pode ser calculada."
    );
  }
  if (jornada.fim.getTime() < jornada.inicio.getTime()) {
    throw new Erros.TimestampInvalidoError("Jornada com fim anterior ao inicio.");
  }
  return jornada.fim.getTime() - jornada.inicio.getTime();
}

export function tempoClassificadoJornada(jornada) {
  let total = 0;
  for (const atividade of jornada.atividades) {
    total += duracaoAtividadeLiquida(atividade);
    total += duracaoPausasAtividade(atividade);
  }
  total += duracaoEventosSecundarios(jornada);
  return total;
}

export function tempoNaoClassificado(jornada) {
  return duracaoJornadaBruta(jornada) - tempoClassificadoJornada(jornada);
}

export function resumoEventoSecundario(evento) {
  return {
    id: evento.id,
    tipo: evento.tipo,
    motivo: evento.motivo,
    duracao: duracaoEventoSecundario(evento),
  };
}

export function resumoJornada(jornada) {
  return {
    jornadaBruta: duracaoJornadaBruta(jornada),
    tempoClassificado: tempoClassificadoJornada(jornada),
    tempoNaoClassificado: tempoNaoClassificado(jornada),
    atividades: jornada.atividades.map((atividade) => ({
      id: atividade.id,
      bruta: duracaoAtividadeBruta(atividade),
      pausas: duracaoPausasAtividade(atividade),
      liquida: duracaoAtividadeLiquida(atividade),
    })),
    eventosSecundarios: jornada.eventosSecundarios.map(resumoEventoSecundario),
  };
}

// Formatacao "HHhMM" para exibicao. Nunca usada como fonte de calculo -
// apenas apresenta um valor de milissegundos ja calculado a partir de
// timestamps persistidos (regra de ouro: nao calcular duracao pelo
// relogio visual do cliente).
export function formatarDuracao(ms) {
  const sinal = ms < 0 ? "-" : "";
  const totalMinutos = Math.round(Math.abs(ms) / 60000);
  const horas = Math.floor(totalMinutos / 60);
  const minutos = totalMinutos % 60;
  return `${sinal}${horas}h${String(minutos).padStart(2, "0")}`;
}
