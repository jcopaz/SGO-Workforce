"""Infraestrutura de catalogo do Incremento 5.

O catalogo oficial de motivos, e a classificacao de cada um como produtivo,
improdutivo ou nao computavel, sao decisoes de negocio explicitamente
pendentes (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 6 itens
6-9, e secao 15.3 "Antes do Incremento 5"). Este modulo fornece apenas a
estrutura tecnica para representar essas decisoes quando forem tomadas -
nao inventa nenhum valor de classificacao definitivo.

O vocabulario de Categoria vem de docs/07_MOTOR_EVENTOS_E_HH.md ("Categorias
iniciais"), que ja fazia parte da leitura obrigatoria do projeto - nao e uma
invencao deste incremento.

Ver docs/32_ADR_0005_CATALOGO_DESLOCAMENTO_ESPERA_APOIO.md para o registro
completo da decisao.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Categoria(str, Enum):
    """Categorias iniciais de evento, conforme docs/07_MOTOR_EVENTOS_E_HH.md."""

    ATIVIDADE_PLANEJADA = "ATIVIDADE_PLANEJADA"
    ATENDIMENTO_FALHA = "ATENDIMENTO_FALHA"
    DESLOCAMENTO_RODOVIARIO = "DESLOCAMENTO_RODOVIARIO"
    DESLOCAMENTO_FERROVIARIO = "DESLOCAMENTO_FERROVIARIO"
    REFEICAO = "REFEICAO"
    DDS = "DDS"
    REUNIAO = "REUNIAO"
    TREINAMENTO = "TREINAMENTO"
    AGUARDANDO_MATERIAL = "AGUARDANDO_MATERIAL"
    AGUARDANDO_INTERVALO_LIBERACAO = "AGUARDANDO_INTERVALO_LIBERACAO"
    APOIO_OPERACIONAL = "APOIO_OPERACIONAL"
    ATIVIDADE_ADMINISTRATIVA = "ATIVIDADE_ADMINISTRATIVA"
    OUTROS_CATALOGADOS = "OUTROS_CATALOGADOS"


class ClassificacaoHH(str, Enum):
    """Classificacao de um motivo para fins de HH.

    NAO_DEFINIDO e o valor padrao de qualquer entrada de catalogo ate que o
    responsavel pelo produto valide a classificacao definitiva - nunca deve
    ser interpretado como "improdutivo" nem "produtivo" por omissao.
    """

    PRODUTIVA = "PRODUTIVA"
    IMPRODUTIVA = "IMPRODUTIVA"
    NAO_COMPUTAVEL = "NAO_COMPUTAVEL"
    NAO_DEFINIDO = "NAO_DEFINIDO"


@dataclass(frozen=True)
class EntradaCatalogo:
    codigo: str
    descricao: str
    categoria: Optional[Categoria] = None
    classificacao_hh: ClassificacaoHH = ClassificacaoHH.NAO_DEFINIDO


class CatalogoMotivos:
    """Registro em memoria de motivos catalogados.

    Nao ha ainda fonte oficial (planilha, tabela de banco, endpoint) nem
    processo de aprovacao/vigencia - isso e decisao pendente da secao 15.3.
    Esta classe apenas organiza o que ja existe para uso pelo motor e pelos
    relatorios, sem se comprometer com nenhuma fonte definitiva.
    """

    def __init__(self) -> None:
        self._entradas: Dict[str, EntradaCatalogo] = {}

    def registrar(self, entrada: EntradaCatalogo) -> None:
        self._entradas[entrada.codigo] = entrada

    def obter(self, codigo: str) -> Optional[EntradaCatalogo]:
        return self._entradas.get(codigo)

    def todos(self) -> List[EntradaCatalogo]:
        return list(self._entradas.values())


def catalogo_padrao() -> CatalogoMotivos:
    """Catalogo minimo de motivos de teste, para desenvolvimento e piloto tecnico.

    Nenhuma destas entradas e um motivo oficial validado com a operacao -
    todas tem classificacao_hh=NAO_DEFINIDO. PAUSA_TESTE segue a decisao
    explicita da secao 5.3 do alinhamento oficial (Incremento 1); os demais
    (*_TESTE) estendem o mesmo padrao por analogia para permitir testar o
    motor de Deslocamento/Espera/Apoio deste incremento.
    """
    catalogo = CatalogoMotivos()
    catalogo.registrar(
        EntradaCatalogo(
            codigo="PAUSA_TESTE",
            descricao="Motivo de pausa provisorio para testes (ADR-0001).",
            categoria=None,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="DESLOCAMENTO_TESTE",
            descricao="Motivo de deslocamento provisorio para testes (ADR-0005).",
            categoria=Categoria.DESLOCAMENTO_RODOVIARIO,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="ESPERA_TESTE",
            descricao="Motivo de espera provisorio para testes (ADR-0005).",
            categoria=Categoria.AGUARDANDO_MATERIAL,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="APOIO_TESTE",
            descricao="Motivo de apoio provisorio para testes (ADR-0005).",
            categoria=Categoria.APOIO_OPERACIONAL,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    return catalogo
