"""
Camada de persistencia local do SGO Workforce (Incremento 2).

Responsavel por serializar/desserializar as entidades de dominio
(workforce_core) e por gravar/recuperar o estado de uma jornada em disco de
forma resiliente a fechamento abrupto e a arquivos corrompidos.

Formato de serializacao e politica de corrupcao sao decisoes provisorias -
ver docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md.
"""

from .catalogo_rasf import ItemCatalogoRasf, carregar_catalogo_rasf, carregar_catalogos_rasf
from .exceptions import ArquivoCorrompidoError, ErroPersistencia, JornadaNaoEncontradaError
from .repositorio_jornada import RepositorioJornadaArquivo
from .repositorio_pulsos_gps import RepositorioPulsosGpsArquivo

__all__ = [
    "ArquivoCorrompidoError",
    "ErroPersistencia",
    "JornadaNaoEncontradaError",
    "RepositorioJornadaArquivo",
    "RepositorioPulsosGpsArquivo",
    "ItemCatalogoRasf",
    "carregar_catalogo_rasf",
    "carregar_catalogos_rasf",
]
