"""Testes do Incremento 10: mapa operacional (Folium) e geracao de pulsos de exemplo.

mapa.py e testavel diretamente (folium.Map e um objeto Python comum, sem
depender do runtime do Streamlit) - o smoke test real do servidor
(`streamlit run`) fica em docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md.
"""

import json
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import folium
import pytest

from dados import (
    filtrar_pulsos_por_periodo,
    gerar_jornadas_exemplo,
    gerar_pulsos_exemplo,
    reclassificar_qualidade_pulsos,
)
from mapa import (
    _COR_MALHA_FERREA,
    _COR_PULSO_BRUTO,
    _COR_QUALIDADE_SUSPEITA,
    _COR_SEM_ATIVIDADE,
    _COR_TRAJETORIA,
    construir_mapa,
    cor_por_rotulo,
    resumo_jornada_com_localizacao,
    rotulo_classificacao_pulso,
)
from workforce_core import MotorJornada
from workforce_core.consolidacao import ClassificacaoInstante
from workforce_core.entities import PulsoGps
from workforce_core.enums import QualidadePulso


def _contido(rotulo: str, html: str) -> bool:
    """Confere se `rotulo` aparece no HTML gerado pelo Folium, cru ou
    escapado como `json.dumps` (padrao `ensure_ascii=True`) grava nomes de
    camada dentro do <script> do LayerControl - "ç"/"ó" viram literalmente
    "\\u00e7"/"\\u00f3" no HTML, nao o caractere em si (mesmo fenomeno de
    `_contido` em test_painel.py, so que no Folium em vez do pyecharts)."""
    return rotulo in html or json.dumps(rotulo)[1:-1] in html


def test_gerar_pulsos_exemplo_cobre_o_periodo_da_jornada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]

    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=300)

    assert len(pulsos) > 1
    assert pulsos[0].timestamp_dispositivo >= jornada.inicio
    assert pulsos[-1].timestamp_dispositivo <= jornada.fim
    assert all(p.jornada_id == jornada.id for p in pulsos)


def test_gerar_pulsos_exemplo_e_deterministico_por_jornada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]

    pulsos_a = gerar_pulsos_exemplo(tmp_path / "pulsos_a", jornada, intervalo_segundos=300)
    pulsos_b = gerar_pulsos_exemplo(tmp_path / "pulsos_b", jornada, intervalo_segundos=300)

    assert [(p.latitude, p.longitude) for p in pulsos_a] == [
        (p.latitude, p.longitude) for p in pulsos_b
    ]


def test_construir_mapa_sem_pulsos_nao_quebra():
    mapa = construir_mapa(
        [],
        distancia_simplificacao_metros=50,
        raio_cluster_metros=20,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    assert isinstance(mapa, folium.Map)


def test_construir_mapa_com_pulsos_gera_camadas(tmp_path):
    # Pedido do responsavel pelo produto em 2026-08-04 (ADR-0049): pulsos
    # brutos sao sempre desenhados direto no mapa (sem FeatureGroup/toggle
    # proprio - ja sao selecionaveis pelos filtros de atividade/data/
    # horario da tela) - so a trajetoria continua como camada nomeada/
    # togglable no LayerControl.
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=180)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )

    html = mapa.get_root().render()
    assert html.count("L.circleMarker(") >= len(pulsos)  # um marcador por pulso, sempre visivel
    assert _contido("Traçar trajetória", html)


def test_popup_escapa_html_de_campos_controlados_pelo_usuario(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    jornada.colaborador_matricula = "<script>alert(1)</script>"

    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        mostrar_pulsos_brutos=True,
    )

    html = mapa.get_root().render()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_construir_mapa_pulsos_brutos_em_amarelo(tmp_path):
    # Pedido do responsavel pelo produto em 2026-08-04: pulso bruto sempre
    # amarelo (a qualidade continua no popup, so deixou de ser codificada
    # por cor do marcador).
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert _COR_PULSO_BRUTO in html


def test_construir_mapa_trajetoria_vermelha_tracejada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=180)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert _COR_TRAJETORIA in html
    assert "dashArray" in html  # folium traduz dash_array para a opcao Leaflet dashArray


