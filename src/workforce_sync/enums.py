"""Estados da fila de sincronizacao (Incremento 3).

Os quatro estados exigidos pelo CLAUDE.md ("a fila deve mostrar registros
pendentes, sincronizados, com erro e em conflito").
"""

from enum import Enum


class StatusSincronizacao(str, Enum):
    PENDENTE = "PENDENTE"
    SINCRONIZADO = "SINCRONIZADO"
    ERRO = "ERRO"
    CONFLITO = "CONFLITO"
