"""Upload de fotos do atendimento de falha para o Supabase Storage (D3 do
roteiro combinado com o responsavel pelo produto, apos o ADR-0021).

Usa a API REST nativa do Supabase (nao o protocolo S3 - o responsavel pelo
produto forneceu chaves JWT, nao credenciais de Access Key/Secret),
autenticando com a `service_role` key. Essa chave fica exclusivamente
neste backend (variavel de ambiente no Render) - nunca chega na interface
de campo, que so fala com `POST /fotos`/`GET /fotos/url` do proprio
backend (mesmo token de sincronizacao dos demais endpoints).

Projeto Supabase: "Repositorio de Evidencias do SGO", bucket dedicado
`sgo-workforce-piloto` (privado) - decisao do responsavel pelo produto.
"""

from __future__ import annotations

import os
from uuid import uuid4

import requests

_BUCKET_PADRAO = "sgo-workforce-piloto"
_TIMEOUT_SEGUNDOS = 30


class SupabaseStorageNaoConfiguradoError(Exception):
    """SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY ausentes no ambiente do backend."""


class SupabaseStorageErro(Exception):
    """Supabase Storage recusou a operacao (upload ou geracao de URL assinada)."""


def _configuracao() -> tuple[str, str, str]:
    url = os.environ.get("SUPABASE_URL")
    chave = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not chave:
        raise SupabaseStorageNaoConfiguradoError(
            "Backend sem SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY configuradas - "
            "nao pode enviar fotos."
        )
    bucket = os.environ.get("SUPABASE_BUCKET", _BUCKET_PADRAO)
    return url.rstrip("/"), chave, bucket


def enviar_foto(conteudo: bytes, nome_arquivo: str, content_type: str) -> str:
    """Envia o conteudo ao bucket configurado e devolve o caminho
    permanente do objeto (nao uma URL assinada - essa expira e e gerada
    sob demanda por `gerar_url_assinada`)."""
    url, chave, bucket = _configuracao()
    caminho = f"{uuid4()}-{nome_arquivo}"
    resposta = requests.post(
        f"{url}/storage/v1/object/{bucket}/{caminho}",
        headers={
            "Authorization": f"Bearer {chave}",
            "Content-Type": content_type or "application/octet-stream",
        },
        data=conteudo,
        timeout=_TIMEOUT_SEGUNDOS,
    )
    if resposta.status_code >= 300:
        raise SupabaseStorageErro(
            f"Supabase Storage recusou o upload (HTTP {resposta.status_code}): {resposta.text}"
        )
    return caminho


def gerar_url_assinada(caminho: str, expira_em_segundos: int = 3600) -> str:
    """Gera uma URL assinada valida por `expira_em_segundos`, para exibir a
    foto sob demanda (painel, conferencia de RASF) sem tornar o bucket
    publico."""
    url, chave, bucket = _configuracao()
    resposta = requests.post(
        f"{url}/storage/v1/object/sign/{bucket}/{caminho}",
        headers={"Authorization": f"Bearer {chave}"},
        json={"expiresIn": expira_em_segundos},
        timeout=_TIMEOUT_SEGUNDOS,
    )
    if resposta.status_code >= 300:
        raise SupabaseStorageErro(
            f"Supabase Storage recusou gerar a URL assinada (HTTP {resposta.status_code}): "
            f"{resposta.text}"
        )
    caminho_assinado = resposta.json()["signedURL"]
    return f"{url}/storage/v1{caminho_assinado}"