def test_construir_mapa_malha_ferrea_sempre_visivel_sem_toggle(tmp_path):
    # ADR-0049: malha ferrea desenhada direto no mapa, nunca como camada
    # nomeada/togglable - "Malha ferrea MRS" aqui e so o texto do tooltip
    # de cada trecho, nao um nome de FeatureGroup no LayerControl.
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    trilho = [(-19.97, -44.01), (-19.98, -44.02), (-19.99, -44.03)]

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        trilhos_ferrovia=[trilho],
    )
    html = mapa.get_root().render()
    assert "Malha ferrea MRS" in html
    assert _COR_MALHA_FERREA in html
    # Nunca vira uma entrada do LayerControl (so "Tracar trajetoria" e).
    assert '"Malha ferrea MRS" :' not in html


def test_construir_mapa_sem_pulsos_ainda_mostra_malha_ferrea():
    # A malha ferrea e uma camada de referencia estatica - nao deveria
    # depender de existir alguma jornada/pulso pra aparecer.
    trilho = [(-19.97, -44.01), (-19.98, -44.02)]

    mapa = construir_mapa(
        [],
        distancia_simplificacao_metros=50,
        raio_cluster_metros=20,
        tempo_minimo_cluster=timedelta(minutes=5),
        trilhos_ferrovia=[trilho],
    )
    html = mapa.get_root().render()
    assert "Malha ferrea MRS" in html


# ----------------------------------------------------------------------
# Rotulo/cor por classificacao (pedido do responsavel pelo produto em
# 2026-08-04, ver ADR-0047) e marcos de inicio/fim.
# ----------------------------------------------------------------------
def test_rotulo_classificacao_pulso_por_tipo():
    assert rotulo_classificacao_pulso(ClassificacaoInstante("ATIVIDADE", None)) == "Atividade"
    assert (
        rotulo_classificacao_pulso(ClassificacaoInstante("ATENDIMENTO_FALHA", None))
        == "Atendimento de falha"
    )
    assert rotulo_classificacao_pulso(ClassificacaoInstante("SEM_ATIVIDADE", None)) == "Sem atividade"


def test_rotulo_classificacao_pulso_pausa_usa_rotulo_motivo():
    # Sem catalogo informado, rotulo_motivo cai no proprio codigo (ver
    # painel/dados.py::rotulo_motivo).
    rotulo = rotulo_classificacao_pulso(ClassificacaoInstante("PAUSA", "EE02"))
    assert "EE02" in rotulo


def test_cor_por_rotulo_e_deterministica():
    assert cor_por_rotulo("EE02 - Refeicao") == cor_por_rotulo("EE02 - Refeicao")
    assert cor_por_rotulo("Sem atividade") == _COR_SEM_ATIVIDADE


def test_cor_por_rotulo_rotulos_diferentes_tendem_a_cores_diferentes():
    cores = {cor_por_rotulo(f"Categoria {i}") for i in range(8)}
    assert len(cores) > 1  # nao deveria colapsar tudo numa cor so


def test_construir_mapa_marcos_de_inicio_e_fim(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        marco_inicio=pulsos[0],
        marco_fim=pulsos[-1],
    )
    html = mapa.get_root().render()
    assert "Inicio da jornada" in html
    assert "Fim da jornada" in html
    assert '"green"' in html
    assert '"red"' in html
    # Marcos sao desenhados direto no mapa (ADR-0049) - nunca viram uma
    # camada nomeada/togglable no LayerControl.
    assert "Inicio e fim" not in html


def test_construir_mapa_cor_por_pulso_sobrescreve_amarelo_padrao(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    cor_customizada = "#1E88E5"
    cor_por_pulso = {pulso.id: cor_customizada for pulso in pulsos}

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        cor_por_pulso=cor_por_pulso,
    )
    html = mapa.get_root().render()
    assert cor_customizada in html
    assert _COR_PULSO_BRUTO not in html


def test_construir_mapa_rotulo_por_pulso_aparece_no_popup(tmp_path):
    # Pedido do responsavel pelo produto em 2026-08-07: o popup do pulso so
    # mostrava qualidade, sem dar pra saber qual atividade era so pela cor.
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    rotulo_por_pulso = {pulso.id: "EE07 - Reunião ou ADM" for pulso in pulsos}

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
        rotulo_por_pulso=rotulo_por_pulso,
    )
    html = mapa.get_root().render()
    assert "Atividade/Evento:" in html
    assert "EE07" in html


