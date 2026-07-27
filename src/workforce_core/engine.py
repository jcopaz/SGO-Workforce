"""Motor de transicoes do Incremento 1.

Uma instancia de MotorJornada controla o ciclo de vida de uma unica jornada
de um colaborador: inicio/fim de jornada, inicio/fim de atividade principal
e inicio/fim de pausa, aplicando as restricoes da secao 8 do alinhamento
oficial (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md).

Uma transicao repetida (ex.: encerrar a jornada duas vezes) e sempre
bloqueada com a mesma excecao, nunca corrompe o estado interno - isso
cobre a exigencia de resiliencia a duplicidade de comando (secao 9.13).
"""

from __future__ import annotations

from datetime import datetime

from .entities import Atividade, DadosFalha, EventoSecundario, Jornada, OrdemServico, Pausa
from .enums import (
    EstadoAtividade,
    EstadoEventoSecundario,
    EstadoJornada,
    EstadoPausa,
    ResultadoAtividade,
    TipoEventoSecundario,
)
from .exceptions import (
    AtendimentoFalhaCamposObrigatoriosError,
    AtendimentoFalhaNaoAtivoError,
    AtividadeEncerramentoComPausaAbertaError,
    AtividadeExigeNenhumEventoSecundarioAtivoError,
    AtividadeJaAtivaError,
    AtividadeNaoAtivaError,
    AtividadeNaoConcluidaExigeSemDadosFalhaError,
    EstadoInconsistenteError,
    EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError,
    EventoSecundarioJaAtivoError,
    EventoSecundarioMotivoObrigatorioError,
    EventoSecundarioNaoAtivoError,
    EventoSecundarioTipoObrigatorioError,
    JornadaComAtividadeAbertaError,
    JornadaComEventoSecundarioAbertoError,
    JornadaComPausaAbertaError,
    JornadaJaAbertaError,
    JornadaNaoAbertaError,
    OrdemServicoExigeAtividadeSemFalhaError,
    OrdemServicoNaoEncontradaError,
    OrdemServicoNumeroObrigatorioError,
    PausaExigeAtividadeAtivaError,
    PausaJaAtivaError,
    PausaMotivoObrigatorioError,
    PausaNaoAtivaError,
    TimestampInvalidoError,
)

CAMPOS_OBRIGATORIOS_FALHA = ("nota", "ativo", "sintoma", "objeto", "observacao")


def _validar_dados_falha_completos(dados: DadosFalha) -> None:
    faltantes = [campo for campo in CAMPOS_OBRIGATORIOS_FALHA if not getattr(dados, campo)]
    if faltantes:
        raise AtendimentoFalhaCamposObrigatoriosError(
            "Atendimento de falha nao pode ser encerrado sem: " + ", ".join(faltantes) + "."
        )


