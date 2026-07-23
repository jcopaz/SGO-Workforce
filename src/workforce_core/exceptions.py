"""Excecoes do motor de dominio.

Cada excecao corresponde a uma regra inegociavel ou restricao de estado
descrita em docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md (secoes 3.3 e 8).
"""


class ErroDominio(Exception):
    """Base para todas as excecoes do motor de dominio do SGO Workforce."""


class JornadaJaAbertaError(ErroDominio):
    """Tentativa de iniciar uma jornada quando ja existe uma jornada aberta ou encerrada."""


class JornadaNaoAbertaError(ErroDominio):
    """Operacao exige uma jornada aberta, mas nao ha jornada aberta."""


class JornadaComPausaAbertaError(ErroDominio):
    """Nao e permitido encerrar a jornada enquanto houver pausa ativa."""


class JornadaComAtividadeAbertaError(ErroDominio):
    """Nao e permitido encerrar a jornada silenciosamente com atividade ativa."""


class AtividadeJaAtivaError(ErroDominio):
    """Nao e permitido iniciar uma segunda atividade principal."""


class AtividadeNaoAtivaError(ErroDominio):
    """Operacao exige uma atividade ativa, mas nao ha atividade ativa."""


class AtividadeEncerramentoComPausaAbertaError(ErroDominio):
    """Nao e permitido encerrar a atividade enquanto houver pausa ativa."""


class PausaJaAtivaError(ErroDominio):
    """Nao e permitido iniciar uma segunda pausa."""


class PausaNaoAtivaError(ErroDominio):
    """Operacao exige uma pausa ativa, mas nao ha pausa ativa."""


class PausaExigeAtividadeAtivaError(ErroDominio):
    """No Incremento 1, pausa somente e permitida com atividade principal ativa."""


class PausaMotivoObrigatorioError(ErroDominio):
    """O motivo da pausa e obrigatorio."""


class PausaForaDoIntervaloError(ErroDominio):
    """A pausa deve estar contida no intervalo bruto da atividade a qual pertence."""


class TimestampInvalidoError(ErroDominio):
    """O timestamp de fim nao pode ser anterior ao timestamp de inicio correspondente."""


class EstadoInconsistenteError(ErroDominio):
    """Um conjunto de entidades persistidas viola as invariantes do dominio.

    Exemplos: mais de uma atividade principal ativa/pausada na mesma jornada,
    mais de uma pausa ativa, ou pausa ativa vinculada a uma atividade que nao
    esta com estado PAUSADA. Levantada ao reconstruir um MotorJornada a partir
    de dados persistidos (ver MotorJornada.a_partir_de).
    """


class EventoSecundarioJaAtivoError(ErroDominio):
    """Nao e permitido iniciar um segundo deslocamento/espera/apoio simultaneo."""


class EventoSecundarioNaoAtivoError(ErroDominio):
    """Operacao exige um evento secundario ativo, mas nao ha nenhum."""


class EventoSecundarioTipoObrigatorioError(ErroDominio):
    """O tipo do evento secundario (DESLOCAMENTO/ESPERA/APOIO) e obrigatorio."""


class EventoSecundarioMotivoObrigatorioError(ErroDominio):
    """O motivo do evento secundario e obrigatorio."""


class EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError(ErroDominio):
    """Deslocamento/espera/apoio e mutuamente exclusivo com a atividade principal.

    Reflete a regra "apenas um evento principal ativo" de
    docs/07_MOTOR_EVENTOS_E_HH.md: dentro de uma jornada aberta, so pode
    haver uma "coisa" em andamento por vez - a atividade principal (com ou
    sem pausa) ou um evento secundario, nunca as duas.
    """


class AtividadeExigeNenhumEventoSecundarioAtivoError(ErroDominio):
    """Nao e permitido iniciar atividade com deslocamento/espera/apoio em andamento."""


class JornadaComEventoSecundarioAbertoError(ErroDominio):
    """Nao e permitido encerrar a jornada com deslocamento/espera/apoio aberto."""


class AtendimentoFalhaNaoAtivoError(ErroDominio):
    """Operacao exige um atendimento de falha ativo, mas a atividade ativa nao e uma."""


class AtendimentoFalhaCamposObrigatoriosError(ErroDominio):
    """Um atendimento de falha nao pode ser encerrado sem nota, ativo, sintoma,
    causa, acao e observacao tecnica.

    Regra inegociavel de docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md,
    secao 3.5.
    """
