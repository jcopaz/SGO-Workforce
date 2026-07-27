// Excecoes do motor de dominio, espelhando src/workforce_core/exceptions.py

export class ErroDominio extends Error {
  constructor(mensagem) {
    super(mensagem);
    this.name = this.constructor.name;
  }
}

export class JornadaJaAbertaError extends ErroDominio {}
export class JornadaNaoAbertaError extends ErroDominio {}
export class JornadaComPausaAbertaError extends ErroDominio {}
export class JornadaComAtividadeAbertaError extends ErroDominio {}
export class AtividadeJaAtivaError extends ErroDominio {}
export class AtividadeNaoAtivaError extends ErroDominio {}
export class AtividadeEncerramentoComPausaAbertaError extends ErroDominio {}
export class PausaJaAtivaError extends ErroDominio {}
export class PausaNaoAtivaError extends ErroDominio {}
export class PausaExigeAtividadeAtivaError extends ErroDominio {}
export class PausaMotivoObrigatorioError extends ErroDominio {}
export class PausaForaDoIntervaloError extends ErroDominio {}
export class TimestampInvalidoError extends ErroDominio {}
export class EstadoInconsistenteError extends ErroDominio {}
export class AtendimentoFalhaNaoAtivoError extends ErroDominio {}
export class AtendimentoFalhaCamposObrigatoriosError extends ErroDominio {}
