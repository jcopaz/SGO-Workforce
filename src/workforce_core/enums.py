"""Estados do dominio, conforme docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 8."""

from enum import Enum


class EstadoJornada(str, Enum):
    NAO_INICIADA = "NAO_INICIADA"
    ABERTA = "ABERTA"
    ENCERRADA = "ENCERRADA"


class EstadoAtividade(str, Enum):
    CRIADA = "CRIADA"
    ATIVA = "ATIVA"
    PAUSADA = "PAUSADA"
    ENCERRADA = "ENCERRADA"


class ResultadoAtividade(str, Enum):
    """Resultado do encerramento de uma Atividade comum (EE17/EE23,
    ADR-0025). Antes desta decisao, EE17 era so inferido pela ausencia de
    dados_falha (workforce_core.consolidacao) - este campo torna o
    resultado explicito para permitir o segundo desfecho (EE23,
    "Manutencao Programada Nao Concluida", ADR-0023).

    None (o padrao para qualquer Atividade que nunca passou por
    encerrar_atividade_nao_concluida) e tratado como CONCLUIDA na
    consolidacao - mesmo comportamento que ja existia antes deste campo
    existir, preservando jornadas ja sincronizadas.
    """

    CONCLUIDA = "CONCLUIDA"
    NAO_CONCLUIDA = "NAO_CONCLUIDA"


class EstadoPausa(str, Enum):
    CRIADA = "CRIADA"
    ATIVA = "ATIVA"
    ENCERRADA = "ENCERRADA"


class EstadoEventoSecundario(str, Enum):
    """Incremento 5: deslocamento, espera e apoio (docs/07_MOTOR_EVENTOS_E_HH.md)."""

    CRIADA = "CRIADA"
    ATIVA = "ATIVA"
    ENCERRADA = "ENCERRADA"


class TipoEventoSecundario(str, Enum):
    DESLOCAMENTO = "DESLOCAMENTO"
    ESPERA = "ESPERA"
    APOIO = "APOIO"


class QualidadePulso(str, Enum):
    """Marcacao de qualidade de um pulso GPS (Incremento 7).

    Categorias citadas literalmente em docs/08_GPS_PULSOS_E_PRIVACIDADE.md
    ("Pontos impossiveis, saltos e velocidade incompativel devem ser
    marcados, nao sobrescritos"). Nenhum limiar numerico (precisao minima,
    velocidade maxima plausivel) e definido pelo enum em si - isso e
    decisao de negocio pendente (secao 15.3 "Antes do Incremento 7").
    """

    NAO_AVALIADO = "NAO_AVALIADO"
    OK = "OK"
    PRECISAO_RUIM = "PRECISAO_RUIM"
    SALTO_IMPOSSIVEL = "SALTO_IMPOSSIVEL"
    VELOCIDADE_INCOMPATIVEL = "VELOCIDADE_INCOMPATIVEL"
