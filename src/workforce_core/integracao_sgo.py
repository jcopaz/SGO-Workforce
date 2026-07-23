"""Contrato de integracao futura com o SGO (Incremento 13).

Este modulo NAO integra com o SGO - a regra de ouro do CLAUDE.md e a
secao 3.1 do alinhamento oficial proibem acoplar o Workforce ao codigo do
SGO durante o MVP, e nao ha nenhum sistema SGO real presente neste
repositorio para integrar de qualquer forma. O que existe aqui e apenas a
FORMA do contrato futuro - as chaves e o formato de leitura ja descritos
em docs/16_INTEGRACAO_FUTURA_SGO.md e
docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 10, preparados com
antecedencia para que a integracao real (quando acontecer) nao exija
redesenhar as chaves.

Nao inventa: autenticacao entre aplicacoes, estrategia de SSO,
experiencia visual unificada, responsabilidade de cada sistema sobre os
dados mestres, nem regra de devolucao do HH real - tudo isso continua
pendente (secao 15.3 "Antes do Incremento 13").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ReferenciaOS:
    """Identificador de uma OS que nunca usa apenas o numero.

    docs/16_INTEGRACAO_FUTURA_SGO.md, secao "Chaves": "OS pode ser
    reaproveitada em ciclos SAP. Toda associacao futura deve carregar
    ciclo/plano/data de importacao, nao apenas o numero da OS." Repetido
    em docs/27 secao 10.3.

    `data_importacao` fica de fora da igualdade/hash (`compare=False`):
    e metadado de auditoria de quando o snapshot foi lido, nao parte da
    identidade da OS - duas leituras da mesma OS em datas diferentes
    continuam sendo a mesma OS.
    """

    numero: str
    ciclo_ou_plano: str
    data_importacao: Optional[datetime] = field(default=None, compare=False)


@dataclass(frozen=True)
class UsuarioAutorizado:
    matricula: str
    nome: str
    coordenacao_codigo: Optional[str] = None


@dataclass(frozen=True)
class Coordenacao:
    codigo: str
    descricao: str


@dataclass(frozen=True)
class Especialidade:
    codigo: str
    descricao: str


@dataclass(frozen=True)
class Patio:
    codigo: str
    descricao: str


@dataclass(frozen=True)
class Ativo:
    identificador: str
    descricao: str
    patio_codigo: Optional[str] = None


@dataclass(frozen=True)
class OsProgramada:
    referencia: ReferenciaOS
    descricao: str
    ativo_identificador: Optional[str] = None


@dataclass(frozen=True)
class MetadadosSnapshot:
    """"eventos de atualizacao com versao e timestamp" (docs/16)."""

    versao_contrato: str
    obtido_em: datetime


@runtime_checkable
class ContratoSGO(Protocol):
    """Contrato de leitura da "primeira integracao" (docs/27 secao 10.4).

    Somente leitura, deliberadamente: "Primeiro integracao por leitura/
    snapshot. Depois escrita controlada." (docs/16, secao "Estrategia").
    A devolucao de HH real (POST /integracao/hh-real sugerido em docs/16)
    e a "segunda integracao" (docs/27 secao 10.5) e permanece fora deste
    contrato ate que a primeira esteja validada.
    """

    def metadados_snapshot(self) -> MetadadosSnapshot: ...

    def listar_usuarios_autorizados(self) -> List[UsuarioAutorizado]: ...

    def listar_coordenacoes(self) -> List[Coordenacao]: ...

    def listar_especialidades(self) -> List[Especialidade]: ...

    def listar_patios(self) -> List[Patio]: ...

    def listar_ativos(self) -> List[Ativo]: ...

    def listar_os_programadas(self) -> List[OsProgramada]: ...


class ContratoSGOEmMemoria:
    """Implementacao falsa do ContratoSGO, para desenvolvimento e testes.

    Nao representa nenhum dado real do SGO. Serve apenas para validar que
    o formato do contrato (Protocol acima) e usavel antes de existir uma
    integracao real - mesmo papel que ClienteSincronizacaoEmMemoria
    cumpriu para o Incremento 3.
    """

    def __init__(self, versao_contrato: str = "0.0.0-dev"):
        self._versao_contrato = versao_contrato
        self._usuarios: List[UsuarioAutorizado] = []
        self._coordenacoes: List[Coordenacao] = []
        self._especialidades: List[Especialidade] = []
        self._patios: List[Patio] = []
        self._ativos: List[Ativo] = []
        self._os_programadas: List[OsProgramada] = []

    def metadados_snapshot(self) -> MetadadosSnapshot:
        return MetadadosSnapshot(
            versao_contrato=self._versao_contrato, obtido_em=datetime.now()
        )

    def carregar_usuarios(self, usuarios: List[UsuarioAutorizado]) -> None:
        self._usuarios = list(usuarios)

    def carregar_coordenacoes(self, coordenacoes: List[Coordenacao]) -> None:
        self._coordenacoes = list(coordenacoes)

    def carregar_especialidades(self, especialidades: List[Especialidade]) -> None:
        self._especialidades = list(especialidades)

    def carregar_patios(self, patios: List[Patio]) -> None:
        self._patios = list(patios)

    def carregar_ativos(self, ativos: List[Ativo]) -> None:
        self._ativos = list(ativos)

    def carregar_os_programadas(self, os_programadas: List[OsProgramada]) -> None:
        self._os_programadas = list(os_programadas)

    def listar_usuarios_autorizados(self) -> List[UsuarioAutorizado]:
        return list(self._usuarios)

    def listar_coordenacoes(self) -> List[Coordenacao]:
        return list(self._coordenacoes)

    def listar_especialidades(self) -> List[Especialidade]:
        return list(self._especialidades)

    def listar_patios(self) -> List[Patio]:
        return list(self._patios)

    def listar_ativos(self) -> List[Ativo]:
        return list(self._ativos)

    def listar_os_programadas(self) -> List[OsProgramada]:
        return list(self._os_programadas)
