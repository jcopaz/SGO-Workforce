"""Repositorio de jornadas em Postgres hospedado (Incremento de sincronizacao real).

Mesma forma publica de workforce_storage.RepositorioJornadaArquivo
(salvar/carregar/listar_ids/listar_abertas), para que o backend possa
reaproveitar as mesmas funcoes de serializacao ja testadas
(workforce_storage.serializacao) sem duplicar o contrato de campos.

Schema minimo, sem modelar cada campo da jornada relacionalmente - mesmo
espirito provisorio do ADR-0002 (persistencia local em arquivo): a jornada
inteira vira uma linha com o dict ja serializado em JSONB, e a validacao de
estrutura continua sendo feita pelo dominio (jornada_de_dict), nao pelo
banco. Ver docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md.

Nao ha suite de teste de integracao real com Postgres neste repositorio
(sem servidor Postgres disponivel no ambiente de desenvolvimento) - so
validado por leitura de codigo. A API (workforce_api.app) e testada com
RepositorioJornadaArquivo injetado no lugar deste repositorio.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

import psycopg2
import psycopg2.extras

from workforce_core.entities import Jornada
from workforce_core.enums import EstadoJornada

from workforce_storage.exceptions import ArquivoCorrompidoError, JornadaNaoEncontradaError
from workforce_storage.serializacao import jornada_de_dict, jornada_para_dict

_CRIAR_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS jornadas (
    id UUID PRIMARY KEY,
    dados JSONB NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class RepositorioJornadaPostgres:
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

    def salvar(self, jornada: Jornada) -> None:
        """Grava a jornada (upsert por id) - reenviar a mesma jornada nunca
        cria um segundo registro, mesma garantia de idempotencia do
        ADR-0003."""
        dados = jornada_para_dict(jornada)
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO jornadas (id, dados, atualizado_em)
                    VALUES (%s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                        SET dados = EXCLUDED.dados, atualizado_em = now()
                    """,
                    [str(jornada.id), psycopg2.extras.Json(dados)],
                )
            conexao.commit()

    def carregar(self, jornada_id: UUID) -> Jornada:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT dados FROM jornadas WHERE id = %s", [str(jornada_id)]
                )
                linha = cursor.fetchone()
        if linha is None:
            raise JornadaNaoEncontradaError(
                f"Nao existe jornada persistida com id {jornada_id}."
            )
        try:
            return jornada_de_dict(linha[0])
        except (KeyError, ValueError, TypeError) as exc:
            raise ArquivoCorrompidoError(
                f"Registro de jornada com estrutura invalida: {jornada_id}"
            ) from exc

    def listar_ids(self) -> List[UUID]:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT id FROM jornadas")
                linhas = cursor.fetchall()
        return [UUID(str(linha[0])) for linha in linhas]

    def listar_abertas(self) -> List[Jornada]:
        abertas: List[Jornada] = []
        for jornada_id in self.listar_ids():
            try:
                jornada = self.carregar(jornada_id)
            except ArquivoCorrompidoError:
                continue
            if jornada.estado == EstadoJornada.ABERTA:
                abertas.append(jornada)
        return abertas