def _identificar_estado_ativo(
    jornada: Jornada,
) -> tuple[Atividade | None, Pausa | None, EventoSecundario | None]:
    """Deriva a atividade principal ativa, a pausa ativa e o evento
    secundario ativo a partir do estado persistido das entidades, validando
    as invariantes do dominio.

    Usada na recuperacao de estado (Incremento 2): o estado ativo nunca e
    persistido separadamente, ele e sempre recalculado a partir dos estados
    de Atividade, Pausa e EventoSecundario, evitando divergencia entre eles.
    """
    atividades_em_andamento = [
        atividade
        for atividade in jornada.atividades
        if atividade.estado in (EstadoAtividade.ATIVA, EstadoAtividade.PAUSADA)
    ]
    if len(atividades_em_andamento) > 1:
        raise EstadoInconsistenteError(
            "Mais de uma atividade principal ativa ou pausada na mesma jornada."
        )
    atividade_ativa = atividades_em_andamento[0] if atividades_em_andamento else None

    pausas_ativas: list[Pausa] = []
    for atividade in jornada.atividades:
        encontradas = [pausa for pausa in atividade.pausas if pausa.estado == EstadoPausa.ATIVA]
        if encontradas and atividade is not atividade_ativa:
            raise EstadoInconsistenteError(
                "Pausa ativa vinculada a uma atividade que nao e a atividade "
                "principal em andamento."
            )
        pausas_ativas.extend(encontradas)

    if len(pausas_ativas) > 1:
        raise EstadoInconsistenteError("Mais de uma pausa ativa na mesma jornada.")
    pausa_ativa = pausas_ativas[0] if pausas_ativas else None

    if pausa_ativa is not None and (
        atividade_ativa is None or atividade_ativa.estado != EstadoAtividade.PAUSADA
    ):
        raise EstadoInconsistenteError(
            "Existe pausa ativa, mas a atividade vinculada nao esta com estado PAUSADA."
        )
    if (
        atividade_ativa is not None
        and atividade_ativa.estado == EstadoAtividade.PAUSADA
        and pausa_ativa is None
    ):
        raise EstadoInconsistenteError(
            "Atividade esta com estado PAUSADA, mas nao ha pausa ativa correspondente."
        )

    eventos_ativos = [
        evento
        for evento in jornada.eventos_secundarios
        if evento.estado == EstadoEventoSecundario.ATIVA
    ]
    if len(eventos_ativos) > 1:
        raise EstadoInconsistenteError(
            "Mais de um evento secundario (deslocamento/espera/apoio) ativo na "
            "mesma jornada."
        )
    evento_secundario_ativo = eventos_ativos[0] if eventos_ativos else None

    if evento_secundario_ativo is not None and atividade_ativa is not None:
        raise EstadoInconsistenteError(
            "Evento secundario ativo simultaneamente com atividade principal "
            "ativa/pausada - essas duas coisas sao mutuamente exclusivas."
        )

    return atividade_ativa, pausa_ativa, evento_secundario_ativo


