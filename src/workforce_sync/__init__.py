"""
Fila offline e sincronizacao idempotente do SGO Workforce (Incremento 3).

Formato de registro de fila, tamanho de lote e politica de retry sao
decisoes provisorias - ver
docs/30_ADR_0003_FILA_OFFLINE_E_SINCRONIZACAO_PROVISORIA.md.
"""

from .cliente import ClienteSincronizacao, ClienteSincronizacaoEmMemoria, ResultadoEnvio, StatusEnvio
from .cursor_pulsos import CursorSincronizacaoPulsos, RepositorioCursorPulsosArquivo
from .entidades import RegistroFila
from .enums import StatusSincronizacao
from .exceptions import ErroSincronizacao, RegistroCorrompidoError, RegistroNaoEncontradoError
from .fila import FilaSincronizacao
from .repositorio_fila import RepositorioFilaArquivo
from .sincronizador import RelatorioSincronizacao, Sincronizador
from .sincronizador_pulsos import RelatorioSincronizacaoPulsos, SincronizadorPulsos

__all__ = [
    "ClienteSincronizacao",
    "ClienteSincronizacaoEmMemoria",
    "ResultadoEnvio",
    "StatusEnvio",
    "RegistroFila",
    "StatusSincronizacao",
    "ErroSincronizacao",
    "RegistroCorrompidoError",
    "RegistroNaoEncontradoError",
    "FilaSincronizacao",
    "RepositorioFilaArquivo",
    "RelatorioSincronizacao",
    "Sincronizador",
    "CursorSincronizacaoPulsos",
    "RepositorioCursorPulsosArquivo",
    "RelatorioSincronizacaoPulsos",
    "SincronizadorPulsos",
]
