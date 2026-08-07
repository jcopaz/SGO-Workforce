"""Testes do Incremento 9: painel gerencial (dados e graficos, sem Streamlit).
Ampliado no ADR-0031 (dashboard completo de produtividade/execucao e
detalhamento de falhas).

app.py (o entrypoint Streamlit) nao e testavel por pytest fora do runtime
do Streamlit - validado por smoke test manual (`streamlit run`), ver
docs/36_ADR_0009_DASHBOARD_ECHARTS_PYECHARTS.md.
"""

import json
from datetime import date, datetime, timedelta, timezone

import pytest


def _contido(texto: str, html: str) -> bool:
    """Confere se `texto` aparece no HTML renderizado pelo pyecharts, cru
    ou escapado como o `json.dumps` (padrao `ensure_ascii=True`) grava
    caracteres acentuados dentro do <script> - "á" vira literalmente
    "\\u00e1" no HTML, nao o caractere em si (o navegador decodifica isso
    normalmente ao rodar o JS; so a comparacao de string do teste
    precisava saber disso)."""
    escapado = json.dumps(texto)[1:-1]
    return texto in html or escapado in html

from dados import (
    ROTULOS_CATEGORIA,
    agrupar_duracao_por_categoria,
    carregar_jornadas,
    contagem_e_duracao_media_por_motivo,
    formatar_data_hora,
    formatar_horas,
    gerar_jornadas_exemplo,
    gerar_jornadas_exemplo_volumoso,
    horas_produtiva_nao_rentavel_do_resumo,
    montar_linhas_atendimento_falha,
    montar_linhas_eventos,
    montar_resumo,
    rotulo_categoria,
    rotulo_motivo,
    utilizacao_hh_do_resumo,
    utilizacao_hh_por_colaborador,
)
from graficos import (
    CAMINHO_ECHARTS_JS_LOCAL,
    grafico_distribuicao_pizza,
    grafico_donut_contagem,
    grafico_duracao_media_por_sintoma,
    grafico_evolucao_diaria,
    grafico_evolucao_diaria_falhas,
    grafico_gauge_percentual,
    grafico_hh_falhas_por_colaborador,
    grafico_hh_por_categoria,
    grafico_hh_por_colaborador,
    grafico_funil_duracao_por_sintoma,
    grafico_hh_por_motivo,
    grafico_ranking_duracao_falhas,
    grafico_reincidencia_ativos,
    grafico_sankey_colaborador_categoria,
    grafico_scatter_duracao_frequencia,
    grafico_utilizacao_por_colaborador,
    renderizar_embutido,
)
from workforce_core.catalogo import Categoria, ClassificacaoHH
from workforce_core.consolidacao import LinhaAtendimentoFalha, LinhaEvento, ResumoConsolidado
from workforce_storage import RepositorioJornadaArquivo


def test_formatar_horas():
    assert formatar_horas(timedelta(hours=4, minutes=10)) == "4h10"
    assert formatar_horas(timedelta(minutes=5)) == "0h05"
    assert formatar_horas(timedelta()) == "0h00"


def test_formatar_data_hora():
    assert formatar_data_hora(datetime(2026, 7, 27, 8, 5, 9)) == "27/07/2026 08:05:09"
    assert formatar_data_hora(None) == "--"


def test_formatar_data_hora_converte_utc_aware_para_horario_brasil():
    # Bug real corrigido em 2026-08-04 (ADR-0047): um instante vindo do
    # backend em UTC (a interface de campo serializa via .toISOString())
    # aparecia no painel com a hora UTC crua, 3h adiantada em relacao ao
    # horario real de Brasilia.
    momento_utc = datetime(2026, 7, 27, 11, 5, 9, tzinfo=timezone.utc)
    assert formatar_data_hora(momento_utc) == "27/07/2026 08:05:09"


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


