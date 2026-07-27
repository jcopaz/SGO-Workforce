"""Exportacao CSV (Incremento 11).

Arquivos separados conforme docs/14_EXPORTACOES.md: jornadas, eventos,
falhas e GPS. "Participantes" nao e exportado porque o sistema ainda nao
modela multiplos participantes por evento (fora de escopo - ver secao 6
do alinhamento oficial, "regra para multiplas OS no mesmo evento").

"Eventos" unifica Atividade, Pausa e EventoSecundario em um unico arquivo
com colunas comuns, no espirito do modelo generico de "Evento" ja descrito
em docs/07_MOTOR_EVENTOS_E_HH.md (categoria, motivo, inicio, fim).

Filtragem de quais jornadas exportar e responsabilidade de quem chama -
"filtros da tela devem ser repetidos no arquivo" (docs/14) e satisfeito
pelos filtros ja terem sido aplicados antes de a lista de jornadas chegar
aqui, nao por este modulo reimplementar filtros.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from workforce_core.calculo import (
    duracao_atividade_bruta,
    duracao_atividade_liquida,
    duracao_evento_secundario,
    duracao_jornada_bruta,
    duracao_pausa,
    tempo_classificado_jornada,
    tempo_nao_classificado,
)
from workforce_core.engine import CAMPOS_OBRIGATORIOS_FALHA
from workforce_core.entities import Jornada, PulsoGps

from .metadados import MetadadosExportacao

CAMPOS_JORNADAS = [
    "jornada_id",
    "colaborador_matricula",
    "estado",
    "inicio",
    "fim",
    "jornada_bruta_segundos",
    "tempo_classificado_segundos",
    "tempo_nao_classificado_segundos",
]

CAMPOS_EVENTOS = [
    "jornada_id",
    "tipo_evento",
    "evento_id",
    "evento_pai_id",
    "motivo_ou_tipo",
    "inicio",
    "fim",
    "duracao_bruta_segundos",
    "duracao_liquida_segundos",
]

CAMPOS_FALHAS = [
    "jornada_id",
    "atividade_id",
    "inicio",
    "fim",
    "nota",
    "ativo",
    "sintoma",
    "objeto",
    "causa",
    "acao",
    "observacao",
    "completo",
]

CAMPOS_GPS = [
    "pulso_id",
    "jornada_id",
    "colaborador_matricula",
    "timestamp_dispositivo",
    "latitude",
    "longitude",
    "precisao_metros",
    "qualidade",
]


def _iso(valor) -> str:
    return valor.isoformat() if valor is not None else ""


def linhas_jornadas(jornadas: List[Jornada]) -> List[Dict[str, Any]]:
    linhas = []
    for jornada in jornadas:
        encerrada = jornada.estado.value == "ENCERRADA"
        linhas.append(
            {
                "jornada_id": str(jornada.id),
                "colaborador_matricula": jornada.colaborador_matricula,
                "estado": jornada.estado.value,
                "inicio": _iso(jornada.inicio),
                "fim": _iso(jornada.fim),
                "jornada_bruta_segundos": (
                    duracao_jornada_bruta(jornada).total_seconds() if encerrada else ""
                ),
                "tempo_classificado_segundos": (
                    tempo_classificado_jornada(jornada).total_seconds() if encerrada else ""
                ),
                "tempo_nao_classificado_segundos": (
                    tempo_nao_classificado(jornada).total_seconds() if encerrada else ""
                ),
            }
        )
    return linhas


def linhas_eventos(jornadas: List[Jornada]) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    for jornada in jornadas:
        for atividade in jornada.atividades:
            linhas.append(
                {
                    "jornada_id": str(jornada.id),
                    "tipo_evento": "ATENDIMENTO_FALHA" if atividade.dados_falha else "ATIVIDADE",
                    "evento_id": str(atividade.id),
                    "evento_pai_id": "",
                    "motivo_ou_tipo": "",
                    "inicio": _iso(atividade.inicio),
                    "fim": _iso(atividade.fim),
                    "duracao_bruta_segundos": (
                        duracao_atividade_bruta(atividade).total_seconds() if atividade.fim else ""
                    ),
                    "duracao_liquida_segundos": (
                        duracao_atividade_liquida(atividade).total_seconds()
                        if atividade.fim
                        else ""
                    ),
                }
            )
            for pausa in atividade.pausas:
                linhas.append(
                    {
                        "jornada_id": str(jornada.id),
                        "tipo_evento": "PAUSA",
                        "evento_id": str(pausa.id),
                        "evento_pai_id": str(atividade.id),
                        "motivo_ou_tipo": pausa.motivo,
                        "inicio": _iso(pausa.inicio),
                        "fim": _iso(pausa.fim),
                        "duracao_bruta_segundos": (
                            duracao_pausa(pausa).total_seconds() if pausa.fim else ""
                        ),
                        "duracao_liquida_segundos": "",
                    }
                )
        for evento in jornada.eventos_secundarios:
            linhas.append(
                {
                    "jornada_id": str(jornada.id),
                    "tipo_evento": evento.tipo.value,
                    "evento_id": str(evento.id),
                    "evento_pai_id": "",
                    "motivo_ou_tipo": evento.motivo,
                    "inicio": _iso(evento.inicio),
                    "fim": _iso(evento.fim),
                    "duracao_bruta_segundos": (
                        duracao_evento_secundario(evento).total_seconds() if evento.fim else ""
                    ),
                    "duracao_liquida_segundos": "",
                }
            )
    return linhas


def linhas_falhas(jornadas: List[Jornada]) -> List[Dict[str, Any]]:
    linhas = []
    for jornada in jornadas:
        for atividade in jornada.atividades:
            dados = atividade.dados_falha
            if dados is None:
                continue
            # Mesma regra de completude do motor (workforce_core.engine),
            # reaproveitada em vez de duplicada - um incremento anterior
            # duplicou essa tupla aqui e ela ficou desatualizada quando a
            # regra mudou no ADR-0021.
            completo = all(getattr(dados, campo) for campo in CAMPOS_OBRIGATORIOS_FALHA)
            linhas.append(
                {
                    "jornada_id": str(jornada.id),
                    "atividade_id": str(atividade.id),
                    "inicio": _iso(atividade.inicio),
                    "fim": _iso(atividade.fim),
                    "nota": dados.nota or "",
                    "ativo": dados.ativo or "",
                    "sintoma": dados.sintoma or "",
                    "objeto": dados.objeto or "",
                    "causa": dados.causa or "",
                    "acao": dados.acao or "",
                    "observacao": dados.observacao or "",
                    "completo": completo,
                }
            )
    return linhas


def linhas_gps(pulsos: List[PulsoGps]) -> List[Dict[str, Any]]:
    return [
        {
            "pulso_id": str(pulso.id),
            "jornada_id": str(pulso.jornada_id),
            "colaborador_matricula": pulso.colaborador_matricula,
            "timestamp_dispositivo": _iso(pulso.timestamp_dispositivo),
            "latitude": pulso.latitude,
            "longitude": pulso.longitude,
            "precisao_metros": pulso.precisao_metros,
            "qualidade": pulso.qualidade.value,
        }
        for pulso in pulsos
    ]


def _escrever_csv(caminho: Path, campos: List[str], linhas: List[Dict[str, Any]]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def exportar_csvs(
    diretorio: Union[str, Path],
    jornadas: List[Jornada],
    pulsos: List[PulsoGps],
    metadados: MetadadosExportacao,
) -> List[Path]:
    """Grava jornadas/eventos/falhas/gps + metadados em arquivos CSV separados.

    Nome dos arquivos inclui o sufixo de periodo/geracao dos metadados
    (docs/14_EXPORTACOES.md: "nome do arquivo inclui periodo e geracao").
    """
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    sufixo = metadados.sufixo_nome_arquivo()

    arquivos = {
        f"jornadas_{sufixo}.csv": (CAMPOS_JORNADAS, linhas_jornadas(jornadas)),
        f"eventos_{sufixo}.csv": (CAMPOS_EVENTOS, linhas_eventos(jornadas)),
        f"falhas_{sufixo}.csv": (CAMPOS_FALHAS, linhas_falhas(jornadas)),
        f"gps_{sufixo}.csv": (CAMPOS_GPS, linhas_gps(pulsos)),
    }

    caminhos: List[Path] = []
    for nome, (campos, linhas) in arquivos.items():
        caminho = diretorio / nome
        _escrever_csv(caminho, campos, linhas)
        caminhos.append(caminho)

    caminho_metadados = diretorio / f"metadados_{sufixo}.json"
    caminho_metadados.write_text(
        json.dumps(metadados.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    caminhos.append(caminho_metadados)

    return caminhos
