"""Testes de painel/login.py::validar_login_sgo (ADR-0062).

Pura (sem Streamlit) - `sessao_requests` injetavel, mesmo padrao de
`interface_campo/js/integracaoSgo.test.mjs` do lado JS: nunca lanca,
sempre {"ok": bool, ...}. Nenhuma chamada de rede real.
"""

from __future__ import annotations

import requests

from login import validar_login_sgo


class _RespostaFalsa:
    def __init__(self, status_code: int, corpo=None, lanca_json=False):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._corpo = corpo
        self._lanca_json = lanca_json

    def json(self):
        if self._lanca_json:
            raise ValueError("corpo vazio")
        return self._corpo


class _SessaoFalsa:
    def __init__(self, resposta=None, excecao=None, capturar_em=None):
        self._resposta = resposta
        self._excecao = excecao
        self._capturar_em = capturar_em if capturar_em is not None else {}

    def post(self, url, headers=None, data=None, timeout=None):
        self._capturar_em["url"] = url
        self._capturar_em["headers"] = headers
        self._capturar_em["data"] = data
        if self._excecao:
            raise self._excecao
        return self._resposta


def test_validar_login_sgo_sem_configuracao_nao_tenta_chamar_rede():
    chamadas = {}
    sessao = _SessaoFalsa(capturar_em=chamadas)

    resultado = validar_login_sgo("12345", "senha", "", "", sessao_requests=sessao)

    assert resultado["ok"] is False
    assert "não configurada" in resultado["mensagem"]
    assert chamadas == {}


def test_validar_login_sgo_sem_conexao_nunca_lanca():
    sessao = _SessaoFalsa(excecao=requests.exceptions.ConnectionError("offline"))

    resultado = validar_login_sgo(
        "12345", "senha", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is False
    assert "Sem conexão" in resultado["mensagem"]


def test_validar_login_sgo_401_reporta_credenciais_incorretas():
    sessao = _SessaoFalsa(resposta=_RespostaFalsa(401))

    resultado = validar_login_sgo(
        "12345", "senha-errada", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is False
    assert "incorretas" in resultado["mensagem"]


def test_validar_login_sgo_403_repassa_detail_do_backend():
    sessao = _SessaoFalsa(
        resposta=_RespostaFalsa(403, corpo={"detail": "Senha pendente de troca."})
    )

    resultado = validar_login_sgo(
        "12345", "senha", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is False
    assert resultado["mensagem"] == "Senha pendente de troca."


def test_validar_login_sgo_403_sem_corpo_json_usa_mensagem_generica():
    sessao = _SessaoFalsa(resposta=_RespostaFalsa(403, lanca_json=True))

    resultado = validar_login_sgo(
        "12345", "senha", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is False
    assert "negado" in resultado["mensagem"]


def test_validar_login_sgo_erro_generico_reporta_status():
    sessao = _SessaoFalsa(resposta=_RespostaFalsa(500))

    resultado = validar_login_sgo(
        "12345", "senha", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is False
    assert "500" in resultado["mensagem"]


def test_validar_login_sgo_sucesso_envia_credenciais_e_devolve_perfil():
    chamadas = {}
    corpo = {
        "username": "12345",
        "nome": "Colaborador Teste",
        "perfil": "Técnico",
        "escopo": "Paranapiacaba",
        "governanca": ["Mapa de Campo"],
        "sid": "token-de-teste",
    }
    sessao = _SessaoFalsa(resposta=_RespostaFalsa(200, corpo=corpo), capturar_em=chamadas)

    resultado = validar_login_sgo(
        "12345", "minhasenha", "https://sgo-de-teste.invalido", "chave-teste", sessao_requests=sessao
    )

    assert resultado["ok"] is True
    assert resultado["username"] == "12345"
    assert resultado["nome"] == "Colaborador Teste"
    assert resultado["perfil"] == "Técnico"
    assert resultado["governanca"] == ["Mapa de Campo"]

    assert chamadas["url"] == "https://sgo-de-teste.invalido/auth/validar"
    assert chamadas["headers"]["x-api-key"] == "chave-teste"
    assert chamadas["data"] == {"username": "12345", "senha": "minhasenha"}