def test_gerar_jornadas_exemplo_volumoso_produz_dado_variado(tmp_path):
    """Simulador ETL (ADR-0033) - garante volume e variedade suficientes
    pra estressar os graficos (muitos colaboradores/categorias/motivos),
    e que toda jornada gerada respeita as regras do motor de dominio (nao
    haveria com_erro/excecao se alguma sequencia fosse invalida)."""
    criadas = gerar_jornadas_exemplo_volumoso(
        tmp_path, quantidade_colaboradores=10, dias=20, semente=1
    )
    assert len(criadas) > 50

    jornadas, com_erro = carregar_jornadas(tmp_path)
    assert com_erro == []
    assert len(jornadas) == len(criadas)
    assert all(j.estado.value == "ENCERRADA" for j in jornadas)

    linhas = montar_linhas_eventos(jornadas)
    assert len({linha.colaborador_matricula for linha in linhas}) == 10
    # So codigos EE reais (nunca os motivos legados de catalogo_padrao,
    # tipo PAUSA_TESTE/REFEICAO/DDS, que duplicariam o mesmo motivo com
    # um codigo diferente do EE02/EE20 oficial).
    motivos = {linha.motivo for linha in linhas if linha.motivo}
    assert len(motivos) > 10
    assert all(motivo.startswith("EE") for motivo in motivos)

    falhas = montar_linhas_atendimento_falha(jornadas)
    assert len(falhas) > 0
    assert all((falha.nota or "").startswith("SIM-FALHA-") for falha in falhas)


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
    # NAO_DEFINIDO) para o evento secundario, entao esse pedaco nao cai em
    # PRODUTIVA_NAO_RENTAVEL - mas a primeira jornada (i=0) tambem inclui
    # um atendimento de falha de 45min (EE21, categoria ATENDIMENTO_FALHA),
    # que desde o ADR-0053 e PRODUTIVA_NAO_RENTAVEL - o valor esperado nao
    # e mais zero.
    gerar_jornadas_exemplo(tmp_path, quantidade=1)
    jornadas, _ = carregar_jornadas(tmp_path)
    resumo = montar_resumo(jornadas)

    assert horas_produtiva_nao_rentavel_do_resumo(resumo) == timedelta(minutes=45)


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
# Rotulos legiveis (ADR-0031)
# ----------------------------------------------------------------------
def test_rotulo_categoria_cobre_todos_os_valores_do_enum():
    # Nenhuma Categoria deveria cair no fallback categoria.value (cru) -
    # bug real relatado em 2026-07-31 ("o gestor nao tem de cabeca os
    # motivos, precisa ser descritivo"). Algumas categorias (ex.: DDS) tem
    # rotulo igual ao valor do enum por coincidencia - a sigla ja e um
    # rotulo legivel por si so - entao o que importa e ter entrada
    # explicita no dicionario, nao a string necessariamente diferir.
    for categoria in Categoria:
        assert categoria in ROTULOS_CATEGORIA, categoria
        assert rotulo_categoria(categoria) == ROTULOS_CATEGORIA[categoria]


def test_rotulo_categoria_none_e_sem_categoria():
    assert rotulo_categoria(None) == "Sem categoria"


def test_rotulo_motivo_formato_codigo_descricao():
    assert rotulo_motivo("EE07") == "EE07 - Reunião ou ADM"


def test_rotulo_motivo_codigo_desconhecido_cai_no_proprio_codigo():
    assert rotulo_motivo("CODIGO_QUE_NAO_EXISTE") == "CODIGO_QUE_NAO_EXISTE"


def test_rotulo_motivo_none_e_sem_motivo():
    assert rotulo_motivo(None) == "Sem motivo"


def test_utilizacao_hh_por_colaborador_com_dados_de_exemplo(tmp_path):
    gerar_jornadas_exemplo(tmp_path, quantidade=2)
    jornadas, _ = carregar_jornadas(tmp_path)

    por_colaborador = utilizacao_hh_por_colaborador(jornadas)

    assert set(por_colaborador.keys()) == {j.colaborador_matricula for j in jornadas}
    assert all(fracao is not None and 0 < fracao <= 1 for fracao in por_colaborador.values())


