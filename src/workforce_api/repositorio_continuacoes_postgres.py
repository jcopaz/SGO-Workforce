"""Repositorio de continuacoes de atendimento de falha em Postgres
hospedado (D4 - "Falha nao Concluida", transferencia entre colaboradores,
ver docs/49_ADR_0022_GPS_FOTO_TRANSFERENCIA_ATENDIMENTO_FALHA.md).

Mesmo espirito de repositorio_postgres.py/repositorio_catalogo_postgres.py
(ADR-0017/ADR-0019): schema minimo, validacao de estrutura feita pela
camada de API, nao pelo banco.

Sem suite de teste de integracao real com Postgres neste repositorio (sem
servidor Postgres disponivel no ambiente de desenvolvimento) - so validado
por leitura de codigo. A API (workforce_api.app) e testada com um
repositorio falso em memoria injetado no lugar deste.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID, uuid4

import psycopg2
import psycopg2.extras

_CRIAR_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS continuacoes_falha (
    id UUID PRIMARY KEY,
    matricula_destino TEXT NOT NULL,
    dados JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    consumida BOOLEAN NOT NULL DEFAULT false
)
"""


class RepositorioContinuacoesFalhaPostgres:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._garantir_tabela()

    def _conectar(self):
        return psycopg2.connect(self._dsn)

    def _garantir_tabela(self) -> None:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(_CRIAR_TABELA_SQL)
            conexao.commit()

    def criar(self, matricula_destino: str, dados: Dict[str, Any]) -> UUID:
        continuacao_id = uuid4()
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO continuacoes_falha (id, matricula_destino, dados, criado_em, consumida)
                    VALUES (%s, %s, %s, now(), false)
                    """,
                    [str(continuacao_id), matricula_destino, psycopg2.extras.Json(dados)],
                )
            conexao.commit()
        return continuacao_id

    def listar_pendentes(self, matricula_destino: str) -> List[Dict[str, Any]]:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, dados FROM continuacoes_falha
                    WHERE matricula_destino = %s AND consumida = false
                    ORDER BY criado_em
                    """,
                    [matricula_destino],
                )
                linhas = cursor.fetchall()
        return [{"id": str(linha[0]), "dados": linha[1]} for linha in linhas]

    def marcar_consumida(self, continuacao_id: UUID) -> None:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "UPDATE continuacoes_falha SET consumida = true WHERE id = %s",
                    [str(continuacao_id)],
                )
            conexao.commit()
