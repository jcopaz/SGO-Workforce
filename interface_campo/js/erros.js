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
export class EventoSecundarioJaAtivoError extends ErroDominio {}
export class EventoSecundarioNaoAtivoError extends ErroDominio {}
export class EventoSecundarioTipoObrigatorioError extends ErroDominio {}
export class EventoSecundarioMotivoObrigatorioError extends ErroDominio {}
export class EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError extends ErroDominio {}
export class AtividadeExigeNenhumEventoSecundarioAtivoError extends ErroDominio {}
export class JornadaComEventoSecundarioAbertoError extends ErroDominio {}
export class OrdemServicoNumeroObrigatorioError extends ErroDominio {}
export class OrdemServicoExigeAtividadeSemFalhaError extends ErroDominio {}
export class OrdemServicoNaoEncontradaError extends ErroDominio {}
export class AtividadeNaoConcluidaExigeSemDadosFalhaError extends ErroDominio {}