def test_contagem_e_duracao_media_por_motivo_ignora_atividade_sem_motivo():
    linhas = [
        LinhaEvento("1", date(2026, 7, 1), Categoria.ATIVIDADE_PLANEJADA, None, timedelta(hours=3), "ATIVIDADE"),
        LinhaEvento("1", date(2026, 7, 1), Categoria.REFEICAO, "EE02", timedelta(hours=1), "PAUSA"),
        LinhaEvento("2", date(2026, 7, 2), Categoria.REFEICAO, "EE02", timedelta(minutes=30), "PAUSA"),
    ]

    resultado = contagem_e_duracao_media_por_motivo(linhas)

    assert resultado == {"EE02": (2, timedelta(minutes=45))}


# ----------------------------------------------------------------------
# Graficos - Visao Geral
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
    assert "Atividade planejada" in html
    assert "Sem categoria" in html


def test_grafico_distribuicao_pizza_renderiza_html_autocontido():
    por_categoria = {Categoria.DESLOCAMENTO_RODOVIARIO: timedelta(minutes=30)}
    grafico = grafico_distribuicao_pizza(por_categoria)
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert _contido("Deslocamento rodoviário", html)


def test_grafico_distribuicao_pizza_usa_cor_por_rotulo_pedido_2026_08_07():
    # Mesma categoria = mesma cor em qualquer grafico do painel (e no mapa
    # operacional) - nunca a paleta automatica do pyecharts.
    from mapa import cor_por_rotulo

    por_categoria = {Categoria.DESLOCAMENTO_RODOVIARIO: timedelta(minutes=30)}
    grafico = grafico_distribuicao_pizza(por_categoria)
    html = renderizar_embutido(grafico)

    cor_esperada = cor_por_rotulo(rotulo_categoria(Categoria.DESLOCAMENTO_RODOVIARIO))
    assert cor_esperada.lower() in html.lower()


def test_grafico_hh_por_colaborador_usa_cor_por_rotulo_pedido_2026_08_07():
    from mapa import cor_por_rotulo

    grafico = grafico_hh_por_colaborador(_linhas_evento_exemplo())
    html = renderizar_embutido(grafico)

    cor_esperada = cor_por_rotulo(rotulo_categoria(Categoria.ATIVIDADE_PLANEJADA))
    assert cor_esperada.lower() in html.lower()


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
    assert "Atividade planejada" in html


def test_grafico_hh_por_motivo_ignora_linhas_sem_motivo_e_usa_rotulo_descritivo():
    grafico, altura_px = grafico_hh_por_motivo(_linhas_evento_exemplo())
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert _contido("EE02 - Refeição 1 hora", html)
    assert altura_px > 0


def test_grafico_utilizacao_por_colaborador_ordena_do_maior_para_o_menor():
    grafico = grafico_utilizacao_por_colaborador({"C1": 0.4, "C2": 0.9, "C3": None})

    # Inspeciona o eixo X (categorias) direto no JSON de opcoes do ECharts,
    # em vez de procurar a substring "C3" no HTML renderizado - o HTML
    # embute 1MB+ de JS do ECharts, que tem codigos de cor hexadecimais
    # (ex.: "#B0B6C3") onde "C3" aparece por coincidencia, dando falso
    # positivo numa checagem ingenua de substring.
    opcoes = json.loads(grafico.dump_options())
    categorias_eixo_x = opcoes["xAxis"][0]["data"]
    assert categorias_eixo_x == ["C2", "C1"]  # ordenado do maior para o menor, C3 (None) fora

    html = renderizar_embutido(grafico)
    assert "<script>" in html
    assert "cdn" not in html.lower()


def test_grafico_scatter_duracao_frequencia_renderiza_com_rotulo_descritivo():
    dados_scatter = {"EE07": (5, timedelta(minutes=30)), "EE12": (2, timedelta(hours=2))}
    html = renderizar_embutido(grafico_scatter_duracao_frequencia(dados_scatter))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert _contido("EE07 - Reunião ou ADM", html)
    assert _contido("EE12 - Deslocamento rodoviário", html)


