"""Sincronizacao em lote de pulsos GPS (Incremento 7).

Le pulsos pendentes a partir do cursor (o que ainda nao foi confirmado
pelo servidor) e envia em lotes de tamanho configuravel, avancando o
cursor somente quando o lote inteiro e aceito. Reenviar o mesmo intervalo
(por exemplo, apos um ack perdido) e seguro porque o cliente de
transporte trata cada lote como upsert por id de pulso (ver
ClienteSincronizacaoEmMemoria.enviar_lote_pulsos).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from workforce_storage.repositorio_pulsos_gps import RepositorioPulsosGpsArquivo
from workforce_storage.serializacao import pulso_gps_para_dict

from .cliente import ClienteSincronizacao, StatusEnvio
from .cursor_pulsos import CursorSincronizacaoPulsos, RepositorioCursorPulsosArquivo

TAMANHO_LOTE_PULSOS_PADRAO = 100


@dataclass
class RelatorioSincronizacaoPulsos:
    enviados: int = 0
    sincronizados: int = 0
    com_erro: bool = False
    mensagem_erro: str = ""


class SincronizadorPulsos:
    def __init__(
        self,
        repositorio_pulsos: RepositorioPulsosGpsArquivo,
        repositorio_cursor: RepositorioCursorPulsosArquivo,
        cliente: ClienteSincronizacao,
    ):
        self._repo_pulsos = repositorio_pulsos
        self._repo_cursor = repositorio_cursor
        self._cliente = cliente

    def sincronizar_pendentes(
        self, jornada_id: UUID, tamanho_lote: int = TAMANHO_LOTE_PULSOS_PADRAO
    ) -> RelatorioSincronizacaoPulsos:
        pulsos = self._repo_pulsos.ler_pulsos(jornada_id)
        cursor = self._repo_cursor.carregar_ou_zero(jornada_id)

        pendentes = pulsos[cursor.total_sincronizado : cursor.total_sincronizado + tamanho_lote]
        if not pendentes:
            return RelatorioSincronizacaoPulsos(enviados=0, sincronizados=0)

        lote_dict = [pulso_gps_para_dict(p) for p in pendentes]
        resultado = self._cliente.enviar_lote_pulsos(jornada_id, lote_dict)

        if resultado.status != StatusEnvio.ACEITO:
            return RelatorioSincronizacaoPulsos(
                enviados=len(pendentes),
                sincronizados=0,
                com_erro=True,
                mensagem_erro=resultado.mensagem,
            )

        cursor.total_sincronizado += len(pendentes)
        cursor.atualizado_em = datetime.now(timezone.utc)
        self._repo_cursor.salvar(cursor)
        return RelatorioSincronizacaoPulsos(enviados=len(pendentes), sincronizados=len(pendentes))

    def sincronizar_tudo(
        self, jornada_id: UUID, tamanho_lote: int = TAMANHO_LOTE_PULSOS_PADRAO
    ) -> RelatorioSincronizacaoPulsos:
        """Chama sincronizar_pendentes repetidamente ate esvaziar a fila ou
        ate encontrar um erro - conveniencia para quando ha mais pulsos
        pendentes do que cabem em um unico lote.
        """
        total = RelatorioSincronizacaoPulsos()
        while True:
            parcial = self.sincronizar_pendentes(jornada_id, tamanho_lote)
            total.enviados += parcial.enviados
            total.sincronizados += parcial.sincronizados
            if parcial.com_erro:
                total.com_erro = True
                total.mensagem_erro = parcial.mensagem_erro
                break
            if parcial.enviados == 0:
                break
        return total
