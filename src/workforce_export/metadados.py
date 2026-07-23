"""Metadados obrigatorios de toda exportacao (Incremento 11).

docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md secao 3.7 (regra
inegociavel): "Toda exportacao devera possuir data de geracao, periodo,
filtros e usuario responsavel." Repetido em
docs/14_EXPORTACOES.md, secao "Regras".

`usuario_responsavel` e sempre um parametro explicito - nao ha
autenticacao no sistema ainda (nenhum incremento implementou login), entao
nao existe um "usuario logado" para preencher sozinho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MetadadosExportacao:
    usuario_responsavel: str
    filtros: Dict[str, Any] = field(default_factory=dict)
    periodo_inicio: Optional[datetime] = None
    periodo_fim: Optional[datetime] = None
    data_geracao: datetime = field(default_factory=_agora_utc)

    def __post_init__(self) -> None:
        if not self.usuario_responsavel:
            raise ValueError(
                "usuario_responsavel e obrigatorio em toda exportacao "
                "(docs/27 secao 3.7)."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usuario_responsavel": self.usuario_responsavel,
            "filtros": dict(self.filtros),
            "periodo_inicio": self.periodo_inicio.isoformat() if self.periodo_inicio else None,
            "periodo_fim": self.periodo_fim.isoformat() if self.periodo_fim else None,
            "data_geracao": self.data_geracao.isoformat(),
        }

    def sufixo_nome_arquivo(self) -> str:
        """"...inclui periodo e geracao" (docs/14) - sufixo pronto para compor nomes de arquivo."""
        periodo = "todos"
        if self.periodo_inicio and self.periodo_fim:
            periodo = f"{self.periodo_inicio:%Y%m%d}-{self.periodo_fim:%Y%m%d}"
        geracao = self.data_geracao.strftime("%Y%m%dT%H%M%SZ")
        return f"{periodo}_gerado-{geracao}"
