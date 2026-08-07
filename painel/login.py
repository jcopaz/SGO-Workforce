"""Login do painel contra o SGO (Gestão_OS) - ADR-0062.

`validar_login_sgo` e' pura (sem Streamlit, `sessao_requests` injetavel
para teste - mesmo padrao de painel/dados.py) e reaproveita o mesmo
contrato de POST /auth/validar ja usado por
interface_campo/js/integracaoSgo.js::validarLoginSgo: nunca lanca,
sempre devolve {"ok": bool, ...}.

`exigir_login` e' a parte Streamlit (gate de tela, session_state) -
chamada uma unica vez em painel/app.py, antes de `st.navigation(...)`.
`st.session_state` sobrevive a reruns normais (clique em botao, trocar
filtro) dentro da mesma sessao de navegador, mas NAO sobrevive a um
F5/nova aba (sem token persistido - fora do escopo desta rodada, ver
ADR-0062).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests
import streamlit as st


def validar_login_sgo(
    username: str,
    senha: str,
    url_api_sgo: str,
    chave_api_sgo: str,
    *,
    sessao_requests=requests,
) -> Dict[str, object]:
    if not url_api_sgo or not chave_api_sgo:
        return {"ok": False, "mensagem": "Integração com o SGO não configurada."}

    try:
        resposta = sessao_requests.post(
            f"{url_api_sgo.rstrip('/')}/auth/validar",
            headers={"x-api-key": chave_api_sgo},
            data={"username": username, "senha": senha},
            timeout=30,
        )
    except requests.exceptions.RequestException:
        return {"ok": False, "mensagem": "Sem conexão com o SGO agora."}

    if resposta.status_code == 401:
        return {"ok": False, "mensagem": "Matrícula ou senha do SGO incorretas."}
    if resposta.status_code == 403:
        # Cobre tanto "chave de integracao invalida/nao configurada no lado
        # do SGO" quanto "senha pendente de troca" (ver api.py) - a mensagem
        # do proprio backend ja distingue os dois casos.
        detalhe = "Acesso ao SGO negado."
        try:
            corpo = resposta.json()
            if corpo.get("detail"):
                detalhe = corpo["detail"]
        except ValueError:
            pass
        return {"ok": False, "mensagem": detalhe}
    if not resposta.ok:
        return {"ok": False, "mensagem": f"SGO recusou a validação (HTTP {resposta.status_code})."}

    dados = resposta.json()
    return {
        "ok": True,
        "username": dados.get("username"),
        "nome": dados.get("nome"),
        "perfil": dados.get("perfil"),
        "escopo": dados.get("escopo"),
        "governanca": dados.get("governanca") or [],
    }


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    """Le st.secrets sem derrubar o painel se nao houver secrets.toml
    configurado (uso local, sem Streamlit Cloud) - mesmo padrao ja usado em
    painel/telas/dashboard.py e painel/telas/mapa_operacional.py."""
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


# Prefixo dedicado (nao "painel_") de proposito: painel/telas/*.py ja usa
# "painel_" para dezenas de chaves de widget (filtros, selectbox - ex.
# painel_mapa_colaborador_selecionado) - reaproveitar o mesmo prefixo aqui
# faria um "limpar tudo que comeca com painel_" no logout (mostrar_usuario_logado)
# arrastar chaves de filtro sem relacao nenhuma com login.
_CHAVES_SESSAO_LOGIN = [
    "auth_sgo_logado",
    "auth_sgo_usuario",
    "auth_sgo_nome",
    "auth_sgo_perfil",
    "auth_sgo_escopo",
    "auth_sgo_governanca",
]


def exigir_login() -> None:
    """Bloqueia o painel ate' o login contra o SGO ser validado. Chamar uma
    unica vez em painel/app.py, logo apos aplicar_estilo_sgo() e antes de
    montar a navegacao - nada do resto do painel deve rodar sem login."""
    if st.session_state.get("auth_sgo_logado"):
        return

    st.title("SGO Workforce | Login")

    url_api_sgo = _obter_secret_seguro("SGO_API_URL")
    chave_api_sgo = _obter_secret_seguro("SGO_WORKFORCE_API_KEY")
    if not url_api_sgo or not chave_api_sgo:
        st.error(
            "Integração com o SGO não configurada. Defina os secrets "
            "`SGO_API_URL` e `SGO_WORKFORCE_API_KEY` (Streamlit Cloud: "
            "Settings → Secrets) para liberar o login."
        )
        st.stop()

    with st.form("form_login_painel"):
        usuario = st.text_input("Matrícula / Usuário do SGO")
        senha = st.text_input("Senha do SGO", type="password")
        enviar = st.form_submit_button("Entrar", use_container_width=True)

    if enviar:
        if not usuario.strip() or not senha:
            st.error("Informe matrícula e senha.")
        else:
            resultado = validar_login_sgo(usuario.strip(), senha, url_api_sgo, chave_api_sgo)
            if resultado["ok"]:
                st.session_state.update(
                    {
                        "auth_sgo_logado": True,
                        "auth_sgo_usuario": resultado["username"],
                        "auth_sgo_nome": resultado["nome"],
                        "auth_sgo_perfil": resultado["perfil"],
                        "auth_sgo_escopo": resultado["escopo"],
                        "auth_sgo_governanca": resultado["governanca"],
                    }
                )
                st.rerun()
            else:
                st.error(resultado["mensagem"])

    st.stop()


def mostrar_usuario_logado() -> None:
    """Identificação de quem está logado + botão de sair, na sidebar.
    Chamar em painel/app.py depois de exigir_login() (que já garantiu que
    st.session_state tem os campos usados aqui)."""
    nome = st.session_state.get("auth_sgo_nome") or st.session_state.get("auth_sgo_usuario")
    perfil = st.session_state.get("auth_sgo_perfil")
    st.sidebar.caption(f"Logado como {nome} ({perfil})" if perfil else f"Logado como {nome}")
    if st.sidebar.button("Sair", width="stretch"):
        # So as chaves de login (_CHAVES_SESSAO_LOGIN) - nunca um prefixo
        # largo tipo "painel_", que colidiria com filtros/selectbox de
        # outras telas (ver comentario em _CHAVES_SESSAO_LOGIN acima).
        for chave in _CHAVES_SESSAO_LOGIN:
            st.session_state.pop(chave, None)
        st.rerun()
