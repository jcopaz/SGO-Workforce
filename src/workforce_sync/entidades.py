"""Entidade de fila do Incremento 3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from .enums import StatusSincronizacao


@dataclass
class RegistroFila:
    jornada_id: UUID
    status: StatusSincronizacao
    tentativas: int
    ultimo_erro: Optional[str]
    criado_em: datetime
    atualizado_em: datetime
