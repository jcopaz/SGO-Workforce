"""Testes do Incremento 3: fila offline e sincronizacao idempotente.

Cobre as regras da secao 3.4 do alinhamento oficial e a validacao minima
"teste de idempotencia de sincronizacao" do CLAUDE.md.
"""

from datetime import datetime

import pytest

from workforce_core import MotorJornada
from workforce_storage import RepositorioJornadaArquivo
from workforce_sync import (
    ClienteSincronizacaoEmMemoria,
    FilaSincronizacao,
    RepositorioFilaArquivo,
    Sincronizador,
    StatusSincronizacao,
)
from workforce_sync.exceptions import RegistroCorrompidoError


def _dt(hora, minuto, dia=1):
    return datetime(2026, 1, dia, hora, minuto)


def _nova_jornada(matricula="12345"):
    motor = MotorJornada(matricula)
    motor.iniciar_jornada(_dt(8, 0))
    return motor


@pytest.fixture
def ambiente(tmp_path):
    repo_jornada = RepositorioJornadaArquivo(tmp_path / "jornadas")
    repo_fila = RepositorioFilaArquivo(tmp_path / "fila")
    fila = FilaSincronizacao(repo_fila)
    cliente = ClienteSincronizacaoEmMemoria()
    sincronizador = Sincronizador(fila, repo_jornada, cliente)
    return repo_jornada, fila, cliente, sincronizador


def test_enfileirar_marca_como_pendente(ambiente):
    repo_jornada, fila, _cliente, _sync = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)

    registro = fila.enfileirar(motor.jornada.id)

    assert registro.status == StatusSincronizacao.PENDENTE
    assert fila.resumo()[StatusSincronizacao.PENDENTE] == 1


