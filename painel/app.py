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

# Logo animado do produto na sidebar (ADR-0033/0034/0035/0036): substitui
# o logo estatico da MRS a pedido do responsavel do produto.
#
# WebP (nao GIF nem mp4) - anima nativamente numa tag <img> comum, sem a
# barra de controles nativa do navegador que o `st.video` sempre mostra
# (motivo da troca de mp4 pra GIF no ADR-0034). O GIF original (17.4MB,
# 720x720) foi reconvertido pra WebP em 360x360/qualidade 85 (ADR-0036):
# mais que o suficiente pra nitidez nos 260px de largura exibidos aqui
# (inclusive em tela retina), 3.2x mais leve (5.4MB) sem perda
# perceptivel - a resolucao de origem so desperdicava banda.
#
# `st.sidebar.image` em vez de `st.logo` (ADR-0035): `st.logo` reserva
# um slot fixo pequeno no topo, ao lado do botao de recolher a sidebar
# - `size="large"` nao aumenta o suficiente e a posicao nao e
# centralizavel (relatado com captura de tela real: logo minusculo,
# encostado no canto). `st.sidebar.image` e um elemento comum do corpo
# da sidebar (renderiza abaixo do menu de navegacao, que o Streamlit
# sempre ancora no topo) - controla largura de verdade, e a centralizacao
# vem do CSS em `painel/estilo.py` (`[data-testid="stImage"]`).
_CAMINHO_LOGO_WORKFORCE = _CAMINHO_ASSETS / "logo_sgo_workforce.webp"
if _CAMINHO_LOGO_WORKFORCE.exists():
    st.sidebar.image(str(_CAMINHO_LOGO_WORKFORCE), width=260)

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
