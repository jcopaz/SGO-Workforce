"""Fachada da fila de sincronizacao (Incremento 3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from uuid import UUID

from .entidades import RegistroFila
from .enums import StatusSincronizacao
from .exceptions import RegistroNaoEncontradoError
from .repositorio_fila import RepositorioFilaArquivo


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class FilaSincronizacao:
    def __init__(
        self,
        repositorio: RepositorioFilaArquivo,
        relogio: Optional[Callable[[], datetime]] = None,
    ):
        self._repo = repositorio
        self._relogio = relogio or _agora_utc

    def enfileirar(self, jornada_id: UUID) -> RegistroFila:
        """Marca a jornada como pendente de sincronizacao.

        Deve ser chamado apos qualquer transicao local confirmada (inicio ou
        fim de jornada, atividade ou pausa). Se ja existir um registro
        SINCRONIZADO ou ERRO, ele volta para PENDENTE porque o conteudo
        mudou. Um registro em CONFLITO tambem pode ser reenfileirado aqui,
        mas isso e uma acao deliberada de quem chama (por exemplo, apos
        resolucao manual) - este metodo nao resolve o conflito sozinho.
        """
        agora = self._relogio()
        try:
            registro = self._repo.carregar(jornada_id)
            registro.status = StatusSincronizacao.PENDENTE
            registro.atualizado_em = agora
        except RegistroNaoEncontradoError:
            registro = RegistroFila(
                jornada_id=jornada_id,
                status=StatusSincronizacao.PENDENTE,
                tentativas=0,
                ultimo_erro=None,
                criado_em=agora,
                atualizado_em=agora,
            )
        self._repo.salvar(registro)
        return registro

    def listar(self, status: Optional[StatusSincronizacao] = None) -> List[RegistroFila]:
        registros = self._repo.listar_todos()
        if status is None:
            return registros
        return [registro for registro in registros if registro.status == status]

    def resumo(self) -> Dict[StatusSincronizacao, int]:
        contagem = {status: 0 for status in StatusSincronizacao}
        for registro in self._repo.listar_todos():
            contagem[registro.status] += 1
        return contagem

    def _marcar(
        self, jornada_id: UUID, status: StatusSincronizacao, erro: Optional[str]
    ) -> RegistroFila:
        registro = self._repo.carregar(jornada_id)
        registro.status = status
        registro.tentativas += 1
        registro.ultimo_erro = erro
        registro.atualizado_em = self._relogio()
        self._repo.salvar(registro)
        return registro

    def marcar_sincronizado(self, jornada_id: UUID) -> RegistroFila:
        return self._marcar(jornada_id, StatusSincronizacao.SINCRONIZADO, None)

    def marcar_erro(self, jornada_id: UUID, mensagem: str) -> RegistroFila:
        return self._marcar(jornada_id, StatusSincronizacao.ERRO, mensagem)

    def marcar_conflito(self, jornada_id: UUID, mensagem: str) -> RegistroFila:
        return self._marcar(jornada_id, StatusSincronizacao.CONFLITO, mensagem)
