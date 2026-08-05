"""Testes do Incremento 7: pulsos GPS, qualidade e sincronizacao em lote.

Cobre as regras de docs/08_GPS_PULSOS_E_PRIVACIDADE.md: precisao original
nunca descartada, pontos impossiveis/saltos/velocidade incompativel
marcados (nao sobrescritos), e a garantia de nao perder pulsos ja
gravados mesmo com uma linha corrompida no meio do arquivo.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from workforce_core import PulsoGps, QualidadePulso, qualidade_gps
from workforce_storage.repositorio_pulsos_gps import RepositorioPulsosGpsArquivo
from workforce_storage.serializacao import pulso_gps_de_dict, pulso_gps_para_dict
from workforce_sync import (
    ClienteSincronizacaoEmMemoria,
    RepositorioCursorPulsosArquivo,
    SincronizadorPulsos,
)


def _dt(segundos):
    return datetime(2026, 1, 1, 8, 0, 0) + timedelta(seconds=segundos)


def _pulso(jornada_id, segundos, *, lat=0.0, lon=0.0, precisao=10.0, velocidade=None):
    return PulsoGps(
        jornada_id=jornada_id,
        colaborador_matricula="12345",
        latitude=lat,
        longitude=lon,
        precisao_metros=precisao,
        timestamp_dispositivo=_dt(segundos),
        velocidade_metros_segundo=velocidade,
    )


# ----------------------------------------------------------------------
# Qualidade
# ----------------------------------------------------------------------
def test_distancia_metros_entre_pontos_proximos():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, lat=0.0, lon=0.0)
    p2 = _pulso(jornada_id, 60, lat=0.001, lon=0.0)  # ~111m ao norte

    distancia = qualidade_gps.distancia_metros(p1, p2)
    assert 100 < distancia < 120


def test_avaliar_pulso_ok():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, lat=0.0, lon=0.0, precisao=10)
    p2 = _pulso(jornada_id, 60, lat=0.001, lon=0.0, precisao=10)

    qualidade = qualidade_gps.avaliar_pulso(
        p2,
        p1,
        precisao_maxima_aceitavel_metros=50,
        velocidade_maxima_plausivel_metros_segundo=30,
    )
    assert qualidade == QualidadePulso.OK


def test_avaliar_pulso_precisao_ruim():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, precisao=500)

    qualidade = qualidade_gps.avaliar_pulso(
        p1,
        None,
        precisao_maxima_aceitavel_metros=50,
        velocidade_maxima_plausivel_metros_segundo=30,
    )
    assert qualidade == QualidadePulso.PRECISAO_RUIM


def test_avaliar_pulso_salto_impossivel():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, lat=0.0, lon=0.0, precisao=10)
    p2 = _pulso(jornada_id, 60, lat=1.0, lon=0.0, precisao=10)  # ~111km em 60s

    qualidade = qualidade_gps.avaliar_pulso(
        p2,
        p1,
        precisao_maxima_aceitavel_metros=50,
        velocidade_maxima_plausivel_metros_segundo=30,
    )
    assert qualidade == QualidadePulso.SALTO_IMPOSSIVEL


def test_avaliar_pulso_velocidade_incompativel_reportada_pelo_dispositivo():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, precisao=10, velocidade=200.0)

    qualidade = qualidade_gps.avaliar_pulso(
        p1,
        None,
        precisao_maxima_aceitavel_metros=50,
        velocidade_maxima_plausivel_metros_segundo=30,
    )
    assert qualidade == QualidadePulso.VELOCIDADE_INCOMPATIVEL


def test_avaliar_pulso_nao_descarta_precisao_original():
    jornada_id = uuid4()
    p1 = _pulso(jornada_id, 0, precisao=500)
    qualidade_gps.avaliar_pulso(
        p1, None, precisao_maxima_aceitavel_metros=50, velocidade_maxima_plausivel_metros_segundo=30
    )
    assert p1.precisao_metros == 500  # nao foi alterado pela avaliacao


def test_round_trip_serializacao_pulso():
    jornada_id = uuid4()
    pulso = _pulso(jornada_id, 0, lat=-23.5, lon=-46.6, precisao=12.5, velocidade=3.2)
    pulso.qualidade = QualidadePulso.OK

    dados = pulso_gps_para_dict(pulso)
    recarregado = pulso_gps_de_dict(dados)

    assert recarregado.id == pulso.id
    assert recarregado.latitude == pulso.latitude
    assert recarregado.qualidade == QualidadePulso.OK
    assert recarregado.timestamp_recebimento_servidor is None


# ----------------------------------------------------------------------
# Repositorio append-only
# ----------------------------------------------------------------------
def test_gravar_e_ler_pulsos_em_ordem(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    pulsos = [_pulso(jornada_id, i * 60) for i in range(5)]
    for pulso in pulsos:
        repo.gravar_pulso(pulso)

    lidos = repo.ler_pulsos(jornada_id)
    assert [p.id for p in lidos] == [p.id for p in pulsos]
    assert repo.contar_pulsos(jornada_id) == 5


def test_gravar_lote_grava_todos_os_pulsos(tmp_path):
    # ADR-0042/0043 (Fase 1): gravar_lote existe pra ter a mesma forma
    # publica de RepositorioPulsosGpsPostgres.gravar_lote - o endpoint
    # POST /pulsos usa isso, injetando esse repositorio de arquivo nos
    # testes (ver tests/test_workforce_api.py).
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    pulsos = [_pulso(jornada_id, i * 60) for i in range(3)]

    repo.gravar_lote(pulsos)

    lidos = repo.ler_pulsos(jornada_id)
    assert [p.id for p in lidos] == [p.id for p in pulsos]


def test_ler_pulsos_de_jornada_sem_arquivo_retorna_vazio(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    assert repo.ler_pulsos(uuid4()) == []


def test_linha_corrompida_nao_apaga_as_demais(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    repo.gravar_pulso(_pulso(jornada_id, 0))
    repo.gravar_pulso(_pulso(jornada_id, 60))

    caminho = repo._caminho(jornada_id)
    with open(caminho, "a", encoding="utf-8") as arquivo:
        arquivo.write("isso nao e json valido\n")

    repo.gravar_pulso(_pulso(jornada_id, 120))

    pulsos, linhas_com_erro = repo.ler_pulsos_com_erros(jornada_id)
    assert len(pulsos) == 3
    assert linhas_com_erro == [3]


# ----------------------------------------------------------------------
# Expurgo por retencao (ADR-0043 decidiu 90 dias, ADR-0054 implementa)
# ----------------------------------------------------------------------
def test_apagar_pulsos_anteriores_a_remove_so_os_antigos(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    antigo = _pulso(jornada_id, 0)  # 08:00:00
    novo = _pulso(jornada_id, 600)  # 08:10:00
    repo.gravar_lote([antigo, novo])

    apagados = repo.apagar_pulsos_anteriores_a(datetime(2026, 1, 1, 8, 5, tzinfo=timezone.utc))

    assert apagados == 1
    restantes = repo.ler_pulsos(jornada_id)
    assert [p.id for p in restantes] == [novo.id]


def test_apagar_pulsos_anteriores_a_remove_arquivo_quando_fica_vazio(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    repo.gravar_pulso(_pulso(jornada_id, 0))

    apagados = repo.apagar_pulsos_anteriores_a(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))

    assert apagados == 1
    assert not repo._caminho(jornada_id).exists()
    assert repo.ler_pulsos(jornada_id) == []


def test_apagar_pulsos_anteriores_a_nao_mexe_em_pulsos_recentes(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    jornada_id = uuid4()
    pulso = _pulso(jornada_id, 0)
    repo.gravar_pulso(pulso)

    apagados = repo.apagar_pulsos_anteriores_a(datetime(2020, 1, 1, tzinfo=timezone.utc))

    assert apagados == 0
    assert repo.ler_pulsos(jornada_id) == [pulso]


def test_apagar_pulsos_anteriores_a_sem_jornada_nenhuma_devolve_zero(tmp_path):
    repo = RepositorioPulsosGpsArquivo(tmp_path)
    assert repo.apagar_pulsos_anteriores_a(datetime(2030, 1, 1, tzinfo=timezone.utc)) == 0


# ----------------------------------------------------------------------
# Sincronizacao em lote por cursor
# ----------------------------------------------------------------------
@pytest.fixture
def ambiente_pulsos(tmp_path):
    repo_pulsos = RepositorioPulsosGpsArquivo(tmp_path / "pulsos")
    repo_cursor = RepositorioCursorPulsosArquivo(tmp_path / "cursores")
    cliente = ClienteSincronizacaoEmMemoria()
    sincronizador = SincronizadorPulsos(repo_pulsos, repo_cursor, cliente)
    return repo_pulsos, repo_cursor, cliente, sincronizador


def test_sincronizar_pendentes_respeita_tamanho_do_lote(ambiente_pulsos):
    repo_pulsos, _repo_cursor, cliente, sincronizador = ambiente_pulsos
    jornada_id = uuid4()
    for i in range(5):
        repo_pulsos.gravar_pulso(_pulso(jornada_id, i * 60))

    relatorio1 = sincronizador.sincronizar_pendentes(jornada_id, tamanho_lote=2)
    assert relatorio1.enviados == 2
    assert relatorio1.sincronizados == 2
    assert len(cliente.pulsos_recebidos[jornada_id]) == 2

    relatorio2 = sincronizador.sincronizar_pendentes(jornada_id, tamanho_lote=2)
    assert relatorio2.enviados == 2
    assert len(cliente.pulsos_recebidos[jornada_id]) == 4

    relatorio3 = sincronizador.sincronizar_pendentes(jornada_id, tamanho_lote=2)
    assert relatorio3.enviados == 1
    assert len(cliente.pulsos_recebidos[jornada_id]) == 5

    relatorio4 = sincronizador.sincronizar_pendentes(jornada_id, tamanho_lote=2)
    assert relatorio4.enviados == 0
    assert relatorio4.sincronizados == 0


def test_sincronizar_tudo_esvazia_a_fila_em_varios_lotes(ambiente_pulsos):
    repo_pulsos, _repo_cursor, cliente, sincronizador = ambiente_pulsos
    jornada_id = uuid4()
    for i in range(5):
        repo_pulsos.gravar_pulso(_pulso(jornada_id, i * 60))

    relatorio = sincronizador.sincronizar_tudo(jornada_id, tamanho_lote=2)

    assert relatorio.enviados == 5
    assert relatorio.sincronizados == 5
    assert len(cliente.pulsos_recebidos[jornada_id]) == 5


def test_reenvio_apos_ack_perdido_nao_duplica(ambiente_pulsos):
    repo_pulsos, repo_cursor, cliente, sincronizador = ambiente_pulsos
    jornada_id = uuid4()
    for i in range(5):
        repo_pulsos.gravar_pulso(_pulso(jornada_id, i * 60))

    sincronizador.sincronizar_tudo(jornada_id, tamanho_lote=100)
    assert len(cliente.pulsos_recebidos[jornada_id]) == 5

    # Simula o cliente achando que o ultimo lote nao foi confirmado e
    # reenviando a partir de um ponto anterior do cursor.
    cursor = repo_cursor.carregar_ou_zero(jornada_id)
    cursor.total_sincronizado = 2
    repo_cursor.salvar(cursor)

    relatorio = sincronizador.sincronizar_pendentes(jornada_id, tamanho_lote=100)

    assert relatorio.enviados == 3
    assert len(cliente.pulsos_recebidos[jornada_id]) == 5  # sem duplicidade


def test_erro_de_rede_nao_avanca_o_cursor(ambiente_pulsos):
    repo_pulsos, repo_cursor, cliente, sincronizador = ambiente_pulsos
    jornada_id = uuid4()
    repo_pulsos.gravar_pulso(_pulso(jornada_id, 0))
    cliente.forcar_erro_pulsos(jornada_id)

    relatorio = sincronizador.sincronizar_pendentes(jornada_id)

    assert relatorio.com_erro is True
    assert relatorio.sincronizados == 0
    cursor = repo_cursor.carregar_ou_zero(jornada_id)
    assert cursor.total_sincronizado == 0

    # Sem forcar erro de novo, a proxima tentativa deve funcionar.
    relatorio2 = sincronizador.sincronizar_pendentes(jornada_id)
    assert relatorio2.sincronizados == 1
