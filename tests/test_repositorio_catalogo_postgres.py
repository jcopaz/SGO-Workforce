"""Testes do reparo retroativo de tipo_evento_secundario
(src/workforce_api/repositorio_catalogo_postgres.py).

Bug real de producao (2026-07-29): o ALTER TABLE que criou a coluna
`tipo_evento_secundario` (ADR-0024) nunca preencheu dado retroativo, e o
reseed automatico (`_semear_se_vazio`) so roda com a tabela vazia - em
qualquer banco que ja tinha o catalogo do ADR-0014/0019 antes desse
incremento, os 15 codigos "evento_secundario" ficaram permanentemente com
`tipo_evento_secundario` NULL, e a interface de campo travava com
"O tipo do evento secundario (DESLOCAMENTO/ESPERA/APOIO) e obrigatorio."
toda vez que o colaborador tentava iniciar deslocamento/espera/apoio.

Sem Postgres real disponivel neste ambiente (mesma limitacao documentada
no modulo testado) - `_mapeamento_reparo_tipo_evento_secundario` e testada
como funcao pura, e `_reparar_tipo_evento_secundario` e testada com uma
conexao/cursor falsos (sem rede), sem instanciar o repositorio inteiro
(que exigiria Postgres de verdade em `__init__`).
"""

from __future__ import annotations

from workforce_api.repositorio_catalogo_postgres import (
    RepositorioCatalogoPostgres,
    _mapeamento_reparo_tipo_evento_secundario,
)
from workforce_core.catalogo import codigos_relatorio_1_por_tipo_registro


class _CursorFalso:
    def __init__(self, registro_execucoes):
        self._registro_execucoes = registro_execucoes

    def executemany(self, sql, seq_params):
        for params in seq_params:
            self._registro_execucoes.append((sql, tuple(params)))

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _ConexaoFalsa:
    def __init__(self):
        self.executados = []
        self.commitada = False

    def cursor(self):
        return _CursorFalso(self.executados)

    def commit(self):
        self.commitada = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _codigos_com_tipo_evento_secundario_esperados():
    # 15 codigos "evento_secundario" (ADR-0024) + 5 codigos "pausa" que
    # ganharam uso avulso no ADR-0030 (EE02/EE07/EE11/EE20/EE22).
    return set(codigos_relatorio_1_por_tipo_registro("evento_secundario")) | {
        "EE02",
        "EE07",
        "EE11",
        "EE20",
        "EE22",
    }


def test_mapeamento_reparo_cobre_os_20_codigos_com_tipo_evento_secundario():
    mapeamento = _mapeamento_reparo_tipo_evento_secundario()
    codigos = {codigo for _tipo, codigo in mapeamento}
    assert codigos == _codigos_com_tipo_evento_secundario_esperados()
    assert len(mapeamento) == 20


def test_mapeamento_reparo_inclui_ee01_como_apoio():
    # EE01 "Preparacao para jornada" - classificado como APOIO por decisao
    # do responsavel pelo produto em 2026-07-28 (ADR-0024). E exatamente o
    # codigo que apareceu selecionado por padrao no bug real de producao.
    mapeamento = dict((codigo, tipo) for tipo, codigo in _mapeamento_reparo_tipo_evento_secundario())
    assert mapeamento["EE01"] == "APOIO"


def test_reparar_tipo_evento_secundario_atualiza_so_os_15_codigos_com_guarda_de_null(monkeypatch):
    conexao_falsa = _ConexaoFalsa()
    repositorio = RepositorioCatalogoPostgres.__new__(RepositorioCatalogoPostgres)
    monkeypatch.setattr(repositorio, "_conectar", lambda: conexao_falsa)

    repositorio._reparar_tipo_evento_secundario()

    assert conexao_falsa.commitada
    assert len(conexao_falsa.executados) == 20
    for sql, params in conexao_falsa.executados:
        assert "SET tipo_evento_secundario" in sql
        assert "WHERE codigo = %s AND tipo_evento_secundario IS NULL" in sql
        assert len(params) == 2  # (tipo, codigo)

    codigos_atualizados = {params[1] for _sql, params in conexao_falsa.executados}
    assert codigos_atualizados == _codigos_com_tipo_evento_secundario_esperados()