def test_construir_mapa_sem_rotulo_por_pulso_nao_mostra_linha_de_atividade(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert "Atividade/Evento:" not in html


# ----------------------------------------------------------------------
# Filtro de data + faixa de horario (pedido do responsavel pelo produto
# em 2026-08-04, ver ADR-0047).
# ----------------------------------------------------------------------
def test_filtrar_pulsos_por_periodo_faixa_do_dia_inteiro_nao_filtra_nada(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    data_jornada = pulsos[0].timestamp_dispositivo.date()

    filtrados = filtrar_pulsos_por_periodo(
        pulsos, data_jornada, data_jornada, time(0, 0), time(23, 59, 59)
    )
    assert filtrados == pulsos


def test_filtrar_pulsos_por_periodo_data_diferente_devolve_vazio(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)

    filtrados = filtrar_pulsos_por_periodo(
        pulsos, date(1999, 1, 1), date(1999, 1, 1), time(0, 0), time(23, 59, 59)
    )
    assert filtrados == []


def test_filtrar_pulsos_por_periodo_estreita_por_horario(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    data_jornada = pulsos[0].timestamp_dispositivo.date()
    inicio = pulsos[0].timestamp_dispositivo.time()

    filtrados = filtrar_pulsos_por_periodo(pulsos, data_jornada, data_jornada, inicio, inicio)
    assert filtrados == [pulsos[0]]


def test_filtrar_pulsos_por_periodo_converte_utc_para_horario_de_brasilia():
    # Bug que este filtro evita (mesma familia do ADR-0047): um pulso as
    # 23h de Brasilia (02h UTC do dia seguinte) precisa continuar
    # aparecendo no filtro do dia certo (Brasilia), nao do dia UTC.
    pulso_23h_brasilia = PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="12345",
        latitude=-23.5,
        longitude=-46.6,
        precisao_metros=10.0,
        timestamp_dispositivo=datetime(2026, 8, 5, 2, 0, tzinfo=timezone.utc),  # 04/08 23h em Brasilia
    )

    filtrados = filtrar_pulsos_por_periodo(
        [pulso_23h_brasilia], date(2026, 8, 4), date(2026, 8, 4), time(22, 0), time(23, 59, 59)
    )
    assert filtrados == [pulso_23h_brasilia]


def test_filtrar_pulsos_por_periodo_intervalo_de_datas_cobre_jornada_que_atravessa_meia_noite():
    # Bug real relatado pelo responsavel do produto em 2026-08-12 (ADR-0067):
    # jornada iniciada as 19h49 de um dia e encerrada no dia seguinte -
    # antes deste teste, o filtro so aceitava 1 dia e os pulsos depois da
    # meia-noite de Brasilia sumiam do mapa sem o usuario mudar a data.
    pulso_dia_1 = PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="7777777",
        latitude=-23.5,
        longitude=-46.6,
        precisao_metros=10.0,
        timestamp_dispositivo=datetime(2026, 8, 6, 22, 49, tzinfo=timezone.utc),  # 19h49 Brasilia
    )
    pulso_dia_2 = PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="7777777",
        latitude=-23.5,
        longitude=-46.6,
        precisao_metros=10.0,
        timestamp_dispositivo=datetime(2026, 8, 7, 6, 0, tzinfo=timezone.utc),  # 03h Brasilia do dia seguinte
    )

    filtrados = filtrar_pulsos_por_periodo(
        [pulso_dia_1, pulso_dia_2],
        date(2026, 8, 6),
        date(2026, 8, 7),
        time(0, 0),
        time(23, 59, 59),
    )
    assert filtrados == [pulso_dia_1, pulso_dia_2]


# ----------------------------------------------------------------------
# Qualidade de GPS (ADR-0054): limiares aprovados pelo responsavel do
# produto em 2026-08-05 (precisao <= 100m, velocidade implicita <= 50 m/s),
# wireados em painel/dados.py::reclassificar_qualidade_pulsos e refletidos
# no mapa (painel/mapa.py) - motivado por um pulso final real de jornada
# aparecendo longe do local certo, nunca filtrado por nada.
# ----------------------------------------------------------------------
def _pulso(
    *, latitude=-23.5505, longitude=-46.6333, precisao_metros=10.0, minutos_apos_epoca=0
):
    return PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula="12345",
        latitude=latitude,
        longitude=longitude,
        precisao_metros=precisao_metros,
        timestamp_dispositivo=datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc)
        + timedelta(minutes=minutos_apos_epoca),
    )


