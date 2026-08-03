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

# Logo animado do produto, acima do menu de navegacao (ADR-0037):
# `st.logo` de volta no lugar de `st.sidebar.image` (ADR-0035/0036).
#
# `st.navigation` sempre ancora o menu da sidebar ("Analise de Dados" /
# "Dados" / "Configuracoes") no topo, ignorando a ordem do codigo -
# confirmado nesta sessao chamando `st.sidebar.video`/`st.sidebar.image`
# antes de `pagina.run()` e o resultado sempre aparecendo abaixo do menu
# mesmo assim. O unico slot que fica genuinamente ACIMA do menu e o do
# `st.logo`, pedido explicito do responsavel do produto ("acima do
# titulo Analise de Dados").
#
# GIF, nao WebP (bug real do Streamlit, nao do arquivo): lendo o codigo-
# fonte instalado (`streamlit/elements/lib/image_utils.py`), `st.image`/
# `st.logo` so preservam os quadros originais de uma imagem quando o
# formato de saida bate com o de entrada E nenhum resize e necessario -
# WebP nunca e reconhecido como formato de saida (so JPEG/PNG/GIF
# existem em `ImageFormat`), entao SEMPRE vira JPEG de 1 quadro so
# (`_pil_to_bytes` sem `save_all=True`). E por isso que o WebP do
# ADR-0036 apareceu estatico - nao foi erro na conversao, e uma
# limitacao do proprio Streamlit com esse formato. GIF e o unico formato
# que o pipeline preserva intacto (bytes originais, sem reabrir via PIL)
# quando o tamanho ja cabe dentro do layout - `st.logo` usa
# `LayoutConfig(width="content")` internamente (o = 1460px), bem acima
# dos 720px deste arquivo, entao nao aciona nenhum redimensionamento.
# Tentei reduzir a resolucao pra 320px pra economizar banda, mas o
# tamanho do arquivo nao caiu quase nada (esse tipo de gradiente
# continuo comprime mal em GIF em qualquer resolucao) - por isso o
# arquivo aqui e o GIF original sem reprocessar, mantendo a qualidade
# exatamente como fornecido.
#
# Tamanho/centralizacao: `st.logo` limita a altura renderizada a no
# maximo 32px mesmo com `size="large"` (documentado no proprio
# docstring do Streamlit) - CSS em `painel/estilo.py`
# (`[data-testid="stSidebarLogo"]` - NAO `stLogo`, testid diferente
# usado especificamente pro logo dentro da sidebar, ver ADR-0039)
# sobrescreve isso pra dar presenca visual de verdade, e centraliza
# dentro do slot.
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
