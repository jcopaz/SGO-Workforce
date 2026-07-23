"""Motor de sincronizacao idempotente (Incremento 3).

Regras aplicadas (CLAUDE.md e docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md
secao 3.4):
- a sincronizacao e idempotente: reenviar o mesmo registro nao gera
  duplicidade (garantido pelo cliente, ver cliente.py);
- conflitos nunca sao resolvidos silenciosamente: um registro em CONFLITO
  sai do lote automatico e so volta a ser tentado apos reenfileiramento
  explicito (ver FilaSincronizacao.enfileirar);
- uma falha em um registro nao interrompe os demais do lote.

Tamanho de lote e politica de retry/backoff sao decisoes provisorias - ver
docs/30_ADR_0003_FILA_OFFLINE_E_SINCRONIZACAO_PROVISORIA.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from uuid import UUID

from workforce_storage.repositorio_jornada import RepositorioJornadaArquivo
from workforce_storage.serializacao import jornada_para_dict

from .cliente import ClienteSincronizacao, StatusEnvio
from .enums import StatusSincronizacao
from .fila import FilaSincronizacao

TAMANHO_LOTE_PADRAO = 20


@dataclass
class RelatorioSincronizacao:
    processados: List[UUID] = field(default_factory=list)
    sincronizados: List[UUID] = field(default_factory=list)
    com_erro: List[UUID] = field(default_factory=list)
    em_conflito: List[UUID] = field(default_factory=list)


class Sincronizador:
    def __init__(
        self,
        fila: FilaSincronizacao,
        repositorio_jornada: RepositorioJornadaArquivo,
        cliente: ClienteSincronizacao,
    ):
        self._fila = fila
        self._repo_jornada = repositorio_jornada
        self._cliente = cliente

    def sincronizar_pendentes(
        self, tamanho_lote: int = TAMANHO_LOTE_PADRAO
    ) -> RelatorioSincronizacao:
        candidatos = self._fila.listar(StatusSincronizacao.PENDENTE) + self._fila.listar(
            StatusSincronizacao.ERRO
        )
        lote = candidatos[:tamanho_lote]

        relatorio = RelatorioSincronizacao()
        for registro in lote:
            relatorio.processados.append(registro.jornada_id)
            try:
                jornada = self._repo_jornada.carregar(registro.jornada_id)
                dados = jornada_para_dict(jornada)
                resultado = self._cliente.enviar_jornada(registro.jornada_id, dados)
            except Exception as exc:  # nao deixa um registro ruim travar o lote inteiro
                self._fila.marcar_erro(registro.jornada_id, str(exc))
                relatorio.com_erro.append(registro.jornada_id)
                continue

            if resultado.status == StatusEnvio.ACEITO:
                self._fila.marcar_sincronizado(registro.jornada_id)
                relatorio.sincronizados.append(registro.jornada_id)
            elif resultado.status == StatusEnvio.CONFLITO:
                self._fila.marcar_conflito(registro.jornada_id, resultado.mensagem)
                relatorio.em_conflito.append(registro.jornada_id)
            else:
                self._fila.marcar_erro(registro.jornada_id, resultado.mensagem)
                relatorio.com_erro.append(registro.jornada_id)

        return relatorio