def test_reclassificar_qualidade_pulsos_marca_ok_dentro_dos_limiares():
    pulsos = [_pulso(precisao_metros=10.0, minutos_apos_epoca=0)]
    resultado = reclassificar_qualidade_pulsos(pulsos)
    assert resultado[0].qualidade == QualidadePulso.OK


def test_reclassificar_qualidade_pulsos_marca_precisao_ruim_acima_de_100m():
    pulsos = [_pulso(precisao_metros=150.0, minutos_apos_epoca=0)]
    resultado = reclassificar_qualidade_pulsos(pulsos)
    assert resultado[0].qualidade == QualidadePulso.PRECISAO_RUIM


def test_reclassificar_qualidade_pulsos_marca_salto_impossivel():
    # ~111km de distancia (1 grau de latitude) em 60s = ~1850 m/s, muito
    # acima do limiar de 50 m/s aprovado - exatamente o tipo de "pulso
    # final longe do local certo" relatado em producao.
    pulsos = [
        _pulso(latitude=-23.5505, longitude=-46.6333, minutos_apos_epoca=0),
        _pulso(latitude=-22.5505, longitude=-46.6333, minutos_apos_epoca=1),
    ]
    resultado = reclassificar_qualidade_pulsos(pulsos)
    assert resultado[0].qualidade == QualidadePulso.OK
    assert resultado[1].qualidade == QualidadePulso.SALTO_IMPOSSIVEL


def test_reclassificar_qualidade_pulsos_nao_muta_a_lista_original():
    original = [_pulso(precisao_metros=150.0)]
    reclassificar_qualidade_pulsos(original)
    assert original[0].qualidade == QualidadePulso.NAO_AVALIADO


def test_reclassificar_qualidade_pulsos_avalia_em_ordem_cronologica():
    # Entrada fora de ordem (pulso mais novo primeiro na lista) nao
    # deveria inverter quem e "anterior" no calculo de velocidade.
    mais_novo = _pulso(latitude=-22.5505, longitude=-46.6333, minutos_apos_epoca=1)
    mais_antigo = _pulso(latitude=-23.5505, longitude=-46.6333, minutos_apos_epoca=0)

    resultado = reclassificar_qualidade_pulsos([mais_novo, mais_antigo])

    assert resultado[0].timestamp_dispositivo == mais_antigo.timestamp_dispositivo
    assert resultado[0].qualidade == QualidadePulso.OK
    assert resultado[1].qualidade == QualidadePulso.SALTO_IMPOSSIVEL


