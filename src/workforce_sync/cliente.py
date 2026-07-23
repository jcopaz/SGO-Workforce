"""Contrato de transporte da sincronizacao (Incremento 3).

Nao existe ainda uma API real (FastAPI e Postgres/Neon pertencem a
incrementos de infraestrutura ainda nao construidos). O Protocol
ClienteSincronizacao define o contrato minimo que um transporte real
precisara cumprir; ClienteSincronizacaoEmMemoria e uma implementacao falsa
usada em desenvolvimento e testes para validar o algoritmo de
sincronizacao idempotente antes de existir um servidor de verdade.

Autenticacao tecnica da API e um item explicitamente pendente (secao 15.3
do alinhamento oficial) e nao e tratado aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Protocol, Set
from uuid import UUID


class StatusEnvio(str, Enum):
    ACEITO = "ACEITO"
    CONFLITO = "CONFLITO"
    ERRO = "ERRO"


@dataclass
class ResultadoEnvio:
    status: StatusEnvio
    mensagem: str = ""


class ClienteSincronizacao(Protocol):
    def enviar_jornada(self, jornada_id: UUID, dados: dict) -> ResultadoEnvio:
        ...

    def enviar_lote_pulsos(self, jornada_id: UUID, lote: List[dict]) -> ResultadoEnvio:
        ...


class ClienteSincronizacaoEmMemoria:
    """Simula um servidor idempotente, para uso em testes e desenvolvimento local.

    Reenviar o mesmo jornada_id nunca cria um segundo registro no lado do
    "servidor": a copia armazenada e apenas substituida (upsert). Isso
    modela a garantia de idempotencia exigida pelo CLAUDE.md sem depender
    de uma API real.
    """

    def __init__(self) -> None:
        self.armazenado: Dict[UUID, dict] = {}
        self.chamadas: List[UUID] = []
        self._forcar_conflito: Set[UUID] = set()
        self._forcar_erro: Set[UUID] = set()
        # pulsos_recebidos: jornada_id -> {pulso_id: dados}. Um dict (nao
        # lista) para que o reenvio do mesmo lote (ack perdido) nunca
        # duplique um pulso ja recebido - mesma garantia de idempotencia
        # usada para jornadas, aplicada por id de pulso.
        self.pulsos_recebidos: Dict[UUID, Dict[str, dict]] = {}
        self.chamadas_lote_pulsos: List[UUID] = []
        self._forcar_erro_pulsos: Set[UUID] = set()

    def forcar_conflito(self, jornada_id: UUID) -> None:
        self._forcar_conflito.add(jornada_id)

    def forcar_erro(self, jornada_id: UUID) -> None:
        self._forcar_erro.add(jornada_id)

    def forcar_erro_pulsos(self, jornada_id: UUID) -> None:
        self._forcar_erro_pulsos.add(jornada_id)

    def enviar_jornada(self, jornada_id: UUID, dados: dict) -> ResultadoEnvio:
        self.chamadas.append(jornada_id)
        if jornada_id in self._forcar_erro:
            self._forcar_erro.discard(jornada_id)
            return ResultadoEnvio(StatusEnvio.ERRO, "Falha simulada de rede.")
        if jornada_id in self._forcar_conflito:
            self._forcar_conflito.discard(jornada_id)
            return ResultadoEnvio(
                StatusEnvio.CONFLITO, "Versao mais recente ja existe no servidor."
            )
        self.armazenado[jornada_id] = dados
        return ResultadoEnvio(StatusEnvio.ACEITO)

    def enviar_lote_pulsos(self, jornada_id: UUID, lote: List[dict]) -> ResultadoEnvio:
        self.chamadas_lote_pulsos.append(jornada_id)
        if jornada_id in self._forcar_erro_pulsos:
            self._forcar_erro_pulsos.discard(jornada_id)
            return ResultadoEnvio(StatusEnvio.ERRO, "Falha simulada de rede.")
        recebidos = self.pulsos_recebidos.setdefault(jornada_id, {})
        for pulso in lote:
            recebidos[pulso["id"]] = pulso
        return ResultadoEnvio(StatusEnvio.ACEITO)
