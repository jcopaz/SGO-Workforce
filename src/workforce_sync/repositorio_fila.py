"""Persistencia local dos registros de fila (Incremento 3).

Mesmo padrao de workforce_storage.RepositorioJornadaArquivo: um arquivo
JSON por registro, escrita atomica, e nenhuma remocao automatica de
arquivo corrompido. A fila precisa sobreviver a fechamento/reinicio tanto
quanto a jornada em si - senao o app "esqueceria" o que ainda falta
sincronizar.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Union
from uuid import UUID

from .entidades import RegistroFila
from .enums import StatusSincronizacao
from .exceptions import RegistroCorrompidoError, RegistroNaoEncontradoError


class RepositorioFilaArquivo:
    def __init__(self, diretorio: Union[str, Path]):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(parents=True, exist_ok=True)

    def _caminho(self, jornada_id: UUID) -> Path:
        return self.diretorio / f"{jornada_id}.json"

    def salvar(self, registro: RegistroFila) -> None:
        caminho = self._caminho(registro.jornada_id)
        tmp = caminho.with_name(caminho.name + ".tmp")
        dados = {
            "jornada_id": str(registro.jornada_id),
            "status": registro.status.value,
            "tentativas": registro.tentativas,
            "ultimo_erro": registro.ultimo_erro,
            "criado_em": registro.criado_em.isoformat(),
            "atualizado_em": registro.atualizado_em.isoformat(),
        }
        tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(caminho)

    def carregar(self, jornada_id: UUID) -> RegistroFila:
        caminho = self._caminho(jornada_id)
        if not caminho.exists():
            raise RegistroNaoEncontradoError(
                f"Nao existe registro de fila para a jornada {jornada_id}."
            )
        texto = caminho.read_text(encoding="utf-8")
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise RegistroCorrompidoError(
                f"Registro de fila corrompido (JSON invalido): {caminho}"
            ) from exc
        try:
            return RegistroFila(
                jornada_id=UUID(dados["jornada_id"]),
                status=StatusSincronizacao(dados["status"]),
                tentativas=dados["tentativas"],
                ultimo_erro=dados["ultimo_erro"],
                criado_em=datetime.fromisoformat(dados["criado_em"]),
                atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise RegistroCorrompidoError(
                f"Registro de fila com estrutura invalida: {caminho}"
            ) from exc

    def listar_todos(self) -> List[RegistroFila]:
        registros: List[RegistroFila] = []
        for caminho in self.diretorio.glob("*.json"):
            try:
                registros.append(self.carregar(UUID(caminho.stem)))
            except RegistroCorrompidoError:
                continue
        return registros
