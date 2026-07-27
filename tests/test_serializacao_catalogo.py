"""Testes de workforce_storage.serializacao para EntradaCatalogo (catalogo
dinamico - docs/46_ADR_0019_CATALOGO_DINAMICO.md).
"""

from workforce_core.catalogo import Categoria, ClassificacaoHH, EntradaCatalogo
from workforce_core.enums import TipoEventoSecundario
from workforce_storage.serializacao import entrada_catalogo_de_dict, entrada_catalogo_para_dict


def test_entrada_catalogo_round_trip_com_categoria():
    entrada = EntradaCatalogo(
        codigo="EE02",
        descricao="Refeição 1 hora",
        categoria=Categoria.REFEICAO,
        classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        tipo_registro="pausa",
        ativo=True,
    )

    dados = entrada_catalogo_para_dict(entrada)
    reconstruida = entrada_catalogo_de_dict(dados)

    assert reconstruida == entrada


def test_entrada_catalogo_round_trip_sem_categoria():
    entrada = EntradaCatalogo(codigo="X", descricao="Exemplo", tipo_registro="pausa")

    dados = entrada_catalogo_para_dict(entrada)
    assert dados["categoria"] is None

    reconstruida = entrada_catalogo_de_dict(dados)
    assert reconstruida.categoria is None


def test_entrada_catalogo_de_dict_usa_defaults_para_campos_ausentes():
    # Compatibilidade retroativa: um dict so com codigo/descricao (formato
    # minimo) ainda deve reconstruir uma EntradaCatalogo valida.
    entrada = entrada_catalogo_de_dict({"codigo": "EE99", "descricao": "Teste"})

    assert entrada.categoria is None
    assert entrada.classificacao_hh == ClassificacaoHH.NAO_DEFINIDO
    assert entrada.tipo_registro == "pausa"
    assert entrada.ativo is True


def test_entrada_catalogo_para_dict_inclui_inativo():
    entrada = EntradaCatalogo(codigo="EE05", descricao="Desativado", ativo=False)
    dados = entrada_catalogo_para_dict(entrada)
    assert dados["ativo"] is False


def test_entrada_catalogo_round_trip_com_tipo_evento_secundario():
    entrada = EntradaCatalogo(
        codigo="EE12",
        descricao="Deslocamento rodoviário",
        categoria=Categoria.DESLOCAMENTO_RODOVIARIO,
        tipo_registro="evento_secundario",
        tipo_evento_secundario=TipoEventoSecundario.DESLOCAMENTO,
    )

    dados = entrada_catalogo_para_dict(entrada)
    assert dados["tipo_evento_secundario"] == "DESLOCAMENTO"

    reconstruida = entrada_catalogo_de_dict(dados)
    assert reconstruida == entrada


def test_entrada_catalogo_de_dict_tipo_evento_secundario_ausente_vira_none():
    # Compatibilidade retroativa: linhas gravadas antes deste incremento
    # (sem a coluna) continuam reconstruindo normalmente.
    entrada = entrada_catalogo_de_dict({"codigo": "EE02", "descricao": "Refeição 1 hora"})
    assert entrada.tipo_evento_secundario is None