def test_sincronizacao_bem_sucedida_marca_sincronizado(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila.enfileirar(motor.jornada.id)

    relatorio = sincronizador.sincronizar_pendentes()

    assert relatorio.sincronizados == [motor.jornada.id]
    assert fila.resumo()[StatusSincronizacao.SINCRONIZADO] == 1
    assert len(cliente.armazenado) == 1


def test_sincronizar_pendentes_e_idempotente_quando_nada_mudou(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila.enfileirar(motor.jornada.id)

    sincronizador.sincronizar_pendentes()
    assert len(cliente.chamadas) == 1

    # Nada novo para enviar: a segunda chamada nao deve gerar nenhuma nova
    # tentativa de rede, porque o registro ja esta SINCRONIZADO.
    relatorio2 = sincronizador.sincronizar_pendentes()

    assert relatorio2.processados == []
    assert len(cliente.chamadas) == 1
    assert len(cliente.armazenado) == 1


def test_reenvio_apos_confirmacao_perdida_nao_duplica(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila.enfileirar(motor.jornada.id)
    sincronizador.sincronizar_pendentes()

    # Simula o cliente nao tendo recebido a confirmacao do servidor e
    # tentando reenviar o mesmo registro.
    fila.enfileirar(motor.jornada.id)
    sincronizador.sincronizar_pendentes()

    assert len(cliente.chamadas) == 2
    assert len(cliente.armazenado) == 1  # upsert, nunca duplicidade
    assert fila.resumo()[StatusSincronizacao.SINCRONIZADO] == 1


def test_erro_de_rede_marca_erro_e_e_retentado_automaticamente(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila.enfileirar(motor.jornada.id)

    cliente.forcar_erro(motor.jornada.id)
    relatorio1 = sincronizador.sincronizar_pendentes()

    assert relatorio1.com_erro == [motor.jornada.id]
    registro = fila.listar(StatusSincronizacao.ERRO)[0]
    assert registro.tentativas == 1
    assert registro.ultimo_erro

    # ERRO entra automaticamente no proximo lote (ao contrario de CONFLITO).
    relatorio2 = sincronizador.sincronizar_pendentes()

    assert relatorio2.sincronizados == [motor.jornada.id]
    assert fila.resumo()[StatusSincronizacao.SINCRONIZADO] == 1


def test_conflito_nao_e_resolvido_silenciosamente(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente
    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila.enfileirar(motor.jornada.id)

    cliente.forcar_conflito(motor.jornada.id)
    relatorio1 = sincronizador.sincronizar_pendentes()

    assert relatorio1.em_conflito == [motor.jornada.id]
    assert fila.resumo()[StatusSincronizacao.CONFLITO] == 1

    # Um conflito nao pode ser retentado automaticamente: uma segunda
    # chamada de sincronizacao nao deve nem tocar nesse registro.
    chamadas_antes = len(cliente.chamadas)
    relatorio2 = sincronizador.sincronizar_pendentes()

    assert relatorio2.processados == []
    assert len(cliente.chamadas) == chamadas_antes
    assert fila.resumo()[StatusSincronizacao.CONFLITO] == 1

    # So volta a ser tentado apos reenfileiramento explicito.
    fila.enfileirar(motor.jornada.id)
    relatorio3 = sincronizador.sincronizar_pendentes()
    assert relatorio3.sincronizados == [motor.jornada.id]


def test_fila_mostra_os_quatro_status_simultaneamente(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente

    sincronizado = _nova_jornada("2")
    com_erro = _nova_jornada("3")
    em_conflito = _nova_jornada("4")

    for motor in (sincronizado, com_erro, em_conflito):
        repo_jornada.salvar(motor.jornada)
        fila.enfileirar(motor.jornada.id)

    cliente.forcar_erro(com_erro.jornada.id)
    cliente.forcar_conflito(em_conflito.jornada.id)

    # 1a chamada: sincronizado -> SINCRONIZADO, com_erro -> ERRO (falha
    # simulada de rede), em_conflito -> CONFLITO.
    sincronizador.sincronizar_pendentes()
    # 2a chamada: ERRO entra automaticamente no lote e agora sucede (a
    # falha simulada ja foi consumida); CONFLITO fica de fora.
    sincronizador.sincronizar_pendentes()

    # "pendente" e criada e enfileirada por ultimo, depois de todo
    # processamento acima, para permanecer PENDENTE de forma deterministica.
    pendente = _nova_jornada("1")
    repo_jornada.salvar(pendente.jornada)
    fila.enfileirar(pendente.jornada.id)

    resumo = fila.resumo()
    assert resumo[StatusSincronizacao.PENDENTE] == 1
    assert resumo[StatusSincronizacao.SINCRONIZADO] == 2
    assert resumo[StatusSincronizacao.ERRO] == 0
    assert resumo[StatusSincronizacao.CONFLITO] == 1
    assert sum(resumo.values()) == 4


def test_tamanho_de_lote_limita_processamento_por_chamada(ambiente):
    repo_jornada, fila, cliente, sincronizador = ambiente

    for i in range(5):
        motor = _nova_jornada(str(i))
        repo_jornada.salvar(motor.jornada)
        fila.enfileirar(motor.jornada.id)

    relatorio = sincronizador.sincronizar_pendentes(tamanho_lote=2)

    assert len(relatorio.processados) == 2
    assert fila.resumo()[StatusSincronizacao.PENDENTE] == 3
    assert fila.resumo()[StatusSincronizacao.SINCRONIZADO] == 2


def test_fila_persiste_entre_reinicializacoes(tmp_path):
    repo_jornada = RepositorioJornadaArquivo(tmp_path / "jornadas")
    repo_fila = RepositorioFilaArquivo(tmp_path / "fila")
    fila1 = FilaSincronizacao(repo_fila)

    motor = _nova_jornada()
    repo_jornada.salvar(motor.jornada)
    fila1.enfileirar(motor.jornada.id)

    # "Reinicia o app": nova instancia de fila sobre o mesmo diretorio.
    fila2 = FilaSincronizacao(RepositorioFilaArquivo(tmp_path / "fila"))

    assert fila2.resumo()[StatusSincronizacao.PENDENTE] == 1


def test_registro_de_fila_corrompido_nao_e_apagado(tmp_path):
    repo_fila = RepositorioFilaArquivo(tmp_path / "fila")
    fila = FilaSincronizacao(repo_fila)

    motor = _nova_jornada()
    fila.enfileirar(motor.jornada.id)

    caminho = repo_fila._caminho(motor.jornada.id)
    caminho.write_text("nao e json valido", encoding="utf-8")

    with pytest.raises(RegistroCorrompidoError):
        repo_fila.carregar(motor.jornada.id)

    assert caminho.exists()
    # listar_todos ignora o corrompido sem quebrar nem apagar nada.
    assert fila.listar() == []
    assert caminho.exists()
