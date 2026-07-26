"""Catalogo de motivos - piloto tecnico (catalogo dinamico).

Cadastro/edicao de motivos de pausa/deslocamento/apoio, consumidos pela
interface de campo via GET /catalogo (backend real). So funciona com o
backend (API) - nao existe "catalogo em arquivo local", o Postgres do
backend e a unica fonte de verdade daqui em diante. Ver
docs/46_ADR_0019_CATALOGO_DINAMICO.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st

from workforce_core.catalogo import Categoria, ClassificacaoHH


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    """Le st.secrets sem derrubar a pagina se nao houver secrets.toml
    configurado (uso local, sem Streamlit Cloud)."""
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


st.set_page_config(page_title="SGO Workforce | Catálogo (piloto)", layout="wide")

st.warning(
    "Piloto técnico. Editar um motivo aqui muda a classificação de "
    "jornadas já registradas que usam esse código - não há versionamento "
    "de catálogo neste incremento (ver docs/46_ADR_0019_CATALOGO_DINAMICO.md). "
    "Só motivos com tipo 'pausa' e ativos aparecem hoje no app de campo."
)

st.title("SGO Workforce | Catálogo de motivos (piloto)")

# Mesmas chaves de session_state da pagina principal (painel/app.py) -
# Streamlit compartilha st.session_state entre paginas da mesma sessao,
# entao quem ja configurou a API la nao precisa preencher de novo aqui.
if "painel_api_url" not in st.session_state:
    st.session_state.painel_api_url = _obter_secret_seguro("SYNC_API_URL")
if "painel_api_token" not in st.session_state:
    st.session_state.painel_api_token = _obter_secret_seguro("SYNC_TOKEN")

url_api = st.text_input(
    "URL do backend (ex.: https://sgo-workforce.onrender.com)",
    key="painel_api_url",
)
token_api = st.text_input(
    "Token de sincronização (SYNC_TOKEN)",
    key="painel_api_token",
    type="password",
)

if not url_api or not token_api:
    st.warning("Informe a URL do backend e o token de sincronização para continuar.")
    st.stop()

url_base = url_api.rstrip("/")
headers = {"X-Sync-Token": token_api}

try:
    resposta = requests.get(f"{url_base}/catalogo", headers=headers, timeout=60)
    resposta.raise_for_status()
    catalogo = resposta.json()
except requests.exceptions.RequestException as exc:
    st.error(f"Não foi possível buscar o catálogo do backend: {exc}")
    st.stop()

st.subheader(f"Motivos cadastrados ({len(catalogo)})")
st.dataframe(
    [
        {
            "Código": motivo["codigo"],
            "Descrição": motivo["descricao"],
            "Categoria": motivo["categoria"] or "(nenhuma)",
            "Classificação HH": motivo["classificacao_hh"],
            "Tipo de registro": motivo["tipo_registro"],
        }
        for motivo in catalogo
    ],
    width="stretch",
)

st.subheader("Criar ou editar motivo")
st.caption(
    "Informe um código já existente na tabela acima para editá-lo "
    "(sobrescreve os campos), ou um código novo para criar um motivo."
)

with st.form("form_motivo_catalogo"):
    codigo = st.text_input("Código (ex.: EE24)")
    descricao = st.text_input("Descrição")

    opcoes_categoria = ["(nenhuma)"] + [categoria.value for categoria in Categoria]
    categoria_selecionada = st.selectbox("Categoria", opcoes_categoria)

    classificacao_selecionada = st.selectbox(
        "Classificação HH", [classificacao.value for classificacao in ClassificacaoHH]
    )
    tipo_registro_selecionado = st.selectbox(
        "Tipo de registro",
        ["pausa", "evento_secundario", "atividade"],
        help=(
            "Só motivos 'pausa' ativos aparecem no seletor de pausa da "
            "interface de campo hoje - 'evento_secundario' e 'atividade' "
            "ainda não têm tela própria lá (ADR-0004)."
        ),
    )
    ativo_selecionado = st.checkbox("Ativo", value=True)

    enviado = st.form_submit_button("Salvar")

if enviado:
    if not codigo.strip() or not descricao.strip():
        st.error("Código e descrição são obrigatórios.")
    else:
        payload = {
            "codigo": codigo.strip(),
            "descricao": descricao.strip(),
            "categoria": None if categoria_selecionada == "(nenhuma)" else categoria_selecionada,
            "classificacao_hh": classificacao_selecionada,
            "tipo_registro": tipo_registro_selecionado,
            "ativo": ativo_selecionado,
        }
        try:
            resposta_post = requests.post(
                f"{url_base}/catalogo", json=payload, headers=headers, timeout=60
            )
            resposta_post.raise_for_status()
        except requests.exceptions.RequestException as exc:
            st.error(f"Não foi possível salvar o motivo: {exc}")
        else:
            st.success(f"Motivo '{payload['codigo']}' salvo.")
            st.rerun()
