"""Repositorio de pulsos GPS em Postgres hospedado (Fase 1 da captacao real
de geolocalizacao - ADR-0042/0043).

Mesma forma publica de workforce_storage.RepositorioPulsosGpsArquivo
(gravar_lote/ler_pulsos), para o endpoint POST/GET /pulsos poder tratar as
duas implementacoes de forma intercambiavel via Depends - mesmo padrao ja
usado entre RepositorioJornadaArquivo/RepositorioJornadaPostgres.

Schema minimo, mesmo espirito provisorio de repositorio_postgres.py: o
pulso inteiro vira uma linha com o dict ja serializado em JSONB
(pulso_gps_para_dict/pulso_gps_de_dict), sem migracao versionada
(CREATE TABLE IF NOT EXISTS a cada boot, padrao ja aceito no ADR-0017).
`jornada_id` fica em coluna propria (fora do JSONB) so pra indexar o filtro
de GET /pulsos?jornada_id=... - nao e uma normalizacao de verdade.

Nao ha suite de teste de integracao real com Postgres neste repositorio
(sem servidor Postgres disponivel no ambiente de desenvolvimento) - so
validado por leitura de codigo, mesma ressalva de repositorio_postgres.py.
A API (workforce_api.app) e testada com RepositorioPulsosGpsArquivo
injetado no lugar deste repositorio.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

import psycopg2
import psycopg2.extras

from workforce_core.entities import PulsoGps

from workforce_storage.serializacao import pulso_gps_de_dict, pulso_gps_para_dict

_CRIAR_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS pulsos_gps (
    id UUID PRIMARY KEY,
    jornada_id UUID NOT NULL,
    dados JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""
_CRIAR_INDICE_SQL = """
CREATE INDEX IF NOT EXISTS idx_pulsos_gps_jornada_id ON pulsos_gps (jornada_id)
"""


class RepositorioPulsosGpsPostgres:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._garantir_tabela()

    def _conectar(self):
        return psycopg2.connect(self._dsn)

    def _garantir_tabela(self) -> None:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(_CRIAR_TABELA_SQL)
                cursor.execute(_CRIAR_INDICE_SQL)
            conexao.commit()

    def gravar_lote(self, pulsos: List[PulsoGps]) -> None:
        """Grava varios pulsos numa unica transacao (upsert por id) -
        reenviar o mesmo lote (ack perdido do lado do cliente) nunca
        duplica, mesma garantia de idempotencia de RepositorioJornadaPostgres.salvar.

        Um pulso e um fato imutavel (a posicao capturada num instante) -
        diferente de jornada, que e emendada ao longo do tempo - por isso o
        conflito so atualiza `dados` (por seguranca, caso o mesmo id chegue
        com um payload levemente diferente por algum motivo), nunca
        `criado_em`, que fica fixo no primeiro recebimento."""
        if not pulsos:
            return
        argumentos = [
            (str(pulso.id), str(pulso.jornada_id), psycopg2.extras.Json(pulso_gps_para_dict(pulso)))
            for pulso in pulsos
        ]
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO pulsos_gps (id, jornada_id, dados)
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE
                        SET dados = EXCLUDED.dados
                    """,
                    argumentos,
                    template="(%s, %s, %s)",
                )
            conexao.commit()

    def ler_pulsos(self, jornada_id: UUID) -> List[PulsoGps]:
        """Le todos os pulsos da jornada, em ordem cronologica pelo
        timestamp do proprio dispositivo (nao pela ordem de insercao no
        banco) - um lote atrasado que chega fora de ordem nao embaralha a
        trajetoria."""
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT dados FROM pulsos_gps
                    WHERE jornada_id = %s
                    ORDER BY dados->>'timestamp_dispositivo'
                    """,
                    [str(jornada_id)],
                )
                linhas = cursor.fetchall()
        return [pulso_gps_de_dict(linha[0]) for linha in linhas]
