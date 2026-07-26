"""Testes do catalogo real do "Relatorio de Atividades Diarias de Manutencao"
(Relatorio 1, codigos EE01-EE23), fornecido pelo responsavel pelo produto
em 2026-07-23 - ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md.
"""

from workforce_core.catalogo import (
    Categoria,
    ClassificacaoHH,
    catalogo_relatorio_1_manutencao,
    codigos_relatorio_1_por_tipo_registro,
)


def test_catalogo_relatorio_1_tem_23_codigos():
    # EE01-EE23 = 23 codigos catalogaveis. EE24 (Horas nao apontadas) nao
    # entra - ver ADR-0014.
    catalogo = catalogo_relatorio_1_manutencao()
    codigos = {e.codigo for e in catalogo.todos()}
    assert len(codigos) == 23
    assert "EE24" not in codigos
    assert {"EE01", "EE17", "EE22", "EE23"} <= codigos


def test_catalogo_relatorio_1_classificacao_hh_nao_definida():
    catalogo = catalogo_relatorio_1_manutencao()
    for entrada in catalogo.todos():
        assert entrada.classificacao_hh == ClassificacaoHH.NAO_DEFINIDO


def test_catalogo_relatorio_1_categorias_estruturais_corretas():
    catalogo = catalogo_relatorio_1_manutencao()
    # EE17 = atividade planejada (manutencao em equipamentos).
    assert catalogo.obter("EE17").categoria == Categoria.ATIVIDADE_PLANEJADA
    # EE22 = atendimento de falha (manutencao nao planejada).
    assert catalogo.obter("EE22").categoria == Categoria.ATENDIMENTO_FALHA
    # EE12/EE13/EE14 = os tres tipos de deslocamento.
    assert catalogo.obter("EE12").categoria == Categoria.DESLOCAMENTO_RODOVIARIO
    assert catalogo.obter("EE13").categoria == Categoria.DESLOCAMENTO_FERROVIARIO
    assert catalogo.obter("EE14").categoria == Categoria.DESLOCAMENTO_A_PE


def test_catalogo_relatorio_1_entrada_carrega_tipo_registro():
    # EntradaCatalogo.tipo_registro precisa bater com
    # codigos_relatorio_1_por_tipo_registro (mesma fonte,
    # _RELATORIO_1_ENTRADAS) - agora carregado no proprio objeto para o
    # catalogo dinamico (Incremento de catalogo real) nao precisar de uma
    # segunda fonte de verdade so pra saber o tipo de um codigo.
    catalogo = catalogo_relatorio_1_manutencao()
    assert catalogo.obter("EE02").tipo_registro == "pausa"
    assert catalogo.obter("EE01").tipo_registro == "evento_secundario"
    assert catalogo.obter("EE17").tipo_registro == "atividade"
    assert all(entrada.ativo for entrada in catalogo.todos())


def test_codigos_relatorio_1_por_tipo_registro_pausa():
    codigos_pausa = codigos_relatorio_1_por_tipo_registro("pausa")
    assert set(codigos_pausa) == {"EE02", "EE07", "EE11", "EE21", "EE23"}


def test_codigos_relatorio_1_por_tipo_registro_evento_secundario():
    codigos_evento = codigos_relatorio_1_por_tipo_registro("evento_secundario")
    assert set(codigos_evento) == {
        "EE01",
        "EE03",
        "EE04",
        "EE05",
        "EE06",
        "EE08",
        "EE09",
        "EE10",
        "EE12",
        "EE13",
        "EE14",
        "EE15",
        "EE16",
        "EE18",
        "EE19",
        "EE20",
    }


def test_codigos_relatorio_1_por_tipo_registro_atividade():
    assert set(codigos_relatorio_1_por_tipo_registro("atividade")) == {"EE17", "EE22"}


def test_codigos_relatorio_1_por_tipo_registro_cobre_todos_os_23_codigos():
    todos = (
        codigos_relatorio_1_por_tipo_registro("pausa")
        + codigos_relatorio_1_por_tipo_registro("evento_secundario")
        + codigos_relatorio_1_por_tipo_registro("atividade")
    )
    assert len(todos) == 23
    assert len(set(todos)) == 23  # nenhum codigo em mais de um tipo


def test_codigos_relatorio_1_por_tipo_registro_desconhecido_retorna_vazio():
    assert codigos_relatorio_1_por_tipo_registro("tipo_que_nao_existe") == []
