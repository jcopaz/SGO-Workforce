"""Testes de workforce_core/fuso_horario.py - conversao para o horario de
Brasilia usada no limite de apresentacao/agrupamento por dia do painel
(ADR-0047, pedido do responsavel pelo produto em 2026-08-04: "calibre
todo o aplicativo para o timezone do Brasil")."""

from datetime import datetime, timezone

from workforce_core.fuso_horario import FUSO_BRASIL, para_horario_brasil


def test_para_horario_brasil_converte_utc_aware_para_horario_local():
    momento_utc = datetime(2026, 8, 4, 17, 0, 0, tzinfo=timezone.utc)

    convertido = para_horario_brasil(momento_utc)

    assert convertido.hour == 14
    assert convertido.tzinfo == FUSO_BRASIL


def test_para_horario_brasil_evento_proximo_a_meia_noite_fica_no_dia_certo():
    # 23h de Brasilia em 04/08 corresponde a 02h UTC do dia 05/08 - a data
    # calendario de Brasilia (04/08) e a que importa para agrupamentos por
    # dia no painel, nunca a data UTC.
    momento_utc = datetime(2026, 8, 5, 2, 0, 0, tzinfo=timezone.utc)

    convertido = para_horario_brasil(momento_utc)

    assert convertido.date().isoformat() == "2026-08-04"
    assert convertido.hour == 23


def test_para_horario_brasil_naive_passa_direto_sem_alterar():
    momento_naive = datetime(2026, 8, 4, 14, 0, 0)

    convertido = para_horario_brasil(momento_naive)

    assert convertido == momento_naive
    assert convertido.tzinfo is None


def test_para_horario_brasil_none_devolve_none():
    assert para_horario_brasil(None) is None
