"""Entidades do Incremento 1: Jornada, Atividade e Pausa.

Sao estruturas de dados em memoria. Persistencia, serializacao e UUID
de sincronizacao pertencem aos Incrementos 2 e 3 (fora deste escopo).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from .enums import (
    EstadoAtividade,
    EstadoEventoSecundario,
    EstadoJornada,
    EstadoPausa,
    QualidadePulso,
    TipoEventoSecundario,
)
from .integracao_sgo import ReferenciaOS


@dataclass
class Pausa:
    atividade_id: UUID
    motivo: str
    id: UUID = field(default_factory=uuid4)
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    estado: EstadoPausa = EstadoPausa.CRIADA


@dataclass
class DadosFalha:
    """Dados de atendimento de falha (Incremento 6, campos revistos no
    ADR-0021 para o formulario da interface de campo).

    Campos obrigatorios ao encerrar, conforme
    docs/48_ADR_0021_ATENDIMENTO_DE_FALHA_CAMPO.md: nota, ativo, sintoma,
    objeto e observacao. Podem ser preenchidos progressivamente entre o
    inicio e o encerramento do atendimento (o horario final obrigatorio e
    o proprio `Atividade.fim`).

    `objeto` e o componente causador (catalogo RASF
    `catalogos/componentes_causadores.csv`), a pedido do responsavel pelo
    produto em 2026-07-27.

    `causa` e `acao` eram campos obrigatorios separados ate o ADR-0021 -
    continuam existindo aqui (nao removidos, para nao quebrar o formato
    de persistencia de registros ja gravados) mas deixaram de ser
    exigidos e nao aparecem no formulario atual da interface de campo;
    `observacao` passou a cobrir o que antes era "causa e acao" (rotulo
    "Observacoes/Causa" na tela).

    `os_referencia` e campo recomendado (nao obrigatorio) para a "OS
    relacionada". Usa ReferenciaOS (Incremento 13) desde o inicio -
    nunca um numero de OS solto - porque "a OS nao podera ser associada
    somente pelo numero, porque o SAP podera reutilizar o numero em
    ciclos diferentes" (docs/27 secao 10.3).
    """

    nota: Optional[str] = None
    ativo: Optional[str] = None
    sintoma: Optional[str] = None
    objeto: Optional[str] = None
    causa: Optional[str] = None
    acao: Optional[str] = None
    observacao: Optional[str] = None
    os_referencia: Optional[ReferenciaOS] = None


@dataclass
class Atividade:
    id: UUID = field(default_factory=uuid4)
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    estado: EstadoAtividade = EstadoAtividade.CRIADA
    pausas: List[Pausa] = field(default_factory=list)
    dados_falha: Optional[DadosFalha] = None


@dataclass
class EventoSecundario:
    """Deslocamento, espera ou apoio (Incremento 5).

    Ao contrario da Pausa (vinculada a uma Atividade), o evento secundario
    e vinculado diretamente a Jornada e e mutuamente exclusivo com a
    atividade principal - ver docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md.
    """

    tipo: TipoEventoSecundario
    motivo: str
    id: UUID = field(default_factory=uuid4)
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    estado: EstadoEventoSecundario = EstadoEventoSecundario.CRIADA


@dataclass
class Jornada:
    colaborador_matricula: str
    id: UUID = field(default_factory=uuid4)
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    estado: EstadoJornada = EstadoJornada.NAO_INICIADA
    atividades: List[Atividade] = field(default_factory=list)
    eventos_secundarios: List[EventoSecundario] = field(default_factory=list)


@dataclass
class PulsoGps:
    """Pulso periodico de localizacao (Incremento 7).

    Vinculado a Jornada por `jornada_id` (nao aninhado, ao contrario de
    Atividade/EventoSecundario) porque o volume esperado e muito maior -
    o modelo alvo (docs/27 secao 4.4) ja lista "pulsos GPS" como entidade
    propria, separada da jornada. Campos conforme
    docs/08_GPS_PULSOS_E_PRIVACIDADE.md secao "Campos" - nenhum foi
    inventado aqui.
    """

    jornada_id: UUID
    colaborador_matricula: str
    latitude: float
    longitude: float
    precisao_metros: float
    timestamp_dispositivo: datetime
    id: UUID = field(default_factory=uuid4)
    velocidade_metros_segundo: Optional[float] = None
    direcao_graus: Optional[float] = None
    fonte: Optional[str] = None
    status_aplicativo: Optional[str] = None
    bateria_percentual: Optional[float] = None
    timestamp_recebimento_servidor: Optional[datetime] = None
    qualidade: QualidadePulso = QualidadePulso.NAO_AVALIADO
