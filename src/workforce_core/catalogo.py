"""Infraestrutura de catalogo do Incremento 5.

O catalogo oficial de motivos, e a classificacao de cada um como produtivo,
improdutivo ou nao computavel, eram decisoes de negocio explicitamente
pendentes (docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md, secao 6 itens
6-9, e secao 15.3 "Antes do Incremento 5"). Este modulo fornece a estrutura
tecnica para representar essas decisoes - nenhum valor foi inventado pelo
agente; `catalogo_padrao()` (motivos de teste) continua NAO_DEFINIDO, e
`catalogo_relatorio_1_manutencao()` (codigos reais) teve sua classificacao
validada codigo a codigo pelo responsavel pelo produto em 2026-07-27 (ver
docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md).

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

    # Contraparte de ATIVIDADE_PLANEJADA quando a manutencao programada nao
    # e concluida no turno (EE23, decisao de negocio de 2026-07-27 - ver
    # docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md).
    ATIVIDADE_PLANEJADA_NAO_CONCLUIDA = "ATIVIDADE_PLANEJADA_NAO_CONCLUIDA"


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
    # "pausa" | "evento_secundario" | "atividade" - mesmo vocabulario ja
    # usado em _RELATORIO_1_ENTRADAS/codigos_relatorio_1_por_tipo_registro,
    # agora carregado no proprio objeto (nao so na tupla interna) para o
    # catalogo dinamico (Incremento de catalogo real, ver
    # docs/46_ADR_0019_CATALOGO_DINAMICO.md) saber montar o seletor certo
    # na interface de campo sem precisar de uma segunda fonte de verdade.
    tipo_registro: str = "pausa"
    # Desativar nunca apaga - mesmo principio de "correcao nunca apaga o
    # evento original" (docs/17_SEGURANCA_GOVERNANCA.md), aplicado a
    # motivos de catalogo.
    ativo: bool = True


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


# Codigo EE -> (descricao exata do formulario, categoria, tipo de registro,
# classificacao_hh). "tipo_registro" indica como o codigo se encaixa no
# motor de dominio hoje:
# - "atividade": e a propria Atividade (nao e um motivo de pausa/evento);
# - "pausa": motivo de Pausa (interrompe uma Atividade em andamento);
# - "evento_secundario": motivo de Deslocamento/Espera/Apoio (vinculado
#   diretamente a Jornada, mutuamente exclusivo com a Atividade principal).
# Ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md para a
# justificativa codigo a codigo original e
# docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md para a
# reclassificacao produtiva/improdutiva e a renumeracao de 2026-07-27
# (responsavel pelo produto validou codigo a codigo).
#
# Renumeracao de 2026-07-27: o antigo EE18 "Suporte da manutencao" foi
# excluido do catalogo por ser duplicado do que hoje e EE21 "Atendimento
# de Falha" - os codigos EE19-EE24 da versao anterior deslizaram uma
# posicao (antigo EE19 -> novo EE18, ..., antigo EE24 -> novo EE23). O
# antigo EE24 "Horas nao apontadas" (tempo nao classificado, calculado
# automaticamente a partir das lacunas entre eventos - nunca uma entrada
# de catalogo) nao existe mais como conceito reservado: o numero EE24 foi
# liberado pela renumeracao e o novo EE23 e uma entrada real,
# "Manutencao Programada Nao Concluida" - contraparte de EE17 quando a
# manutencao nao termina no turno do colaborador.
_RELATORIO_1_ENTRADAS = [
    ("EE01", "Preparação para jornada", Categoria.PREPARACAO_JORNADA, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE02", "Refeição 1 hora", Categoria.REFEICAO, "pausa", ClassificacaoHH.NAO_COMPUTAVEL),
    ("EE03", "Aguardando CCO", Categoria.AGUARDANDO_CCO, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE04", "Falta de ferramenta ou material", Categoria.AGUARDANDO_MATERIAL, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE05", "Trem parado na frente de serviço", Categoria.TREM_PARADO_FRENTE_SERVICO, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE06", "Restrição de infraestrutura", Categoria.RESTRICAO_INFRAESTRUTURA, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE07", "Reunião ou ADM", Categoria.REUNIAO, "pausa", ClassificacaoHH.IMPRODUTIVA),
    ("EE08", "Serviço interno da coordenação", Categoria.SERVICO_INTERNO_COORDENACAO, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE09", "Trabalho não distribuído", Categoria.TRABALHO_NAO_DISTRIBUIDO, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE10", "Aguardando sequência de serviço", Categoria.AGUARDANDO_SEQUENCIA_SERVICO, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE11", "Consulta à documentação técnica", Categoria.CONSULTA_DOCUMENTACAO_TECNICA, "pausa", ClassificacaoHH.PRODUTIVA),
    ("EE12", "Deslocamento rodoviário", Categoria.DESLOCAMENTO_RODOVIARIO, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE13", "Deslocamento ferroviário", Categoria.DESLOCAMENTO_FERROVIARIO, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE14", "Deslocamento a pé", Categoria.DESLOCAMENTO_A_PE, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE15", "Preparar atividade", Categoria.PREPARAR_ATIVIDADE, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE16", "Desmontar atividade", Categoria.DESMONTAR_ATIVIDADE, "evento_secundario", ClassificacaoHH.IMPRODUTIVA),
    ("EE17", "Manutenção Programada", Categoria.ATIVIDADE_PLANEJADA, "atividade", ClassificacaoHH.PRODUTIVA),
    ("EE18", "Carregar veículo", Categoria.CARREGAR_VEICULO, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE19", "Descarregar veículo", Categoria.DESCARREGAR_VEICULO, "evento_secundario", ClassificacaoHH.PRODUTIVA),
    ("EE20", "DDS / APR", Categoria.SMS, "pausa", ClassificacaoHH.PRODUTIVA),
    ("EE21", "Atendimento de Falha", Categoria.ATENDIMENTO_FALHA, "atividade", ClassificacaoHH.PRODUTIVA),
    ("EE22", "Treinamento", Categoria.TREINAMENTO, "pausa", ClassificacaoHH.PRODUTIVA),
    ("EE23", "Manutenção Programada Não Concluída", Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA, "atividade", ClassificacaoHH.PRODUTIVA),
]


def catalogo_completo() -> CatalogoMotivos:
    """Uniao de catalogo_padrao() (motivos de teste/exemplo, ex.: PAUSA_TESTE)
    com catalogo_relatorio_1_manutencao() (codigos reais EE01-EE23).

    Usado onde jornadas de exemplo/teste e jornadas reais da interface de
    campo precisam ser classificadas pelo mesmo catalogo (ex.:
    painel/dados.py::montar_resumo) - sem isso, um consumidor precisaria
    saber de antemao se os dados sao de teste ou reais para escolher o
    catalogo certo, e jornadas com os dois tipos de motivo (ex.: uma de
    exemplo e uma sincronizada de verdade) nunca classificariam ambas
    corretamente com um catalogo so.
    """
    completo = CatalogoMotivos()
    for entrada in catalogo_padrao().todos():
        completo.registrar(entrada)
    for entrada in catalogo_relatorio_1_manutencao().todos():
        completo.registrar(entrada)
    return completo


def catalogo_relatorio_1_manutencao() -> CatalogoMotivos:
    """Catalogo baseado no "Relatorio de Atividades Diarias de Manutencao"
    (Relatorio 1, codigos EE01-EE23) da Gerencia de Manutencao
    Eletroeletronica, fornecido pelo responsavel pelo produto em
    2026-07-23 - o formulario que a equipe efetivamente usa hoje (o
    responsavel confirmou que apenas o Relatorio 1 esta em uso; um
    segundo formulario mais antigo, com codigos numericos 10-250, nao
    esta mais em uso e nao foi incorporado aqui).

    Diferente de catalogo_padrao(), estas entradas nao sao um exemplo de
    teste - sao os codigos e descricoes reais do formulario em papel.
    `classificacao_hh` foi validada codigo a codigo pelo responsavel pelo
    produto em 2026-07-27 (docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md)
    - antes disso permanecia NAO_DEFINIDO para todas.

    Ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md para a
    justificativa original codigo a codigo e ADR-0023 para a renumeracao/
    reclassificacao. Codigos "evento_secundario" ainda nao tem tela propria
    na interface de campo.
    """
    catalogo = CatalogoMotivos()
    for codigo, descricao, categoria, tipo_registro, classificacao_hh in _RELATORIO_1_ENTRADAS:
        catalogo.registrar(
            EntradaCatalogo(
                codigo=codigo,
                descricao=descricao,
                categoria=categoria,
                classificacao_hh=classificacao_hh,
                tipo_registro=tipo_registro,
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
        for codigo, _descricao, _categoria, tipo, _classificacao_hh in _RELATORIO_1_ENTRADAS
        if tipo == tipo_registro
    ]
