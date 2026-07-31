"""Testes do Incremento 9: painel gerencial (dados e graficos, sem Streamlit).

app.py (o entrypoint Streamlit) nao e testavel por pytest fora do runtime
do Streamlit - validado por smoke test manual (`streamlit run`), ver
docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md.
"""

from datetime import date, timedelta

import pytest

from dados import (
    agrupar_duracao_por_categoria,
    carregar_jornadas,
    formatar_data_hora,
    formatar_horas,
    gerar_jornadas_exemplo,
    horas_produtiva_nao_rentavel_do_resumo,
    montar_linhas_eventos,
    montar_resumo,
    utilizacao_hh_do_resumo,
)
from graficos import (
    CAMINHO_ECHARTS_JS_LOCAL,
    grafico_distribuicao_pizza,
    grafico_evolucao_diaria,
    grafico_gauge_percentual,
    grafico_hh_por_categoria,
    grafico_hh_por_colaborador,
    grafico_motivos_treemap,
    renderizar_embutido,
)
from workforce_core.catalogo import Categoria, ClassificacaoHH
from workforce_core.consolidacao import LinhaEvento, ResumoConsolidado
from workforce_storage import RepositorioJornadaArquivo


def test_formatar_horas():
    assert formatar_horas(timedelta(hours=4, minutes=10)) == "4h10"
    assert formatar_horas(timedelta(minutes=5)) == "0h05"
    assert formatar_horas(timedelta()) == "0h00"


def test_formatar_data_hora():
    from datetime import datetime

    assert formatar_data_hora(datetime(2026, 7, 27, 8, 5, 9)) == "27/07/2026 08:05:09"
    assert formatar_data_hora(None) == "--"


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


def test_montar_linhas_eventos_e_agrupar_por_categoria_com_dados_de_exemplo(tmp_path):
    gerar_jornadas_exemplo(tmp_path, quantidade=2)
    jornadas, _ = carregar_jornadas(tmp_path)

    linhas = montar_linhas_eventos(jornadas)
    assert len(linhas) > 0
    assert {linha.colaborador_matricula for linha in linhas} == {
        j.colaborador_matricula for j in jornadas
    }

    por_categoria = agrupar_duracao_por_categoria(linhas)
    assert Categoria.DESLOCAMENTO_RODOVIARIO in por_categoria
    assert Categoria.ATIVIDADE_PLANEJADA in por_categoria
    assert sum(por_categoria.values(), timedelta()) == sum(
        (linha.duracao for linha in linhas), timedelta()
    )


def test_montar_resumo_por_classificacao_hh_com_dados_de_exemplo(tmp_path):
    # gerar_jornadas_exemplo usa DESLOCAMENTO_TESTE/PAUSA_TESTE (motivos de
    # teste, NAO_DEFINIDO) para pausa/evento, mas as atividades (planejada
    # e atendimento de falha) caem nas mesmas Categoria de EE17/EE21, que
    # catalogo_completo() (usado por montar_resumo) ja classifica como
    # PRODUTIVA (ADR-0023) - por isso o bucket PRODUTIVA existe mesmo em
    # dados de exemplo.
    gerar_jornadas_exemplo(tmp_path, quantidade=2)
    jornadas, _ = carregar_jornadas(tmp_path)

    resumo = montar_resumo(jornadas)

    assert ClassificacaoHH.PRODUTIVA in resumo.por_classificacao_hh
    assert resumo.por_classificacao_hh[ClassificacaoHH.PRODUTIVA] > timedelta()


def test_utilizacao_hh_do_resumo_com_dados_de_exemplo(tmp_path):
    gerar_jornadas_exemplo(tmp_path, quantidade=2)
    jornadas, _ = carregar_jornadas(tmp_path)
    resumo = montar_resumo(jornadas)

    fracao = utilizacao_hh_do_resumo(resumo)

    assert fracao is not None
    assert 0 < fracao <= 1


def test_utilizacao_hh_do_resumo_sem_jornada_bruta_retorna_none():
    resumo = ResumoConsolidado()  # jornada_bruta_total == timedelta() (padrao)
    assert utilizacao_hh_do_resumo(resumo) is None


def test_horas_produtiva_nao_rentavel_do_resumo_com_dados_de_exemplo(tmp_path):
    # gerar_jornadas_exemplo usa DESLOCAMENTO_TESTE (motivo de teste,
    # NAO_DEFINIDO) para o evento secundario, entao nao cai em
    # PRODUTIVA_NAO_RENTAVEL - o valor deve ser zero, mas nunca ausente
    # (dict.get com default).
    gerar_jornadas_exemplo(tmp_path, quantidade=1)
    jornadas, _ = carregar_jornadas(tmp_path)
    resumo = montar_resumo(jornadas)

    assert horas_produtiva_nao_rentavel_do_resumo(resumo) == timedelta()


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


def _linhas_evento_exemplo():
    return [
        LinhaEvento(
            colaborador_matricula="1",
            data=date(2026, 7, 1),
            categoria=Categoria.ATIVIDADE_PLANEJADA,
            motivo=None,
            duracao=timedelta(hours=3),
            tipo="ATIVIDADE",
        ),
        LinhaEvento(
            colaborador_matricula="1",
            data=date(2026, 7, 1),
            categoria=Categoria.REFEICAO,
            motivo="EE02",
            duracao=timedelta(hours=1),
            tipo="PAUSA",
        ),
        LinhaEvento(
            colaborador_matricula="2",
            data=date(2026, 7, 2),
            categoria=Categoria.ATIVIDADE_PLANEJADA,
            motivo=None,
            duracao=timedelta(hours=2),
            tipo="ATIVIDADE",
        ),
    ]


def test_grafico_evolucao_diaria_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_evolucao_diaria(_linhas_evento_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "01/07/2026" in html
    assert "02/07/2026" in html


def test_grafico_hh_por_colaborador_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_hh_por_colaborador(_linhas_evento_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()


def test_grafico_motivos_treemap_ignora_linhas_sem_motivo():
    html = renderizar_embutido(grafico_motivos_treemap(_linhas_evento_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "EE02" in html


def test_grafico_gauge_percentual_renderiza_html_autocontido():
    grafico = grafico_gauge_percentual("Utilização HH", 0.75)
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "75" in html


def test_renderizar_embutido_falha_se_asset_local_ausente(tmp_path, monkeypatch):
    import graficos

    caminho_falso = tmp_path / "nao-existe.js"
    monkeypatch.setattr(graficos, "CAMINHO_ECHARTS_JS_LOCAL", caminho_falso)

    grafico = grafico_hh_por_categoria({Categoria.ATIVIDADE_PLANEJADA: timedelta(hours=1)})
    with pytest.raises(FileNotFoundError):
        renderizar_embutido(grafico)
