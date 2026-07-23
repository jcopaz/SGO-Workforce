"""Carregador dos catalogos derivados do RASF (Incremento 6).

Le os arquivos CSV ja extraidos em `catalogos/` (raiz do repositorio):
sintomas, sistemas, tipos_solicitacao, impactos, componentes_causadores e
os tres niveis de analise 6M. Todos compartilham o mesmo formato
(codigo_interno, valor, frequencia, ativo), conforme
`catalogos/dicionario_colunas_rasf.csv` e `catalogos/README.md`.

Estes arquivos **nao sao catalogo definitivo de producao** - o proprio
catalogos/README.md e docs/09_ATENDIMENTO_FALHAS_RASF.md dizem
explicitamente que precisam de governanca, normalizacao e validacao da
Eletroeletrônica antes de virarem catalogo oficial. Este modulo apenas os
torna programaticamente acessiveis, preservando codigo e descricao
originais - nao reinterpreta nem reclassifica nenhum valor.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ItemCatalogoRasf:
    codigo_interno: str
    valor: str
    frequencia: int
    ativo: bool


def _linha_para_item(linha: Dict[str, str]) -> ItemCatalogoRasf:
    return ItemCatalogoRasf(
        codigo_interno=linha["codigo_interno"].strip(),
        valor=linha["valor"].strip(),
        frequencia=int(linha["frequencia"]),
        ativo=linha["ativo"].strip().lower() == "true",
    )


def carregar_catalogo_rasf(caminho_csv: Path) -> List[ItemCatalogoRasf]:
    """Le um unico arquivo CSV do catalogo RASF.

    Usa encoding utf-8-sig porque os arquivos fonte tem BOM no cabecalho
    (observado em todos os CSVs de catalogos/).
    """
    with open(caminho_csv, newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        return [_linha_para_item(linha) for linha in leitor]


# Nome de arquivo (sem extensao) -> chave logica do catalogo.
_ARQUIVOS_CATALOGO_RASF = {
    "sintomas": "sintomas",
    "sistemas": "sistemas",
    "tipos_solicitacao": "tipos_solicitacao",
    "impactos": "impactos",
    "componentes_causadores": "componentes_causadores",
    "6m_nivel_1": "6m_nivel_1",
    "6m_nivel_2": "6m_nivel_2",
    "6m_nivel_3": "6m_nivel_3",
}


def carregar_catalogos_rasf(diretorio: Path) -> Dict[str, List[ItemCatalogoRasf]]:
    """Carrega todos os catalogos RASF conhecidos de um diretorio.

    Arquivos ausentes sao simplesmente omitidos do resultado (nao e erro -
    o diretorio de catalogos pode ser atualizado independentemente do
    codigo). Retorna um dict vazio para o que nao for encontrado.
    """
    diretorio = Path(diretorio)
    catalogos: Dict[str, List[ItemCatalogoRasf]] = {}
    for nome_arquivo, chave in _ARQUIVOS_CATALOGO_RASF.items():
        caminho = diretorio / f"{nome_arquivo}.csv"
        if caminho.exists():
            catalogos[chave] = carregar_catalogo_rasf(caminho)
    return catalogos


def item_por_codigo(itens: List[ItemCatalogoRasf], codigo_interno: str) -> Optional[ItemCatalogoRasf]:
    for item in itens:
        if item.codigo_interno == codigo_interno:
            return item
    return None


def item_por_valor(itens: List[ItemCatalogoRasf], valor: str) -> Optional[ItemCatalogoRasf]:
    for item in itens:
        if item.valor == valor:
            return item
    return None


def apenas_ativos(itens: List[ItemCatalogoRasf]) -> List[ItemCatalogoRasf]:
    return [item for item in itens if item.ativo]
