"""Testes do Incremento 2: persistencia local e recuperacao de estado.

Cobre: nao perder registros ao fechar/reiniciar, preservar UUID, escrita
atomica, e nao apagar dados ao encontrar um arquivo corrompido (regra de
ouro do CLAUDE.md aplicada a persistencia local).
"""

import json
from datetime import datetime, timedelta

import pytest

from workforce_core import MotorJornada, calculo
from workforce_core.exceptions import EstadoInconsistenteError
from workforce_storage import ArquivoCorrompidoError, JornadaNaoEncontradaError, RepositorioJornadaArquivo


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def test_round_trip_fluxo_nominal_preserva_calculo(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(10, 0), motivo="PAUSA_TESTE")
    motor.finalizar_pausa(_dt(10, 20))
    motor.encerrar_atividade(_dt(12, 0))
    motor.encerrar_jornada(_dt(12, 10))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    jornada_recarregada = repo.carregar(motor.jornada.id)
    resumo = calculo.resumo_jornada(jornada_recarregada)

    assert calculo.duracao_jornada_bruta(jornada_recarregada) == timedelta(hours=4, minutes=10)
    assert resumo["tempo_classificado"] == timedelta(hours=3, minutes=50)
    assert resumo["tempo_nao_classificado"] == timedelta(minutes=20)


def test_ids_sao_preservados_no_round_trip(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.encerrar_atividade(_dt(9, 0))
    motor.encerrar_jornada(_dt(9, 10))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)
    recarregada = repo.carregar(motor.jornada.id)

    assert recarregada.id == motor.jornada.id
    assert recarregada.atividades[0].id == motor.jornada.atividades[0].id


def test_recuperacao_de_estado_apos_fechamento_abrupto(tmp_path):
    # Simula o app fechado com a jornada aberta, atividade ativa e uma
    # pausa em andamento (nada foi encerrado ainda).
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    motor.iniciar_pausa(_dt(9, 0), motivo="PAUSA_TESTE")

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    motor_recuperado = repo.carregar_motor(motor.jornada.id)

    # O motor recuperado deve continuar operavel a partir do ponto salvo.
    motor_recuperado.finalizar_pausa(_dt(9, 20))
    motor_recuperado.encerrar_atividade(_dt(10, 0))
    motor_recuperado.encerrar_jornada(_dt(10, 0))

    atividade = motor_recuperado.jornada.atividades[0]
    assert calculo.duracao_pausas_atividade(atividade) == timedelta(minutes=20)
    assert calculo.duracao_atividade_liquida(atividade) == timedelta(hours=1, minutes=30)


def test_recuperacao_com_atividade_ativa_sem_pausa(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    motor_recuperado = repo.carregar_motor(motor.jornada.id)
    motor_recuperado.encerrar_atividade(_dt(9, 0))
    motor_recuperado.encerrar_jornada(_dt(9, 10))

    assert motor_recuperado.jornada.atividades[0].fim == _dt(9, 0)


def test_escrita_e_atomica_sem_arquivo_temporario_residual(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))

    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    arquivos = list(tmp_path.glob("*"))
    assert len(arquivos) == 1
    assert arquivos[0].suffix == ".json"
    assert not any(arquivo.name.endswith(".tmp") for arquivo in arquivos)


def test_carregar_jornada_inexistente_leva_erro_dedicado(tmp_path):
    repo = RepositorioJornadaArquivo(tmp_path)
    from uuid import uuid4

    with pytest.raises(JornadaNaoEncontradaError):
        repo.carregar(uuid4())


def test_arquivo_json_invalido_nao_e_apagado(tmp_path):
    repo = RepositorioJornadaArquivo(tmp_path)
    from uuid import uuid4

    jornada_id = uuid4()
    caminho = tmp_path / f"{jornada_id}.json"
    caminho.write_text("{ isso nao e json valido", encoding="utf-8")

    with pytest.raises(ArquivoCorrompidoError):
        repo.carregar(jornada_id)

    # O arquivo continua no disco, intacto, para inspecao/recuperacao manual.
    assert caminho.exists()
    assert caminho.read_text(encoding="utf-8") == "{ isso nao e json valido"


def test_arquivo_com_estrutura_invalida_nao_e_apagado(tmp_path):
    repo = RepositorioJornadaArquivo(tmp_path)
    from uuid import uuid4

    jornada_id = uuid4()
    caminho = tmp_path / f"{jornada_id}.json"
    caminho.write_text(json.dumps({"id": str(jornada_id)}), encoding="utf-8")

    with pytest.raises(ArquivoCorrompidoError):
        repo.carregar(jornada_id)

    assert caminho.exists()


def test_estado_persistido_inconsistente_e_detectado(tmp_path):
    # Duas atividades ativas na mesma jornada nunca deveriam existir, mas o
    # repositorio precisa recusar esse estado em vez de aceitar cegamente
    # um arquivo adulterado ou corrompido de forma semantica.
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    motor.iniciar_atividade(_dt(8, 10))
    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    caminho = repo._caminho(motor.jornada.id)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    segunda_atividade = dict(dados["atividades"][0])
    segunda_atividade["id"] = "11111111-1111-1111-1111-111111111111"
    dados["atividades"].append(segunda_atividade)
    caminho.write_text(json.dumps(dados), encoding="utf-8")

    with pytest.raises(ArquivoCorrompidoError):
        repo.carregar_motor(motor.jornada.id)

    # A causa raiz continua acessivel para diagnostico.
    with pytest.raises(EstadoInconsistenteError):
        from workforce_core.engine import MotorJornada as MJ

        MJ.a_partir_de(repo.carregar(motor.jornada.id))


def test_listar_abertas_ignora_corrompidos_mas_nao_apaga(tmp_path):
    repo = RepositorioJornadaArquivo(tmp_path)

    motor_ok = MotorJornada("12345")
    motor_ok.iniciar_jornada(_dt(8, 0))
    repo.salvar(motor_ok.jornada)

    from uuid import uuid4

    corrompido_id = uuid4()
    caminho_corrompido = tmp_path / f"{corrompido_id}.json"
    caminho_corrompido.write_text("nao e json", encoding="utf-8")

    abertas = repo.listar_abertas()

    assert len(abertas) == 1
    assert abertas[0].id == motor_ok.jornada.id
    assert caminho_corrompido.exists()


def test_listar_ids_ignora_json_que_nao_e_uuid(tmp_path):
    # Regressao: um .json estranho ao repositorio (ex.: MANIFESTO.json na
    # raiz do projeto) nao pode derrubar a listagem inteira com ValueError.
    (tmp_path / "MANIFESTO.json").write_text("{}", encoding="utf-8")

    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    ids = repo.listar_ids()

    assert ids == [motor.jornada.id]


def test_excluir_remove_arquivo(tmp_path):
    motor = MotorJornada("12345")
    motor.iniciar_jornada(_dt(8, 0))
    repo = RepositorioJornadaArquivo(tmp_path)
    repo.salvar(motor.jornada)

    repo.excluir(motor.jornada.id)

    assert repo.listar_ids() == []
