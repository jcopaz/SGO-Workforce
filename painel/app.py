"""Painel gerencial - piloto tecnico. Launcher (ADR-0020).

So define a navegacao (st.navigation/st.Page, com secoes) e aplica a
identidade visual (painel/estilo.py) - o conteudo de cada tela vive em
painel/telas/. Reorganizado a pedido do responsavel pelo produto:
"Analise de Dados" agrupa as telas so-leitura (dashboard, mapa, PCM);
"Dados" e "insercao ou exportacao de dados"; "Configuracoes" e
"informacao geral aplicada a todos os usuarios" (catalogo de motivos).

Rodar com: streamlit run painel/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from estilo import aplicar_estilo_sgo

st.set_page_config(
    page_title="SGO Workforce | Painel (piloto)",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo_sgo()

_CAMINHO_ASSETS = Path(__file__).resolve().parent / "assets"

# Logo animado do produto no slot fixo do Streamlit (ADR-0033/0034):
# substitui o logo estatico da MRS a pedido do responsavel do produto.
# GIF (nao mp4) - anima nativamente dentro de uma tag <img> comum, sem a
# barra de controles nativa do navegador (play/mudo/volume) que o
# `st.video` sempre mostra e que o responsavel do produto considerou
# pouco premium. `size="large"` da mais presenca visual ao logo -
# comportamento correto do `st.logo` nao foi confirmado num navegador
# real neste ambiente (sandbox sem Playwright/Chromium, mesma limitacao
# de sempre) - conferir visualmente apos o proximo deploy.
_CAMINHO_LOGO_WORKFORCE = _CAMINHO_ASSETS / "logo_sgo_workforce.gif"
if _CAMINHO_LOGO_WORKFORCE.exists():
    st.logo(str(_CAMINHO_LOGO_WORKFORCE), size="large")

pagina = st.navigation(
    {
        "Análise de Dados": [
            st.Page("telas/dashboard.py", title="Visão geral", icon="📊", default=True),
            st.Page("telas/falhas.py", title="Falhas", icon="🛠️"),
            st.Page("telas/mapa_operacional.py", title="Mapa Operacional", icon="🗺️"),
            st.Page("telas/capacidade_pcm.py", title="Capacidade PCM", icon="🏭"),
        ],
        "Dados": [
            st.Page("telas/dados_exportacoes.py", title="Exportações", icon="📤"),
        ],
        "Configurações": [
            st.Page("telas/configuracoes_catalogo.py", title="Catálogo de motivos", icon="⚙️"),
        ],
    }
)
pagina.run()
