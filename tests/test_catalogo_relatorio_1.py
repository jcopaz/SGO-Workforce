"""Testes do catalogo real do "Relatorio de Atividades Diarias de Manutencao"
(Relatorio 1, codigos EE01-EE23), fornecido pelo responsavel pelo produto
em 2026-07-23 - ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md.

Renumerado e reclassificado (produtiva/improdutiva/nao computavel) em
2026-07-27 - ver docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md.
"""

from workforce_core.catalogo import (
    Categoria,
    ClassificacaoHH,
    catalogo_relatorio_1_manutencao,
    codigos_relatorio_1_por_tipo_registro,
)


def test_catalogo_relatorio_1_tem_23_codigos():
    # EE01-EE23 = 23 codigos catalogaveis (ADR-0023: antigo EE18 excluido
    # por duplicar EE21/Atendimento de Falha; antigo EE24 liberado e
    # reaproveitado como o novo EE23).
    catalogo = catalogo_relatorio_1_manutencao()
    codigos = {e.codigo for e in catalogo.todos()}
    assert len(codigos) == 23
    assert "EE24" not in codigos
    assert {"EE01", "EE17", "EE21", "EE23"} <= codigos


def test_catalogo_relatorio_1_classificacao_hh_validada(): # ADR-0023
    catalogo = catalogo_relatorio_1_manutencao()
    esperado = {
        "EE01": ClassificacaoHH.IMPRODUTIVA,
        "EE02": ClassificacaoHH.NAO_COMPUTAVEL,
        "EE03": ClassificacaoHH.IMPRODUTIVA,
        "EE04": ClassificacaoHH.IMPRODUTIVA,
        "EE05": ClassificacaoHH.IMPRODUTIVA,
        "EE06": ClassificacaoHH.IMPRODUTIVA,
        "EE07": ClassificacaoHH.IMPRODUTIVA,
        "EE08": ClassificacaoHH.IMPRODUTIVA,
        "EE09": ClassificacaoHH.IMPRODUTIVA,
        "EE10": ClassificacaoHH.IMPRODUTIVA,
        "EE11": ClassificacaoHH.PRODUTIVA,
        "EE12": ClassificacaoHH.PRODUTIVA,
        "EE13": ClassificacaoHH.PRODUTIVA,
        "EE14": ClassificacaoHH.PRODUTIVA,
        "EE15": ClassificacaoHH.PRODUTIVA,
        "EE16": ClassificacaoHH.IMPRODUTIVA,
        "EE17": ClassificacaoHH.PRODUTIVA,
        "EE18": ClassificacaoHH.PRODUTIVA,
        "EE19": ClassificacaoHH.PRODUTIVA,
        "EE20": ClassificacaoHH.PRODUTIVA,
        "EE21": ClassificacaoHH.PRODUTIVA,
        "EE22": ClassificacaoHH.PRODUTIVA,
        "EE23": ClassificacaoHH.PRODUTIVA,
    }
    for codigo, classificacao in esperado.items():
        assert catalogo.obter(codigo).classificacao_hh == classificacao, codigo
    # Nenhum codigo real do Relatorio 1 deveria continuar NAO_DEFINIDO
    # depois do ADR-0023.
    assert all(
        entrada.classificacao_hh != ClassificacaoHH.NAO_DEFINIDO for entrada in catalogo.todos()
    )


def test_catalogo_relatorio_1_categorias_estruturais_corretas():
    catalogo = catalogo_relatorio_1_manutencao()
    # EE17 = atividade planejada (manutencao programada).
    assert catalogo.obter("EE17").categoria == Categoria.ATIVIDADE_PLANEJADA
    # EE21 = atendimento de falha (renumerado de EE22 no ADR-0023).
    assert catalogo.obter("EE21").categoria == Categoria.ATENDIMENTO_FALHA
    # EE23 = manutencao programada nao concluida (novo no ADR-0023).
    assert catalogo.obter("EE23").categoria == Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA
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
    assert catalogo.obter("EE23").tipo_registro == "atividade"
    assert all(entrada.ativo for entrada in catalogo.todos())


def test_codigos_relatorio_1_por_tipo_registro_pausa():
    codigos_pausa = codigos_relatorio_1_por_tipo_registro("pausa")
    assert set(codigos_pausa) == {"EE02", "EE07", "EE11", "EE20", "EE22"}


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
    }


def test_codigos_relatorio_1_por_tipo_registro_atividade():
    # EE23 (Manutencao Programada Nao Concluida) e nova no ADR-0023.
    assert set(codigos_relatorio_1_por_tipo_registro("atividade")) == {"EE17", "EE21", "EE23"}


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