def test_grafico_sankey_colaborador_categoria_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_sankey_colaborador_categoria(_linhas_evento_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "Atividade planejada" in html


def test_grafico_gauge_percentual_renderiza_sem_texto_duplicado():
    grafico = grafico_gauge_percentual("Utilização HH", 0.75)
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "75" in html
    # Bug real de 2026-07-31: o titulo interno do gauge duplicava
    # literalmente o texto do card KPI do Streamlit, sobrepondo os dois -
    # o texto do titulo nao deve mais aparecer dentro do grafico.
    assert not _contido("Utilização HH", html)


def test_renderizar_embutido_falha_se_asset_local_ausente(tmp_path, monkeypatch):
    import graficos

    caminho_falso = tmp_path / "nao-existe.js"
    monkeypatch.setattr(graficos, "CAMINHO_ECHARTS_JS_LOCAL", caminho_falso)

    grafico = grafico_hh_por_categoria({Categoria.ATIVIDADE_PLANEJADA: timedelta(hours=1)})
    with pytest.raises(FileNotFoundError):
        renderizar_embutido(grafico)


# ----------------------------------------------------------------------
# Graficos - Falhas (ADR-0029/0031)
# ----------------------------------------------------------------------
def _linhas_falha_exemplo():
    return [
        LinhaAtendimentoFalha(
            "1", date(2026, 7, 1), datetime(2026, 7, 1, 8), datetime(2026, 7, 1, 9),
            timedelta(hours=1), "1", "ATIVO-A", "Sintoma A", "Componente X",
        ),
        LinhaAtendimentoFalha(
            "2", date(2026, 7, 2), datetime(2026, 7, 2, 8), datetime(2026, 7, 2, 16),
            timedelta(hours=8), "2", "ATIVO-A", "Sintoma B", "Componente Y",
        ),
    ]


def test_grafico_ranking_duracao_falhas_renderiza_html_autocontido():
    grafico, altura_px = grafico_ranking_duracao_falhas(_linhas_falha_exemplo())
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "Sintoma A" in html
    assert altura_px > 0


def test_grafico_donut_contagem_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_donut_contagem("Ocorrências por sintoma", {"Sintoma A": 3, "Sintoma B": 1}))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "Sintoma A" in html


def test_grafico_evolucao_diaria_falhas_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_evolucao_diaria_falhas(_linhas_falha_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "01/07/2026" in html
    assert "02/07/2026" in html


def test_grafico_hh_falhas_por_colaborador_renderiza_html_autocontido():
    html = renderizar_embutido(grafico_hh_falhas_por_colaborador(_linhas_falha_exemplo()))

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "1" in html and "2" in html


def test_grafico_duracao_media_por_sintoma_renderiza_html_autocontido():
    grafico, altura_px = grafico_duracao_media_por_sintoma({"Sintoma A": timedelta(hours=2)})
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "Sintoma A" in html
    assert altura_px > 0


def test_grafico_reincidencia_ativos_renderiza_html_autocontido():
    grafico, altura_px = grafico_reincidencia_ativos({"ATIVO-A": 3})
    html = renderizar_embutido(grafico)

    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "ATIVO-A" in html
    assert altura_px > 0


def test_grafico_funil_duracao_por_sintoma_soma_entre_ativos():
    # ADR-0033: o funil colapsa a dimensao "ativo" - duracao do mesmo
    # sintoma em ativos diferentes precisa ser somada num unico item do
    # funil, nao aparecer duplicada.
    agrupado = {
        "ATIVO-A": {"Sintoma A": timedelta(hours=1), "Sintoma B": timedelta(minutes=30)},
        "ATIVO-B": {"Sintoma A": timedelta(hours=2)},
    }
    grafico = grafico_funil_duracao_por_sintoma(agrupado)

    opcoes = json.loads(grafico.dump_options())
    dados_funil = {item["name"]: item["value"] for item in opcoes["series"][0]["data"]}
    assert dados_funil["Sintoma A"] == 3.0  # 1h (ATIVO-A) + 2h (ATIVO-B)
    assert dados_funil["Sintoma B"] == 0.5

    html = renderizar_embutido(grafico)
    assert "<script>" in html
    assert "cdn" not in html.lower()
    assert "Sintoma A" in html
    assert "Sintoma A" in html
