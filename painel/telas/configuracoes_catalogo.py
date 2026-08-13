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


st.warning(
    "Piloto técnico. Editar um motivo aqui muda a classificação de "
    "jornadas já registradas que usam esse código - não há versionamento "
    "de catálogo neste incremento (ver docs/46_ADR_0019_CATALOGO_DINAMICO.md). "
    "Só motivos com tipo 'pausa' e ativos aparecem hoje no app de campo."
)

st.title("SGO Workforce | Catálogo de motivos (piloto)")

# Fonte de dados fixa em API (nuvem, ADR-0041) - mesmo padrao das demais
# telas: credenciais vem so de st.secrets, nunca digitadas/visiveis na
# tela. Esta pagina antes mostrava URL e token do backend em campos de
# texto editaveis - contradizia a decisao de seguranca ja tomada nas
# outras telas; corrigido junto da lapidacao geral do painel, 2026-08-12.
url_api = _obter_secret_seguro("SYNC_API_URL")
token_api = _obter_secret_seguro("SYNC_TOKEN")

if not url_api or not token_api:
    st.error(
        "Backend não configurado. Defina os secrets `SYNC_API_URL` e "
        "`SYNC_TOKEN` (Streamlit Cloud: Settings → Secrets) para o "
        "painel funcionar."
    )
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

st.divider()
st.subheader("Manutenção de dados")
with st.expander("Expurgo de pulsos GPS antigos", expanded=False):
    st.warning(
        "Ação permanente e irreversível - apaga pulsos GPS do backend, não "
        "só do painel. Retenção decidida em 2026-07-31 (ADR-0043): 90 dias "
        "por padrão. Nunca apaga jornadas, atividades ou atendimentos de "
        "falha - só o traço de GPS bruto (`docs/08_GPS_PULSOS_E_PRIVACIDADE.md`)."
    )
    dias_retencao = st.number_input(
        "Apagar pulsos com mais de quantos dias?",
        min_value=1,
        value=90,
        step=1,
        key="painel_expurgo_dias",
    )

    # dry_run (ADR-0057, licao trazida do app irmao Gestao_OS): a API
    # recusa apagar de verdade sem `dry_run=false` explicito - o botao de
    # pre-visualizar chama sem esse parametro (fica no padrao seguro),
    # nunca apaga nada, so mostra quantos pulsos seriam afetados.
    if st.button("🔍 Pré-visualizar (não apaga nada)", key="painel_expurgo_preview_botao"):
        try:
            resposta_preview = requests.post(
                f"{url_base}/pulsos/expurgar",
                params={"dias": int(dias_retencao)},
                headers=headers,
                timeout=60,
            )
            resposta_preview.raise_for_status()
        except requests.exceptions.RequestException as exc:
            st.error(f"Não foi possível consultar a pré-visualização: {exc}")
        else:
            quantidade_prevista = resposta_preview.json().get("seriam_apagados", 0)
            st.info(f"{quantidade_prevista} pulso(s) seriam apagados com esse número de dias.")

    confirmar_expurgo = st.checkbox(
        f"Confirmo que quero apagar permanentemente pulsos com mais de {int(dias_retencao)} dias.",
        key="painel_expurgo_confirmado",
    )
    if st.button(
        "🗑️ Expurgar pulsos antigos", disabled=not confirmar_expurgo, key="painel_expurgo_botao"
    ):
        try:
            resposta_expurgo = requests.post(
                f"{url_base}/pulsos/expurgar",
                params={"dias": int(dias_retencao), "dry_run": False},
                headers=headers,
                timeout=60,
            )
            resposta_expurgo.raise_for_status()
        except requests.exceptions.RequestException as exc:
            st.error(f"Não foi possível expurgar os pulsos: {exc}")
        else:
            quantidade_apagada = resposta_expurgo.json().get("apagados", 0)
            st.success(f"{quantidade_apagada} pulso(s) apagado(s) permanentemente.")