class MotorJornada:
    def __init__(self, colaborador_matricula: str | None = None, *, jornada: Jornada | None = None):
        if jornada is not None:
            self.jornada = jornada
        else:
            if colaborador_matricula is None:
                raise TypeError(
                    "colaborador_matricula e obrigatorio ao criar uma jornada nova."
                )
            self.jornada = Jornada(colaborador_matricula=colaborador_matricula)
        self._atividade_ativa: Atividade | None = None
        self._pausa_ativa: Pausa | None = None
        self._evento_secundario_ativo: EventoSecundario | None = None

    @classmethod
    def a_partir_de(cls, jornada: Jornada) -> "MotorJornada":
        """Reconstroi um MotorJornada a partir de uma Jornada persistida.

        Usada na recuperacao apos fechamento/reinicio (Incremento 2). Nao
        confia em nenhum campo separado de "ativo agora": recalcula a
        atividade, a pausa e o evento secundario ativos a partir dos
        estados das entidades e levanta EstadoInconsistenteError se as
        invariantes do dominio (secao 8 do alinhamento oficial, mais as
        regras do Incremento 5) forem violadas.
        """
        atividade_ativa, pausa_ativa, evento_secundario_ativo = _identificar_estado_ativo(
            jornada
        )
        motor = cls(jornada=jornada)
        motor._atividade_ativa = atividade_ativa
        motor._pausa_ativa = pausa_ativa
        motor._evento_secundario_ativo = evento_secundario_ativo
        return motor

    # ------------------------------------------------------------------
    # Jornada
    # ------------------------------------------------------------------
    def iniciar_jornada(self, quando: datetime) -> Jornada:
        if self.jornada.estado != EstadoJornada.NAO_INICIADA:
            raise JornadaJaAbertaError(
                "Ja existe uma jornada iniciada para este colaborador."
            )
        self.jornada.inicio = quando
        self.jornada.estado = EstadoJornada.ABERTA
        return self.jornada

    def encerrar_jornada(self, quando: datetime) -> Jornada:
        if self.jornada.estado != EstadoJornada.ABERTA:
            raise JornadaNaoAbertaError("Nao ha jornada aberta para encerrar.")
        if self._pausa_ativa is not None:
            raise JornadaComPausaAbertaError(
                "Nao e permitido encerrar a jornada com pausa aberta."
            )
        if self._atividade_ativa is not None:
            raise JornadaComAtividadeAbertaError(
                "Nao e permitido encerrar a jornada com atividade aberta sem "
                "tratamento explicito."
            )
        if self._evento_secundario_ativo is not None:
            raise JornadaComEventoSecundarioAbertoError(
                "Nao e permitido encerrar a jornada com deslocamento/espera/apoio aberto."
            )
        self._validar_ordem(self.jornada.inicio, quando, "jornada")
        self.jornada.fim = quando
        self.jornada.estado = EstadoJornada.ENCERRADA
        return self.jornada

    # ------------------------------------------------------------------
    # Atividade
    # ------------------------------------------------------------------
    def iniciar_atividade(self, quando: datetime) -> Atividade:
        self._garantir_jornada_aberta()
        if self._atividade_ativa is not None:
            raise AtividadeJaAtivaError(
                "Ja existe uma atividade principal ativa para este colaborador."
            )
        if self._evento_secundario_ativo is not None:
            raise AtividadeExigeNenhumEventoSecundarioAtivoError(
                "Nao e permitido iniciar atividade com deslocamento/espera/apoio em andamento."
            )
        atividade = Atividade(inicio=quando, estado=EstadoAtividade.ATIVA)
        self.jornada.atividades.append(atividade)
        self._atividade_ativa = atividade
        return atividade

    def _finalizar_atividade(self, quando: datetime, resultado: ResultadoAtividade) -> Atividade:
        self._garantir_jornada_aberta()
        if self._pausa_ativa is not None:
            raise AtividadeEncerramentoComPausaAbertaError(
                "Nao e permitido encerrar a atividade com pausa aberta."
            )
        if self._atividade_ativa is None:
            raise AtividadeNaoAtivaError("Nao ha atividade ativa para encerrar.")
        atividade = self._atividade_ativa
        self._validar_ordem(atividade.inicio, quando, "atividade")
        if atividade.dados_falha is not None:
            _validar_dados_falha_completos(atividade.dados_falha)
        atividade.fim = quando
        atividade.estado = EstadoAtividade.ENCERRADA
        atividade.resultado = resultado
        self._atividade_ativa = None
        return atividade

    def encerrar_atividade(self, quando: datetime) -> Atividade:
        return self._finalizar_atividade(quando, ResultadoAtividade.CONCLUIDA)

    def encerrar_atividade_nao_concluida(self, quando: datetime) -> Atividade:
        """"Atividade nao concluida" (EE23, ADR-0023/0025) - contraparte de
        encerrar_atividade quando a manutencao programada nao termina no
        turno. So se aplica a Atividade comum: atendimento de falha usa
        transferir_atendimento_falha para o desfecho equivalente."""
        if self._atividade_ativa is not None and self._atividade_ativa.dados_falha is not None:
            raise AtividadeNaoConcluidaExigeSemDadosFalhaError(
                "Atendimento de falha usa transferir_atendimento_falha, nao "
                "encerrar_atividade_nao_concluida."
            )
        return self._finalizar_atividade(quando, ResultadoAtividade.NAO_CONCLUIDA)

    # ------------------------------------------------------------------
    # Ordens de servico associadas a Atividade comum (ADR-0025)
    # ------------------------------------------------------------------
    def adicionar_ordem_servico(self, quando: datetime, numero: str) -> OrdemServico:
        self._garantir_jornada_aberta()
        if self._atividade_ativa is None:
            raise AtividadeNaoAtivaError("Nao ha atividade ativa para associar uma OS.")
        if self._atividade_ativa.dados_falha is not None:
            raise OrdemServicoExigeAtividadeSemFalhaError(
                "OS so se associa a atividade comum, nao a atendimento de falha."
            )
        if not numero:
            raise OrdemServicoNumeroObrigatorioError("O numero da OS e obrigatorio.")
        ordem = OrdemServico(numero=numero, criada_em=quando)
        self._atividade_ativa.ordens_servico.append(ordem)
        return ordem

    def excluir_ordem_servico(self, ordem_id) -> OrdemServico:
        """Exclusao parcial de OS nao concluidas (ADR-0023): soft-delete,
        nunca remove da lista - reenviar a mesma exclusao e idempotente
        (excluida=True de novo nao muda nada)."""
        self._garantir_jornada_aberta()
        if self._atividade_ativa is None:
            raise AtividadeNaoAtivaError("Nao ha atividade ativa para excluir uma OS.")
        for ordem in self._atividade_ativa.ordens_servico:
            if ordem.id == ordem_id:
                ordem.excluida = True
                return ordem
        raise OrdemServicoNaoEncontradaError(f"Nenhuma OS com id {ordem_id} na atividade ativa.")

    # ------------------------------------------------------------------
    # Atendimento de falha (Incremento 6)
    # ------------------------------------------------------------------
    def iniciar_atendimento_falha(self, quando: datetime) -> Atividade:
        """Inicia uma atividade marcada como atendimento de falha.

        Reaproveita integralmente as regras de Atividade (jornada aberta,
        atividade principal unica, mutuamente exclusiva com evento
        secundario) - o unico acrescimo e que encerrar_atividade passa a
        exigir nota, ativo, sintoma, objeto e observacao antes de aceitar
        o encerramento (docs/48_ADR_0021_ATENDIMENTO_DE_FALHA_CAMPO.md).
        """
        atividade = self.iniciar_atividade(quando)
        atividade.dados_falha = DadosFalha()
        return atividade

    def registrar_dados_falha(
        self,
        *,
        nota: str | None = None,
        ativo: str | None = None,
        sintoma: str | None = None,
        objeto: str | None = None,
        causa: str | None = None,
        acao: str | None = None,
        observacao: str | None = None,
        gps_latitude: float | None = None,
        gps_longitude: float | None = None,
        gps_precisao_metros: float | None = None,
        gps_capturado_em: datetime | None = None,
        foto_caminho: str | None = None,
    ) -> DadosFalha:
        """Atualiza parcialmente os dados do atendimento de falha em andamento.

        Cada campo so e sobrescrito se for informado (nao-None), permitindo
        preencher nota/ativo/sintoma/objeto no inicio e observacao mais
        perto do encerramento. `causa`/`acao` continuam aceitos por
        compatibilidade (nao usados pelo formulario atual da interface de
        campo, ver ADR-0021). `gps_*`/`foto_caminho` sao best-effort - nunca
        exigidos por `_validar_dados_falha_completos` (ver CAMPOS_OBRIGATORIOS_FALHA).
        """
        self._garantir_jornada_aberta()
        if self._atividade_ativa is None or self._atividade_ativa.dados_falha is None:
            raise AtendimentoFalhaNaoAtivoError(
                "Nao ha atendimento de falha ativo para registrar dados."
            )
        dados = self._atividade_ativa.dados_falha
        if nota is not None:
            dados.nota = nota
        if ativo is not None:
            dados.ativo = ativo
        if sintoma is not None:
            dados.sintoma = sintoma
        if objeto is not None:
            dados.objeto = objeto
        if causa is not None:
            dados.causa = causa
        if acao is not None:
            dados.acao = acao
        if observacao is not None:
            dados.observacao = observacao
        if gps_latitude is not None:
            dados.gps_latitude = gps_latitude
        if gps_longitude is not None:
            dados.gps_longitude = gps_longitude
        if gps_precisao_metros is not None:
            dados.gps_precisao_metros = gps_precisao_metros
        if gps_capturado_em is not None:
            dados.gps_capturado_em = gps_capturado_em
        if foto_caminho is not None:
            dados.foto_caminho = foto_caminho
        return dados

    def transferir_atendimento_falha(self, quando: datetime) -> Atividade:
        """Encerra o atendimento de falha ativo sem exigir campos completos
        - usado quando o colaborador nao consegue concluir no proprio
        turno e passa o atendimento a outra matricula ("Falha nao
        Concluida", D4 do roteiro combinado apos o ADR-0021).

        Deliberadamente pula _validar_dados_falha_completos: e o unico
        jeito de uma atividade com dados_falha terminar ENCERRADA
        incompleta - isso serve de marca de auditoria (ENCERRADA e
        incompleta so pode significar "transferida", nunca "concluida").
        So encerra a atividade, nao a jornada - o colaborador pode ter
        mais o que fazer no resto do turno.
        """
        self._garantir_jornada_aberta()
        if self._pausa_ativa is not None:
            raise AtividadeEncerramentoComPausaAbertaError(
                "Nao e permitido encerrar a atividade com pausa aberta."
            )
        if self._atividade_ativa is None or self._atividade_ativa.dados_falha is None:
            raise AtendimentoFalhaNaoAtivoError(
                "Nao ha atendimento de falha ativo para transferir."
            )
        atividade = self._atividade_ativa
        self._validar_ordem(atividade.inicio, quando, "atividade")
        atividade.fim = quando
        atividade.estado = EstadoAtividade.ENCERRADA
        self._atividade_ativa = None
        return atividade

    # ------------------------------------------------------------------
    # Pausa
    # ------------------------------------------------------------------
    def iniciar_pausa(self, quando: datetime, motivo: str) -> Pausa:
        self._garantir_jornada_aberta()
        if not motivo:
            raise PausaMotivoObrigatorioError("O motivo da pausa e obrigatorio.")
        if self._pausa_ativa is not None:
            raise PausaJaAtivaError("Ja existe uma pausa ativa para este colaborador.")
        if self._atividade_ativa is None or self._atividade_ativa.estado != EstadoAtividade.ATIVA:
            raise PausaExigeAtividadeAtivaError(
                "Pausa somente pode ser iniciada com atividade principal ativa."
            )
        atividade = self._atividade_ativa
        self._validar_ordem(atividade.inicio, quando, "pausa")
        pausa = Pausa(
            atividade_id=atividade.id,
            motivo=motivo,
            inicio=quando,
            estado=EstadoPausa.ATIVA,
        )
        atividade.pausas.append(pausa)
        atividade.estado = EstadoAtividade.PAUSADA
        self._pausa_ativa = pausa
        return pausa

    def finalizar_pausa(self, quando: datetime) -> Pausa:
        self._garantir_jornada_aberta()
        if self._pausa_ativa is None:
            raise PausaNaoAtivaError("Nao ha pausa ativa para finalizar.")
        pausa = self._pausa_ativa
        self._validar_ordem(pausa.inicio, quando, "pausa")
        pausa.fim = quando
        pausa.estado = EstadoPausa.ENCERRADA
        self._pausa_ativa = None
        self._atividade_ativa.estado = EstadoAtividade.ATIVA
        return pausa

    # ------------------------------------------------------------------
    # Evento secundario (deslocamento, espera, apoio - Incremento 5)
    # ------------------------------------------------------------------
    def iniciar_evento_secundario(
        self, quando: datetime, tipo: TipoEventoSecundario, motivo: str
    ) -> EventoSecundario:
        self._garantir_jornada_aberta()
        if tipo is None:
            raise EventoSecundarioTipoObrigatorioError(
                "O tipo do evento secundario (DESLOCAMENTO/ESPERA/APOIO) e obrigatorio."
            )
        if not motivo:
            raise EventoSecundarioMotivoObrigatorioError(
                "O motivo do evento secundario e obrigatorio."
            )
        if self._evento_secundario_ativo is not None:
            raise EventoSecundarioJaAtivoError(
                "Ja existe um deslocamento/espera/apoio ativo para este colaborador."
            )
        if self._atividade_ativa is not None:
            raise EventoSecundarioExigeNenhumaAtividadePrincipalAtivaError(
                "Nao e permitido iniciar deslocamento/espera/apoio com atividade "
                "principal em andamento."
            )
        evento = EventoSecundario(
            tipo=tipo, motivo=motivo, inicio=quando, estado=EstadoEventoSecundario.ATIVA
        )
        self.jornada.eventos_secundarios.append(evento)
        self._evento_secundario_ativo = evento
        return evento

    def encerrar_evento_secundario(self, quando: datetime) -> EventoSecundario:
        self._garantir_jornada_aberta()
        if self._evento_secundario_ativo is None:
            raise EventoSecundarioNaoAtivoError(
                "Nao ha deslocamento/espera/apoio ativo para encerrar."
            )
        evento = self._evento_secundario_ativo
        self._validar_ordem(evento.inicio, quando, "evento secundario")
        evento.fim = quando
        evento.estado = EstadoEventoSecundario.ENCERRADA
        self._evento_secundario_ativo = None
        return evento

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _garantir_jornada_aberta(self) -> None:
        if self.jornada.estado != EstadoJornada.ABERTA:
            raise JornadaNaoAbertaError("A operacao exige uma jornada aberta.")

    @staticmethod
    def _validar_ordem(inicio: datetime, fim: datetime, rotulo: str) -> None:
        if fim < inicio:
            raise TimestampInvalidoError(
                f"O timestamp de fim da {rotulo} nao pode ser anterior ao inicio."
            )
