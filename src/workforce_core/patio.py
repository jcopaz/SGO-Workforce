"""Cadastro de patios (ADR-0072).

"Patio" e "coordenacao" nao existiam como conceito no dominio do sistema -
docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md registrava isso explicitamente
("Filtros de coordenacao, equipe, patio e impacto: nao implementados
porque esses conceitos NAO EXISTEM no dominio do sistema ainda - nao e
uma omissao, e a ausencia do modelo de dados correspondente"). Este
modulo cria a estrutura minima, no mesmo espirito de
workforce_core.catalogo.EntradaCatalogo: upsert por codigo (chave de
negocio), ativo/inativo, sem workflow de aprovacao (mesma decisao do
item 11 de docs/23_DECISOES_PENDENTES.md para o catalogo de motivos).

Latitude/longitude e coordenacao sao dado operacional real informado pelo
responsavel pelo produto por patio (Prainha/Casqueiro, coordenacao
Piacaguera, 2026-08-26) - nenhum valor foi inventado pelo agente.
"coordenacao" fica como texto livre no patio por decisao do responsavel
pelo produto na mesma data (nao virou entidade propria neste incremento -
revisitar se o volume de coordenacoes justificar).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Patio:
    codigo: str
    nome: str
    coordenacao: str
    latitude: float
    longitude: float
    ativo: bool = True
