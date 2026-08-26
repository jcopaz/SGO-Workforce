"""Repositorio do cadastro de patios em Postgres hospedado (ADR-0072).

Mesmo espirito de repositorio_catalogo_postgres.py (ADR-0019): schema
minimo, uma linha por patio, upsert por chave natural (codigo), validacao
de estrutura feita pelo dominio (patio_de_dict), nao pelo banco.

Sem suite de teste de integracao real com Postgres neste repositorio (sem
servidor Postgres disponivel no ambiente de desenvolvimento) - so validado
por leitura de codigo. A API (workforce_api.app) e testada com um
repositorio falso em memoria injetado no lugar deste.
"""

from __future__ import annotations

from typing import List

import psycopg2

from workforce_core.patio import Patio
from workforce_storage.serializacao import patio_de_dict, patio_para_dict

_CRIAR_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS wf_patios (
    codigo TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    coordenacao TEXT NOT NULL DEFAULT '',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

# Semente real: os 3 primeiros patios cadastrados, coordenacao Piacaguera,
# coordenadas informadas pelo responsavel pelo produto em 2026-08-26 -
# nenhum valor inventado pelo agente. Mesmo padrao de
# RepositorioCatalogoPostgres._semear_se_vazio (so roda com a tabela
# vazia, nunca sobrescreve edicao manual feita depois pelo painel).
_PATIOS_SEMENTE = [
    Patio(
        codigo="IPN",
        nome="Pátio Prainha",
        coordenacao="Piaçaguera",
        latitude=-23.948095774842265,
        longitude=-46.30579661328678,
    ),
    Patio(
        codigo="ICQ",
        nome="Pátio Casqueiro",
        coordenacao="Piaçaguera",
        latitude=-23.91531040683147,
        longitude=-46.41890410191962,
    ),
    # Codigo originalmente informado como "IQC - Patio Cascqueiro" (erro de
    # transposicao/digitacao) - responsavel pelo produto confirmou em
    # 2026-08-26 que IQC na verdade e' outro local ("Extensao Cubatao 1"),
    # coordenada quase identica (~1m) a do ICQ acima - marcadores ficam
    # sobrepostos no mapa, confirmado como esperado (extensao colada ao
    # patio principal), nao erro de copia/cola.
    Patio(
        codigo="IQC",
        nome="Extensão Cubatão 1",
        coordenacao="Piaçaguera",
        latitude=-23.91530182548477,
        longitude=-46.41890965645514,
    ),
]


class RepositorioPatiosPostgres:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._garantir_tabela()
        self._semear_se_vazio()

    def _conectar(self):
        return psycopg2.connect(self._dsn)

    def _garantir_tabela(self) -> None:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(_CRIAR_TABELA_SQL)
            conexao.commit()

    def _semear_se_vazio(self) -> None:
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM wf_patios")
                (quantidade,) = cursor.fetchone()
        if quantidade == 0:
            for patio in _PATIOS_SEMENTE:
                self.salvar(patio)

    def salvar(self, patio: Patio) -> None:
        """Upsert por codigo - reenviar o mesmo codigo nunca cria um segundo
        registro, mesma garantia de idempotencia do ADR-0003."""
        dados = patio_para_dict(patio)
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO wf_patios
                        (codigo, nome, coordenacao, latitude, longitude, ativo, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (codigo) DO UPDATE SET
                        nome = EXCLUDED.nome,
                        coordenacao = EXCLUDED.coordenacao,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        ativo = EXCLUDED.ativo,
                        atualizado_em = now()
                    """,
                    [
                        dados["codigo"],
                        dados["nome"],
                        dados["coordenacao"],
                        dados["latitude"],
                        dados["longitude"],
                        dados["ativo"],
                    ],
                )
            conexao.commit()

    def listar(self, *, somente_ativos: bool = True) -> List[Patio]:
        query = "SELECT codigo, nome, coordenacao, latitude, longitude, ativo FROM wf_patios"
        if somente_ativos:
            query += " WHERE ativo = true"
        query += " ORDER BY codigo"
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(query)
                linhas = cursor.fetchall()
        return [
            patio_de_dict(
                {
                    "codigo": linha[0],
                    "nome": linha[1],
                    "coordenacao": linha[2],
                    "latitude": linha[3],
                    "longitude": linha[4],
                    "ativo": linha[5],
                }
            )
            for linha in linhas
        ]
