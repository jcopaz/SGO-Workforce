"""Cursor de sincronizacao de pulsos GPS (Incremento 7).

Pulsos sao gravados em sequencia, append-only (RepositorioPulsosGpsArquivo),
e nao tem o conceito de "conflito" que uma Jornada tem (ninguem mais edita
um pulso). Por isso a fila de 4 estados usada para jornadas
(PENDENTE/SINCRONIZADO/ERRO/CONFLITO) seria excesso de maquinario aqui: um
cursor por jornada, guardando quantos pulsos ja foram confirmados pelo
servidor, e suficiente e mais simples.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Union
from uuid import UUID

from .exceptions import RegistroCorrompidoError


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CursorSincronizacaoPulsos:
    jornada_id: UUID
    total_sincronizado: int
    atualizado_em: datetime


class RepositorioCursorPulsosArquivo:
    """Mesmo padrao de escrita atomica de RepositorioJornadaArquivo."""

    def __init__(self, diretorio: Union[str, Path]):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(parents=True, exist_ok=True)

    def _caminho(self, jornada_id: UUID) -> Path:
        return self.diretorio / f"{jornada_id}.json"

    def salvar(self, cursor: CursorSincronizacaoPulsos) -> None:
        caminho = self._caminho(cursor.jornada_id)
        tmp = caminho.with_name(caminho.name + ".tmp")
        dados = {
            "jornada_id": str(cursor.jornada_id),
            "total_sincronizado": cursor.total_sincronizado,
            "atualizado_em": cursor.atualizado_em.isoformat(),
        }
        tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(caminho)

    def carregar_ou_zero(
        self, jornada_id: UUID, relogio: Optional[Callable[[], datetime]] = None
    ) -> CursorSincronizacaoPulsos:
        caminho = self._caminho(jornada_id)
        if not caminho.exists():
            return CursorSincronizacaoPulsos(
                jornada_id=jornada_id,
                total_sincronizado=0,
                atualizado_em=(relogio or _agora_utc)(),
            )
        texto = caminho.read_text(encoding="utf-8")
        try:
            dados = json.loads(texto)
            return CursorSincronizacaoPulsos(
                jornada_id=UUID(dados["jornada_id"]),
                total_sincronizado=dados["total_sincronizado"],
                atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise RegistroCorrompidoError(
                f"Cursor de sincronizacao de pulsos corrompido: {caminho}"
            ) from exc
