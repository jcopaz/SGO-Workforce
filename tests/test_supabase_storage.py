"""Testes de src/workforce_api/supabase_storage.py (D3, upload de fotos).

Sem chamada de rede real ao Supabase neste ambiente - requests.post e
substituido por um fake via monkeypatch, mesmo espirito das demais
integracoes externas do projeto (Render/Postgres, ver docs/44_ADR_0017).
"""

from __future__ import annotations

import pytest

from workforce_api import supabase_storage


class _RespostaFalsa:
    def __init__(self, status_code, corpo=None, texto=""):
        self.status_code = status_code
        self._corpo = corpo or {}
        self.text = texto

    def json(self):
        return self._corpo


def test_enviar_foto_sem_configuracao_levanta_erro_dedicado(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(supabase_storage.SupabaseStorageNaoConfiguradoError):
        supabase_storage.enviar_foto(b"conteudo", "foto.jpg", "image/jpeg")


def test_enviar_foto_sucesso_devolve_caminho_com_nome_original(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
    monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

    chamadas = []

    def post_falso(url, headers=None, data=None, timeout=None):
        chamadas.append({"url": url, "headers": headers})
        return _RespostaFalsa(200)

    monkeypatch.setattr(supabase_storage.requests, "post", post_falso)

    caminho = supabase_storage.enviar_foto(b"conteudo", "foto.jpg", "image/jpeg")

    assert caminho.endswith("-foto.jpg")
    assert chamadas[0]["url"].startswith(
        "https://exemplo.supabase.co/storage/v1/object/sgo-workforce-piloto/"
    )
    assert chamadas[0]["headers"]["Authorization"] == "Bearer chave-de-teste"


def test_enviar_foto_usa_bucket_customizado(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
    monkeypatch.setenv("SUPABASE_BUCKET", "outro-bucket")

    chamadas = []
    monkeypatch.setattr(
        supabase_storage.requests,
        "post",
        lambda url, **kwargs: chamadas.append(url) or _RespostaFalsa(200),
    )

    supabase_storage.enviar_foto(b"x", "a.png", "image/png")
    assert "/object/outro-bucket/" in chamadas[0]


def test_enviar_foto_erro_http_levanta_supabase_storage_erro(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
    monkeypatch.setattr(
        supabase_storage.requests, "post", lambda *a, **k: _RespostaFalsa(403, texto="forbidden")
    )

    with pytest.raises(supabase_storage.SupabaseStorageErro):
        supabase_storage.enviar_foto(b"x", "a.png", "image/png")


def test_gerar_url_assinada_sem_configuracao_levanta_erro_dedicado(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(supabase_storage.SupabaseStorageNaoConfiguradoError):
        supabase_storage.gerar_url_assinada("qualquer-caminho.jpg")


def test_gerar_url_assinada_sucesso(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
    monkeypatch.setattr(
        supabase_storage.requests,
        "post",
        lambda *a, **k: _RespostaFalsa(
            200, corpo={"signedURL": "/object/sign/bucket/caminho?token=abc"}
        ),
    )

    url = supabase_storage.gerar_url_assinada("caminho.jpg")
    assert url == "https://exemplo.supabase.co/storage/v1/object/sign/bucket/caminho?token=abc"


def test_gerar_url_assinada_erro_http_levanta_supabase_storage_erro(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "chave-de-teste")
    monkeypatch.setattr(
        supabase_storage.requests, "post", lambda *a, **k: _RespostaFalsa(404, texto="not found")
    )

    with pytest.raises(supabase_storage.SupabaseStorageErro):
        supabase_storage.gerar_url_assinada("inexistente.jpg")
