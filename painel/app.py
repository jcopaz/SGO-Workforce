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

if (Path(__file__).resolve().parent / "assets" / "logo_mrs.png").exists():
    st.logo(str(Path(__file__).resolve().parent / "assets" / "logo_mrs.png"))

pagina = st.navigation(
    {
        "Análise de Dados": [
            st.Page("telas/dashboard.py", title="Visão geral", icon="📊", default=True),
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
