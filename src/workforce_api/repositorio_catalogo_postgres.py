"""Repositorio do catalogo de motivos em Postgres hospedado (catalogo
dinamico - docs/46_ADR_0019_CATALOGO_DINAMICO.md).

Mesmo espirito de repositorio_postgres.py (ADR-0017): schema minimo, uma
linha por motivo, upsert por chave natural (codigo), validacao de
estrutura feita pelo dominio (entrada_catalogo_de_dict), nao pelo banco.

Sem suite de teste de integracao real com Postgres neste repositorio
(sem servidor Postgres disponivel no ambiente de desenvolvimento) - so
validado por leitura de codigo. A API (workforce_api.app) e testada com
um repositorio falso em memoria injetado no lugar deste.
"""

from __future__ import annotations

from typing import List

import psycopg2

from workforce_core.catalogo import EntradaCatalogo, catalogo_relatorio_1_manutencao
from workforce_storage.serializacao import entrada_catalogo_de_dict, entrada_catalogo_para_dict

_CRIAR_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS motivos_catalogo (
    codigo TEXT PRIMARY KEY,
    descricao TEXT NOT NULL,
    categoria TEXT NULL,
    classificacao_hh TEXT NOT NULL DEFAULT 'NAO_DEFINIDO',
    tipo_registro TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class RepositorioCatalogoPostgres:
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
        """Popula a tabela com os 23 codigos reais do Relatorio 1 na
        primeira vez que o backend sobe com a tabela vazia - a interface
        de campo nunca deve ver um catalogo sem nenhum motivo."""
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM motivos_catalogo")
                (quantidade,) = cursor.fetchone()
        if quantidade == 0:
            for entrada in catalogo_relatorio_1_manutencao().todos():
                self.salvar(entrada)

    def salvar(self, entrada: EntradaCatalogo) -> None:
        """Upsert por codigo - reenviar o mesmo codigo nunca cria um
        segundo registro, mesma garantia de idempotencia do ADR-0003."""
        dados = entrada_catalogo_para_dict(entrada)
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO motivos_catalogo
                        (codigo, descricao, categoria, classificacao_hh, tipo_registro, ativo, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (codigo) DO UPDATE SET
                        descricao = EXCLUDED.descricao,
                        categoria = EXCLUDED.categoria,
                        classificacao_hh = EXCLUDED.classificacao_hh,
                        tipo_registro = EXCLUDED.tipo_registro,
                        ativo = EXCLUDED.ativo,
                        atualizado_em = now()
                    """,
                    [
                        dados["codigo"],
                        dados["descricao"],
                        dados["categoria"],
                        dados["classificacao_hh"],
                        dados["tipo_registro"],
                        dados["ativo"],
                    ],
                )
            conexao.commit()

    def listar(self, *, somente_ativos: bool = True) -> List[EntradaCatalogo]:
        query = (
            "SELECT codigo, descricao, categoria, classificacao_hh, tipo_registro, ativo "
            "FROM motivos_catalogo"
        )
        if somente_ativos:
            query += " WHERE ativo = true"
        query += " ORDER BY codigo"
        with self._conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(query)
                linhas = cursor.fetchall()
        return [
            entrada_catalogo_de_dict(
                {
                    "codigo": linha[0],
                    "descricao": linha[1],
                    "categoria": linha[2],
                    "classificacao_hh": linha[3],
                    "tipo_registro": linha[4],
                    "ativo": linha[5],
                }
            )
            for linha in linhas
        ]