def test_construir_mapa_pulso_suspeito_ganha_marcador_distinto(tmp_path):
    jornadas = gerar_jornadas_exemplo(tmp_path / "jornadas", quantidade=1)
    jornada = jornadas[0]
    pulsos = gerar_pulsos_exemplo(tmp_path / "pulsos", jornada, intervalo_segundos=600)
    pulsos[-1] = replace(pulsos[-1], qualidade=QualidadePulso.PRECISAO_RUIM)

    mapa = construir_mapa(
        pulsos,
        distancia_simplificacao_metros=30,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert _COR_QUALIDADE_SUSPEITA in html


def test_construir_mapa_pulso_suspeito_fica_fora_da_trajetoria(tmp_path):
    # So 2 pulsos, um deles suspeito -> so sobra 1 pulso confiavel depois
    # do filtro, e simplificar_trajetoria nunca desenha uma linha com um
    # unico ponto - a camada "Tracar trajetoria" nao deveria aparecer.
    pulso_ok = _pulso(latitude=-23.5505, longitude=-46.6333, minutos_apos_epoca=0)
    pulso_suspeito = replace(
        _pulso(latitude=-22.0, longitude=-46.6333, minutos_apos_epoca=1),
        qualidade=QualidadePulso.SALTO_IMPOSSIVEL,
    )

    mapa = construir_mapa(
        [pulso_ok, pulso_suspeito],
        distancia_simplificacao_metros=0,
        raio_cluster_metros=25,
        tempo_minimo_cluster=timedelta(minutes=5),
    )
    html = mapa.get_root().render()
    assert not _contido("Traçar trajetória", html)


# ----------------------------------------------------------------------
# resumo_jornada_com_localizacao (tabela resumo, pedido do responsavel do
# produto em 2026-08-07).
# ----------------------------------------------------------------------
def _pulso_no_instante(momento: datetime, matricula: str = "12345") -> PulsoGps:
    return PulsoGps(
        jornada_id=uuid4(),
        colaborador_matricula=matricula,
        latitude=-23.5505,
        longitude=-46.6333,
        precisao_metros=10.0,
        timestamp_dispositivo=momento,
    )


def test_resumo_jornada_com_localizacao_pega_pulso_mais_proximo_de_inicio_e_fim():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(datetime(2026, 1, 1, 8, 0))
    motor.iniciar_atividade(datetime(2026, 1, 1, 8, 10))
    motor.encerrar_atividade(datetime(2026, 1, 1, 9, 0))
    motor.encerrar_jornada(datetime(2026, 1, 1, 9, 0))

    # Pulso exatamente no inicio/fim da atividade (GPS obrigatorio em toda
    # transicao, ADR-0043/0048 - o caso real e exatamente este) + um pulso
    # de "ruido" bem mais longe no tempo, que nunca deveria ser escolhido.
    pulso_inicio = _pulso_no_instante(datetime(2026, 1, 1, 8, 10))
    pulso_fim = _pulso_no_instante(datetime(2026, 1, 1, 9, 0))
    pulso_ruido = _pulso_no_instante(datetime(2026, 1, 1, 23, 0))

    resumo = resumo_jornada_com_localizacao(motor.jornada, [pulso_ruido, pulso_inicio, pulso_fim])

    assert len(resumo) == 1
    linha = resumo[0]
    assert linha.atividade_evento == "Atividade"
    assert linha.inicio == datetime(2026, 1, 1, 8, 10)
    assert linha.fim == datetime(2026, 1, 1, 9, 0)
    assert linha.localizacao_inicio is pulso_inicio
    assert linha.localizacao_fim is pulso_fim


def test_resumo_jornada_com_localizacao_ignora_sem_atividade():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(datetime(2026, 1, 1, 8, 0))
    motor.iniciar_atividade(datetime(2026, 1, 1, 8, 30))  # lacuna 8:00-8:30 = SEM_ATIVIDADE
    motor.encerrar_atividade(datetime(2026, 1, 1, 9, 0))
    motor.encerrar_jornada(datetime(2026, 1, 1, 9, 0))

    resumo = resumo_jornada_com_localizacao(motor.jornada, [])

    assert len(resumo) == 1  # so a Atividade - a lacuna SEM_ATIVIDADE nao vira linha
    assert resumo[0].atividade_evento == "Atividade"


def test_resumo_jornada_com_localizacao_sem_pulsos_devolve_localizacao_none():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(datetime(2026, 1, 1, 8, 0))
    motor.iniciar_atividade(datetime(2026, 1, 1, 8, 10))
    motor.encerrar_atividade(datetime(2026, 1, 1, 9, 0))
    motor.encerrar_jornada(datetime(2026, 1, 1, 9, 0))

    resumo = resumo_jornada_com_localizacao(motor.jornada, [])

    assert resumo[0].localizacao_inicio is None
    assert resumo[0].localizacao_fim is None


def test_resumo_jornada_com_localizacao_pausa_usa_rotulo_do_motivo():
    motor = MotorJornada("12345")
    motor.iniciar_jornada(datetime(2026, 1, 1, 8, 0))
    motor.iniciar_atividade(datetime(2026, 1, 1, 8, 10))
    motor.iniciar_pausa(datetime(2026, 1, 1, 9, 0), "EE02")
    motor.finalizar_pausa(datetime(2026, 1, 1, 9, 15))
    motor.encerrar_atividade(datetime(2026, 1, 1, 10, 0))
    motor.encerrar_jornada(datetime(2026, 1, 1, 10, 0))

    resumo = resumo_jornada_com_localizacao(motor.jornada, [])

    rotulos = [linha.atividade_evento for linha in resumo]
    assert any("EE02" in rotulo for rotulo in rotulos)
