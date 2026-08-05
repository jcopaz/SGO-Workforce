"""Teste de ponta a ponta da tela "Catálogo de motivos" do painel, via
`streamlit.testing.v1.AppTest` (mesmo padrao de test_falhas_painel.py e
test_mapa_operacional_painel.py).

Cobre so a secao nova do ADR-0054 (expurgo de pulsos GPS antigos) - o
cadastro/edicao de motivo (ADR-0019) ja existia sem teste de ponta a
ponta antes desta sessao e continua fora de escopo aqui.
"""

from __future__ import annotations

from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

_CAMINHO_CONFIGURACOES = str(
    Path(__file__).resolve().parent.parent / "painel" / "telas" / "configuracoes_catalogo.py"
)


class _RespostaFalsa:
    def __init__(self, dados, status_code=200):
        self._dados = dados
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._dados


def _preparar_secrets_de_teste(at: AppTest) -> None:
    at.secrets["SYNC_API_URL"] = "https://backend-de-teste.invalido"
    at.secrets["SYNC_TOKEN"] = "token-de-teste"


def test_configuracoes_mostra_secao_de_expurgo_com_botao_desabilitado(monkeypatch):
    # Botao comeca desabilitado - so libera depois de marcar a
    # confirmacao explicita (acao permanente/irreversivel).
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _RespostaFalsa([]))

    at = AppTest.from_file(_CAMINHO_CONFIGURACOES)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert not at.exception
    assert any("Expurgo de pulsos GPS antigos" in exp.label for exp in at.expander)
    botao = next(b for b in at.button if "Expurgar pulsos antigos" in b.label)
    assert botao.disabled


def test_configuracoes_expurgo_sem_confirmar_nao_chama_endpoint(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _RespostaFalsa([]))
    chamadas = []
    monkeypatch.setattr(
        requests, "post", lambda *args, **kwargs: chamadas.append((args, kwargs))
    )

    at = AppTest.from_file(_CAMINHO_CONFIGURACOES)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    assert chamadas == []


def test_configuracoes_expurgo_confirmado_chama_endpoint_com_dias_padrao(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _RespostaFalsa([]))

    chamadas = []

    def _post_falso(url, **kwargs):
        chamadas.append((url, kwargs.get("params")))
        return _RespostaFalsa({"apagados": 7})

    monkeypatch.setattr(requests, "post", _post_falso)

    at = AppTest.from_file(_CAMINHO_CONFIGURACOES)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    at.checkbox(key="painel_expurgo_confirmado").check().run(timeout=30)
    botao = next(b for b in at.button if "Expurgar pulsos antigos" in b.label)
    assert not botao.disabled

    botao.click().run(timeout=30)

    assert not at.exception
    assert len(chamadas) == 1
    url_chamada, params_chamados = chamadas[0]
    assert url_chamada.endswith("/pulsos/expurgar")
    # dry_run=False explicito (ADR-0057) - sem isso a API recusaria apagar
    # de verdade, ficando so no modo seguro de contagem.
    assert params_chamados == {"dias": 90, "dry_run": False}
    textos = " ".join(s.value for s in at.success)
    assert "7 pulso(s) apagado(s)" in textos


def test_configuracoes_expurgo_preview_nao_apaga_so_mostra_contagem(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _RespostaFalsa([]))

    chamadas = []

    def _post_falso(url, **kwargs):
        chamadas.append((url, kwargs.get("params")))
        return _RespostaFalsa({"dry_run": True, "seriam_apagados": 12})

    monkeypatch.setattr(requests, "post", _post_falso)

    at = AppTest.from_file(_CAMINHO_CONFIGURACOES)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)

    botao_preview = next(b for b in at.button if "Pré-visualizar" in b.label)
    botao_preview.click().run(timeout=30)

    assert not at.exception
    assert len(chamadas) == 1
    url_chamada, params_chamados = chamadas[0]
    assert url_chamada.endswith("/pulsos/expurgar")
    assert params_chamados == {"dias": 90}  # sem dry_run - fica no padrao seguro da API
    textos = " ".join(i.value for i in at.info)
    assert "12 pulso(s) seriam apagados" in textos


def test_configuracoes_expurgo_erro_de_rede_mostra_st_error_sem_quebrar(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _RespostaFalsa([]))

    def _post_com_erro(*args, **kwargs):
        raise requests.exceptions.ConnectionError("backend fora do ar")

    monkeypatch.setattr(requests, "post", _post_com_erro)

    at = AppTest.from_file(_CAMINHO_CONFIGURACOES)
    _preparar_secrets_de_teste(at)
    at.run(timeout=30)
    at.checkbox(key="painel_expurgo_confirmado").check().run(timeout=30)

    botao = next(b for b in at.button if "Expurgar pulsos antigos" in b.label)
    botao.click().run(timeout=30)

    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "Não foi possível expurgar os pulsos" in textos
