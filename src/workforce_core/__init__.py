"""
Motor de dominio do SGO Workforce: Jornada, Atividade, Pausa e calculo de HH.

Escopo do Incremento 1 (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 7).
Sem persistencia, interface, API ou infraestrutura.
"""

from .enums import (
    EstadoAtividade,
    EstadoEventoSecundario,
    EstadoJornada,
    EstadoPausa,
    QualidadePulso,
    ResultadoAtividade,
    TipoEventoSecundario,
)
from .entities import (
    Atividade,
    DadosFalha,
    EventoSecundario,
    Jornada,
    OrdemServico,
    Pausa,
    PulsoGps,
)
from .engine import MotorJornada
from .exceptions import EstadoInconsistenteError
from .integracao_sgo import (
    Ativo,
    Coordenacao,
    ContratoSGO,
    ContratoSGOEmMemoria,
    Especialidade,
    MetadadosSnapshot,
    OsProgramada,
    Patio,
    ReferenciaOS,
    UsuarioAutorizado,
)
from . import calculo
from . import catalogo
from . import consolidacao
from . import exceptions
from . import fuso_horario
from . import geo
from . import integracao_sgo
from . import pcm
from . import qualidade_gps

__all__ = [
    "EstadoJornada",
    "EstadoAtividade",
    "EstadoPausa",
    "EstadoEventoSecundario",
    "TipoEventoSecundario",
    "ResultadoAtividade",
    "QualidadePulso",
    "Jornada",
    "Atividade",
    "Pausa",
    "EventoSecundario",
    "DadosFalha",
    "OrdemServico",
    "PulsoGps",
    "MotorJornada",
    "ReferenciaOS",
    "UsuarioAutorizado",
    "Coordenacao",
    "Especialidade",
    "Patio",
    "Ativo",
    "OsProgramada",
    "MetadadosSnapshot",
    "ContratoSGO",
    "ContratoSGOEmMemoria",
    "calculo",
    "catalogo",
    "consolidacao",
    "exceptions",
    "fuso_horario",
    "geo",
    "integracao_sgo",
    "pcm",
    "qualidade_gps",
]
