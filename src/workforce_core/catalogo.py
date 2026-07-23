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
    """Categorias iniciais de evento, conforme docs/07_MOTOR_EVENTOS_E_HH.md,
    estendidas em 2026-07-23 com as categorias do "Relatorio de Atividades
    Diarias de Manutencao" (Relatorio 1, codigos EE01-EE24) fornecido pelo
    responsavel pelo produto - ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md.
    """

    ATIVIDADE_PLANEJADA = "ATIVIDADE_PLANEJADA"
    ATENDIMENTO_FALHA = "ATENDIMENTO_FALHA"
    DESLOCAMENTO_RODOVIARIO = "DESLOCAMENTO_RODOVIARIO"
    DESLOCAMENTO_FERROVIARIO = "DESLOCAMENTO_FERROVIARIO"
    DESLOCAMENTO_A_PE = "DESLOCAMENTO_A_PE"
    REFEICAO = "REFEICAO"
    DDS = "DDS"
    REUNIAO = "REUNIAO"
    TREINAMENTO = "TREINAMENTO"
    AGUARDANDO_MATERIAL = "AGUARDANDO_MATERIAL"
    AGUARDANDO_INTERVALO_LIBERACAO = "AGUARDANDO_INTERVALO_LIBERACAO"
    APOIO_OPERACIONAL = "APOIO_OPERACIONAL"
    ATIVIDADE_ADMINISTRATIVA = "ATIVIDADE_ADMINISTRATIVA"
    OUTROS_CATALOGADOS = "OUTROS_CATALOGADOS"

    # Categorias do Relatorio 1 (EE01-EE24) sem correspondencia acima.
    PREPARACAO_JORNADA = "PREPARACAO_JORNADA"
    AGUARDANDO_CCO = "AGUARDANDO_CCO"
    TREM_PARADO_FRENTE_SERVICO = "TREM_PARADO_FRENTE_SERVICO"
    RESTRICAO_INFRAESTRUTURA = "RESTRICAO_INFRAESTRUTURA"
    SERVICO_INTERNO_COORDENACAO = "SERVICO_INTERNO_COORDENACAO"
    TRABALHO_NAO_DISTRIBUIDO = "TRABALHO_NAO_DISTRIBUIDO"
    AGUARDANDO_SEQUENCIA_SERVICO = "AGUARDANDO_SEQUENCIA_SERVICO"
    CONSULTA_DOCUMENTACAO_TECNICA = "CONSULTA_DOCUMENTACAO_TECNICA"
    PREPARAR_ATIVIDADE = "PREPARAR_ATIVIDADE"
    DESMONTAR_ATIVIDADE = "DESMONTAR_ATIVIDADE"
    CARREGAR_VEICULO = "CARREGAR_VEICULO"
    DESCARREGAR_VEICULO = "DESCARREGAR_VEICULO"
    SMS = "SMS"


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
    # Motivos de pausa de exemplo, adicionados a pedido do responsavel pelo
    # produto em 2026-07-23 apos o primeiro teste manual da interface de
    # campo (ver ADR-0005, secao "Atualizacao"). Usam a categoria ja
    # documentada em docs/07_MOTOR_EVENTOS_E_HH.md, mas continuam sendo
    # exemplos ilustrativos - nao o catalogo oficial validado com a
    # operacao, por isso classificacao_hh permanece NAO_DEFINIDO.
    catalogo.registrar(
        EntradaCatalogo(
            codigo="REFEICAO",
            descricao="Pausa para refeicao (exemplo de motivo, nao oficial).",
            categoria=Categoria.REFEICAO,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="DDS",
            descricao="Dialogo Diario de Seguranca (exemplo de motivo, nao oficial).",
            categoria=Categoria.DDS,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="REUNIAO",
            descricao="Reuniao (exemplo de motivo, nao oficial).",
            categoria=Categoria.REUNIAO,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    catalogo.registrar(
        EntradaCatalogo(
            codigo="TREINAMENTO",
            descricao="Treinamento (exemplo de motivo, nao oficial).",
            categoria=Categoria.TREINAMENTO,
            classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
        )
    )
    return catalogo


# Codigo EE -> (descricao exata do formulario, categoria, tipo de registro).
# "tipo_registro" indica como o codigo se encaixa no motor de dominio hoje:
# - "atividade": e a propria Atividade (nao e um motivo de pausa/evento);
# - "pausa": motivo de Pausa (interrompe uma Atividade em andamento);
# - "evento_secundario": motivo de Deslocamento/Espera/Apoio (vinculado
#   diretamente a Jornada, mutuamente exclusivo com a Atividade principal).
# Ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md para a
# justificativa codigo a codigo.
_RELATORIO_1_ENTRADAS = [
    ("EE01", "Preparação para jornada", Categoria.PREPARACAO_JORNADA, "evento_secundario"),
    ("EE02", "Refeição 1 hora", Categoria.REFEICAO, "pausa"),
    ("EE03", "Aguardando CCO", Categoria.AGUARDANDO_CCO, "evento_secundario"),
    ("EE04", "Falta de ferramenta ou material", Categoria.AGUARDANDO_MATERIAL, "evento_secundario"),
    ("EE05", "Trem parado na frente de serviço", Categoria.TREM_PARADO_FRENTE_SERVICO, "evento_secundario"),
    ("EE06", "Restrição de infraestrutura", Categoria.RESTRICAO_INFRAESTRUTURA, "evento_secundario"),
    ("EE07", "Reunião ou ADM", Categoria.REUNIAO, "pausa"),
    ("EE08", "Serviço interno da coordenação", Categoria.SERVICO_INTERNO_COORDENACAO, "evento_secundario"),
    ("EE09", "Trabalho não distribuído", Categoria.TRABALHO_NAO_DISTRIBUIDO, "evento_secundario"),
    ("EE10", "Aguardando sequência de serviço", Categoria.AGUARDANDO_SEQUENCIA_SERVICO, "evento_secundario"),
    ("EE11", "Consulta à documentação técnica", Categoria.CONSULTA_DOCUMENTACAO_TECNICA, "pausa"),
    ("EE12", "Deslocamento rodoviário", Categoria.DESLOCAMENTO_RODOVIARIO, "evento_secundario"),
    ("EE13", "Deslocamento ferroviário", Categoria.DESLOCAMENTO_FERROVIARIO, "evento_secundario"),
    ("EE14", "Deslocamento a pé", Categoria.DESLOCAMENTO_A_PE, "evento_secundario"),
    ("EE15", "Preparar atividade", Categoria.PREPARAR_ATIVIDADE, "evento_secundario"),
    ("EE16", "Desmontar atividade", Categoria.DESMONTAR_ATIVIDADE, "evento_secundario"),
    ("EE17", "Manutenção em equipamentos", Categoria.ATIVIDADE_PLANEJADA, "atividade"),
    ("EE18", "Suporte da manutenção", Categoria.APOIO_OPERACIONAL, "evento_secundario"),
    ("EE19", "Carregar veículo", Categoria.CARREGAR_VEICULO, "evento_secundario"),
    ("EE20", "Descarregar veículo", Categoria.DESCARREGAR_VEICULO, "evento_secundario"),
    ("EE21", "SMS", Categoria.SMS, "pausa"),
    ("EE22", "Manutenção não planejada", Categoria.ATENDIMENTO_FALHA, "atividade"),
    ("EE23", "Treinamento", Categoria.TREINAMENTO, "pausa"),
    # EE24 "Horas nao apontadas" nao vira entrada de catalogo: e o proprio
    # conceito de "tempo nao classificado" ja calculado automaticamente a
    # partir das lacunas entre eventos (workforce_core.calculo), nao um
    # motivo que alguem escolhe ao iniciar um evento. Ver ADR-0014.
]


def catalogo_relatorio_1_manutencao() -> CatalogoMotivos:
    """Catalogo baseado no "Relatorio de Atividades Diarias de Manutencao"
    (Relatorio 1, codigos EE01-EE23) da Gerencia de Manutencao
    Eletroeletronica, fornecido pelo responsavel pelo produto em
    2026-07-23 - o formulario que a equipe efetivamente usa hoje (o
    responsavel confirmou que apenas o Relatorio 1 esta em uso; um
    segundo formulario mais antigo, com codigos numericos 10-250, nao
    esta mais em uso e nao foi incorporado aqui).

    Diferente de catalogo_padrao(), estas entradas nao sao um exemplo de
    teste - sao os codigos e descricoes reais do formulario em papel. Ainda
    assim, `classificacao_hh` permanece NAO_DEFINIDO para todas: o codigo
    existir no formulario nao implica uma classificacao
    produtiva/improdutiva/nao computavel validada - essa continua sendo
    uma decisao de negocio separada e pendente (docs/27 secao 6, itens 6-9).

    Ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md para a
    justificativa completa, incluindo por que EE24 nao aparece aqui e por
    que os codigos "evento_secundario" ainda nao tem tela propria na
    interface de campo.
    """
    catalogo = CatalogoMotivos()
    for codigo, descricao, categoria, _tipo_registro in _RELATORIO_1_ENTRADAS:
        catalogo.registrar(
            EntradaCatalogo(
                codigo=codigo,
                descricao=descricao,
                categoria=categoria,
                classificacao_hh=ClassificacaoHH.NAO_DEFINIDO,
            )
        )
    return catalogo


def codigos_relatorio_1_por_tipo_registro(tipo_registro: str) -> List[str]:
    """Lista os codigos EE cujo tipo_registro (ver _RELATORIO_1_ENTRADAS)
    e o informado - por exemplo, "pausa" para os codigos que interrompem
    uma atividade em andamento. Usado para alimentar o seletor da
    interface de campo sem duplicar a classificacao em dois lugares.
    """
    return [
        codigo
        for codigo, _descricao, _categoria, tipo in _RELATORIO_1_ENTRADAS
        if tipo == tipo_registro
    ]
