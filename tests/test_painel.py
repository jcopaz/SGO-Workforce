"""Testes do Incremento 9: painel gerencial (dados e graficos, sem Streamlit).

app.py (o entrypoint Streamlit) nao e testavel por pytest fora do runtime
do Streamlit - validado por smoke test manual (`streamlit run`), ver
docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md.
"""

from datetime import timedelta

import pytest

from dados import carregar_jornadas, formatar_horas, gerar_jornadas_exemplo, montar_resumo
from graficos import (
    CAMINHO_ECHARTS_JS_LOCAL,
    grafico_distribuicao_pizza,
    grafico_hh_por_categoria,
    renderizar_embutido,
)
from workforce_core.catalogo import Categoria
from workforce_storage import RepositorioJornadaArquivo


def test_formatar_horas():
    assert formatar_horas(timedelta(hours=4, minutes=10)) == "4h10"
    assert formatar_horas(timedelta(minutes=5)) == "0h05"
    assert formatar_horas(timedelta()) == "0h00"


def test_carregar_jornadas_diretorio_vazio(tmp_path):
    jornadas, com_erro = carregar_jornadas(tmp_path)
    assert jornadas == []
    assert com_erro == []


def test_gerar_e_carregar_jornadas_exemplo(tmp_path):
    criadas = gerar_jornadas_exemplo(tmp_path, quantidade=3)
    assert len(criadas) == 3

    jornadas, com_erro = carregar_jornadas(tmp_path)
    assert len(jornadas) == 3
    assert com_erro == []
    assert all(j.estado.value == "ENCERRADA" for j in jornadas)


def test_montar_resumo_com_dados_de_exemplo(tmp_path):
    gerar_jornadas_exemplo(tmp_path, quantidade=2)
    jornadas, _ = carregar_jornadas(tmp_path)

    resumo = montar_resumo(jornadas)

    assert resumo.quantidade_jornadas == 2
    assert resumo.jornada_bruta_total > timedelta()
    assert Categoria.DESLOCAMENTO_RODOVIARIO in resumo.por_categoria
    assert Categoria.ATIVIDADE_PLANEJADA in resumo.por_categoria


def test_carregar_jornadas_reporta_arquivo_corrompido_sem_apagar(tmp_path):
    repo = RepositorioJornadaArquivo(tmp_path)
    from uuid import uuid4

    jornada_id = uuid4()
    caminho = tmp_path / f"{jornada_id}.json"
    caminho.write_text("nao e json valido", encoding="utf-8")

    jornadas, com_erro = carregar_jornadas(tmp_path)

    assert jornadas == []
    assert com_erro == [str(jornada_id)]
    assert caminho.exists()


# ----------------------------------------------------------------------
# Graficos
# ----------------------------------------------------------------------
def test_echarts_js_local_esta_presente():
    # O painel se recusa a depender de CDN sem integrity - o asset local
    # precisa existir para o painel funcionar.
    assert CAMINHO_ECHARTS_JS_LOCAL.exists()
    assert CAMINHO_ECHARTS_JS_LOCAL.stat().st_size > 100_000


def test_grafico_hh_por_categoria_renderiza_html_autocontido():
    por_categoria = {
        Categoria.ATIVIDADE_PLANEJADA: timedelta(hours=3),
        None: timedelta(minutes=20),
    }
    grafico = grafico_hh_por_categoria(por_categoria)
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "echarts.min.js" not in html.split("<script>", 1)[1].split("</script>")[0]
    assert "cdn" not in html.lower()
    assert "SEM_CATEGORIA" in html


def test_grafico_distribuicao_pizza_renderiza_html_autocontido():
    por_categoria = {Categoria.DESLOCAMENTO_RODOVIARIO: timedelta(minutes=30)}
    grafico = grafico_distribuicao_pizza(por_categoria)
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()


def test_renderizar_embutido_falha_se_asset_local_ausente(tmp_path, monkeypatch):
    import graficos

    caminho_falso = tmp_path / "nao-existe.js"
    monkeypatch.setattr(graficos, "CAMINHO_ECHARTS_JS_LOCAL", caminho_falso)

    grafico = grafico_hh_por_categoria({Categoria.ATIVIDADE_PLANEJADA: timedelta(hours=1)})
    with pytest.raises(FileNotFoundError):
        renderizar_embutido(grafico)
