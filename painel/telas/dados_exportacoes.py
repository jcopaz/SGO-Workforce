"""Exportacoes CSV, XLSX e GeoJSON - piloto tecnico (Incremento 11).

Layout oficial de colunas, dados pessoais permitidos, politica de
auditoria e perfis autorizados sao decisoes provisorias - ver
docs/38_ADR_0011_EXPORTACOES_CSV_XLSX_GEOJSON.md.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dados import carregar_jornadas, carregar_pulsos
from workforce_export import (
    MetadadosExportacao,
    feature_collection_pontos,
    feature_collection_trajetorias,
)
from workforce_export.csv_exportacao import linhas_eventos, linhas_falhas, linhas_gps, linhas_jornadas
from workforce_export.xlsx_exportacao import exportar_xlsx

st.warning(
    "Piloto tecnico. Layout oficial de colunas, dados pessoais permitidos, "
    "auditoria e perfis autorizados ainda sao decisoes pendentes "
    "(ver docs/38_ADR_0011_EXPORTACOES_CSV_XLSX_GEOJSON.md)."
)

st.title("SGO Workforce | Exportacoes (piloto)")

if "painel_diretorio_jornadas" not in st.session_state:
    st.session_state.painel_diretorio_jornadas = str(_RAIZ_PROJETO / "dados_locais" / "jornadas")
if "painel_diretorio_pulsos" not in st.session_state:
    st.session_state.painel_diretorio_pulsos = str(_RAIZ_PROJETO / "dados_locais" / "pulsos")

diretorio_jornadas = st.text_input("Diretorio de jornadas persistidas", key="painel_diretorio_jornadas")
diretorio_pulsos = st.text_input("Diretorio de pulsos GPS persistidos", key="painel_diretorio_pulsos")

if not diretorio_jornadas:
    st.warning("Informe o diretorio de jornadas para continuar.")
    st.stop()

usuario_responsavel = st.text_input(
    "Usuario responsavel pela exportacao (obrigatorio)", key="painel_export_usuario"
)

jornadas, com_erro = carregar_jornadas(diretorio_jornadas)
if com_erro:
    st.error(f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem apagar.")

if not jornadas:
    st.info("Nenhuma jornada encontrada nesse diretorio.")
    st.stop()

if not usuario_responsavel:
    st.info("Informe o usuario responsavel para habilitar a exportacao.")
    st.stop()

pulsos = []
if diretorio_pulsos:
    for jornada in jornadas:
        pulsos.extend(carregar_pulsos(diretorio_pulsos, jornada.id))

metadados = MetadadosExportacao(
    usuario_responsavel=usuario_responsavel,
    filtros={"diretorio_jornadas": diretorio_jornadas},
)

st.caption(
    f"{len(jornadas)} jornada(s) e {len(pulsos)} pulso(s) serao incluidos "
    f"nesta exportacao, gerada por '{usuario_responsavel}'."
)

aba_csv, aba_xlsx, aba_geojson = st.tabs(["CSV", "XLSX", "GeoJSON"])

with aba_csv:
    st.write("Um arquivo por tipo de dado: jornadas, eventos, falhas e GPS.")
    for nome, campos, linhas in (
        ("jornadas", None, linhas_jornadas(jornadas)),
        ("eventos", None, linhas_eventos(jornadas)),
        ("falhas", None, linhas_falhas(jornadas)),
        ("gps", None, linhas_gps(pulsos)),
    ):
        buffer = io.StringIO()
        if linhas:
            escritor = csv.DictWriter(buffer, fieldnames=list(linhas[0].keys()))
            escritor.writeheader()
            escritor.writerows(linhas)
        st.download_button(
            f"Baixar {nome}.csv ({len(linhas)} linha(s))",
            data=buffer.getvalue(),
            file_name=f"{nome}_{metadados.sufixo_nome_arquivo()}.csv",
            mime="text/csv",
            key=f"download_csv_{nome}",
        )

with aba_xlsx:
    st.write("Workbook unico com as abas Resumo, HH por categoria, HH por ativo, Jornadas, Pausas, Falhas, Qualidade e Dicionario de dados.")
    caminho_xlsx = _RAIZ_PROJETO / "dados_locais" / f"export_{metadados.sufixo_nome_arquivo()}.xlsx"
    if st.button("Gerar XLSX"):
        exportar_xlsx(caminho_xlsx, jornadas, metadados, pulsos=pulsos or None)
        st.success(f"Gerado em {caminho_xlsx}")
        with open(caminho_xlsx, "rb") as arquivo:
            st.download_button(
                "Baixar XLSX",
                data=arquivo.read(),
                file_name=caminho_xlsx.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with aba_geojson:
    incluir_matricula = st.checkbox(
        "Incluir matricula do colaborador nas propriedades (dado pessoal - desligado por padrao)",
        value=False,
        key="painel_export_geojson_matricula",
    )
    if not pulsos:
        st.info("Nenhum pulso GPS carregado - informe o diretorio de pulsos acima.")
    else:
        colecao_pontos = feature_collection_pontos(
            pulsos, incluir_identificacao_pessoal=incluir_matricula
        )
        st.download_button(
            f"Baixar pontos.geojson ({len(pulsos)} pulso(s))",
            data=json.dumps(colecao_pontos, ensure_ascii=False),
            file_name=f"pontos_{metadados.sufixo_nome_arquivo()}.geojson",
            mime="application/geo+json",
        )

        pulsos_por_jornada = {j.id: carregar_pulsos(diretorio_pulsos, j.id) for j in jornadas}
        distancia = st.slider(
            "Distancia minima de simplificacao (m) - nao e valor oficial",
            min_value=0,
            max_value=500,
            value=50,
            key="painel_export_geojson_distancia",
        )
        colecao_trajetorias = feature_collection_trajetorias(
            pulsos_por_jornada,
            distancia_simplificacao_metros=float(distancia),
            incluir_identificacao_pessoal=incluir_matricula,
        )
        st.download_button(
            f"Baixar trajetorias.geojson ({len(colecao_trajetorias['features'])} jornada(s))",
            data=json.dumps(colecao_trajetorias, ensure_ascii=False),
            file_name=f"trajetorias_{metadados.sufixo_nome_arquivo()}.geojson",
            mime="application/geo+json",
        )
