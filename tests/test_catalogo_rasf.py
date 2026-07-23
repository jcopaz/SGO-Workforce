"""Testes do Incremento 6: carregador do catalogo derivado do RASF.

Le os CSVs reais em catalogos/ (raiz do repositorio) - nao sao fixtures
fabricadas, sao os dados extraidos do RASF ja versionados no projeto.
"""

from pathlib import Path

from workforce_storage.catalogo_rasf import (
    apenas_ativos,
    carregar_catalogo_rasf,
    carregar_catalogos_rasf,
    item_por_codigo,
    item_por_valor,
)

DIRETORIO_CATALOGOS = Path(__file__).resolve().parents[1] / "catalogos"


def test_carregar_catalogo_sintomas_real():
    itens = carregar_catalogo_rasf(DIRETORIO_CATALOGOS / "sintomas.csv")
    # catalogos/README.md declara 53 sintomas distintos.
    assert len(itens) == 53
    assert all(item.codigo_interno for item in itens)
    assert all(item.valor for item in itens)
    assert all(isinstance(item.frequencia, int) for item in itens)
    assert all(isinstance(item.ativo, bool) for item in itens)


def test_carregar_catalogo_sistemas_real():
    itens = carregar_catalogo_rasf(DIRETORIO_CATALOGOS / "sistemas.csv")
    # catalogos/README.md declara 5 sistemas.
    assert len(itens) == 5
    valores = {item.valor for item in itens}
    assert "SINALIZAÇÃO" in valores


def test_carregar_todos_os_catalogos_rasf():
    catalogos = carregar_catalogos_rasf(DIRETORIO_CATALOGOS)
    chaves_esperadas = {
        "sintomas",
        "sistemas",
        "tipos_solicitacao",
        "impactos",
        "componentes_causadores",
        "6m_nivel_1",
        "6m_nivel_2",
        "6m_nivel_3",
    }
    assert chaves_esperadas <= set(catalogos.keys())
    assert len(catalogos["tipos_solicitacao"]) == 10
    assert len(catalogos["impactos"]) == 4
    assert len(catalogos["componentes_causadores"]) == 148


def test_carregar_catalogos_de_diretorio_sem_arquivos(tmp_path):
    catalogos = carregar_catalogos_rasf(tmp_path)
    assert catalogos == {}


def test_item_por_codigo_e_por_valor():
    itens = carregar_catalogo_rasf(DIRETORIO_CATALOGOS / "sistemas.csv")
    item = item_por_codigo(itens, "1")
    assert item is not None
    assert item.valor == "SINALIZAÇÃO"

    mesmo_item = item_por_valor(itens, "SINALIZAÇÃO")
    assert mesmo_item == item

    assert item_por_codigo(itens, "não-existe") is None
    assert item_por_valor(itens, "não-existe") is None


def test_apenas_ativos_filtra_corretamente():
    itens = carregar_catalogo_rasf(DIRETORIO_CATALOGOS / "sintomas.csv")
    ativos = apenas_ativos(itens)
    assert all(item.ativo for item in ativos)
    assert len(ativos) <= len(itens)
