"""Identidade visual do painel, copiada do SGO (Gestão_OS) a pedido do
responsável pelo produto, para facilitar integração/migração futura.

Reaproveita literalmente a paleta e os blocos de CSS já usados em
producao pelo Gestão_OS (levantados por leitura de codigo, nenhum
arquivo/modulo do Gestão_OS e importado aqui - so a paleta de cores e o
logo, que e um ativo visual compartilhado da mesma empresa). O Gestão_OS
usa um `st.radio` customizado para o menu lateral; o Workforce usa
`st.navigation`/`st.Page` (API nativa, nao existia quando o Gestão_OS foi
escrito) - os seletores CSS do menu de navegacao sao adaptados, nao uma
copia literal, e precisam de conferencia visual manual (sem navegador
disponivel neste ambiente de desenvolvimento).

Ver docs/47_ADR_0020_REORGANIZACAO_PAINEL_E_IDENTIDADE_VISUAL.md.
"""

from __future__ import annotations

import streamlit as st

_CSS_SGO = """
<style>
/* Sidebar escura, mesma paleta do Gestao_OS */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"] {
    background-color: #0F172A !important;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] small {
    color: #F8FAFC !important;
}

/* Logo do produto (ADR-0035, GIF/WebP animado via st.sidebar.image) -
   `st.logo` (ADR-0034) foi trocado por `st.sidebar.image` porque o
   slot fixo do `st.logo` nao aumenta o suficiente com `size="large"`
   nem e centralizavel (relatado com captura de tela real: logo
   minusculo, encostado no canto). Centralizado + moldura premium
   (cantos arredondados, sombra) aqui - escopado a `stSidebar` pra nao
   afetar nenhum outro `st.image` do restante do painel. */
[data-testid="stSidebar"] [data-testid="stImage"] {
    display: flex !important;
    justify-content: center !important;
    margin: 12px 0 !important;
}
[data-testid="stSidebar"] [data-testid="stImage"] img {
    border-radius: 14px !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5) !important;
}

/* Menu de navegacao (st.navigation/st.Page) - adaptacao do "pill menu"
   do Gestao_OS (que la e feito sobre um st.radio customizado). Os
   testids de st.navigation podem variar entre versoes do Streamlit -
   ajuste best-effort, conferir visualmente apos rodar `streamlit run`. */
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"] {
    border-radius: 8px !important;
    color: #CBD5E1 !important;
    transition: all 0.2s ease-in-out !important;
}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(255, 255, 255, 0.08) !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: rgba(255, 75, 75, 0.2) !important;
    border-left: 4px solid #FF4B4B !important;
    font-weight: bold !important;
    color: #FFFFFF !important;
}

/* Inputs/selects na sidebar */
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] div[data-baseweb="input"] > div,
[data-testid="stSidebar"] div[data-baseweb="base-input"] > input {
    background-color: #1E293B !important;
    border-color: #475569 !important;
    border-radius: 6px !important;
    color: white !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="input"] input {
    color: white !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background-color: #FF4B4B !important;
    color: white !important;
    border-radius: 6px !important;
}

/* Botoes em gradiente (global) - mesmos blocos do Gestao_OS */
button[kind="secondary"] {
    background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.3s ease !important;
    font-weight: 600 !important;
}
button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #2563EB 0%, #60A5FA 100%) !important;
    box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4) !important;
    transform: translateY(-2px) !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #991B1B 0%, #EF4444 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.3s ease !important;
    font-weight: 700 !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #DC2626 0%, #F87171 100%) !important;
    box-shadow: 0 6px 12px rgba(239, 68, 68, 0.4) !important;
    transform: translateY(-2px) !important;
}

/* Cards de KPI escuros - mesmas classes do Gestao_OS, para reaproveitar
   em qualquer tela que monte cards via st.markdown(unsafe_allow_html=True) */
.kpi-header-wrapper, .kpi-header-card {
    font-family: "Source Sans Pro", sans-serif;
}
.kpi-header-card {
    border-radius: 12px;
    padding: 16px 20px;
    background-color: #1A202C;
    border: 1px solid #333D4E;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    height: 140px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
    margin-bottom: 15px;
}
.kpi-border-gray { border-left: 4px solid #64748B; }
.kpi-border-red { border-left: 4px solid #EF4444; }
.kpi-border-green { border-left: 4px solid #10B981; }
.kpi-border-blue { border-left: 4px solid #3B82F6; }

.kpi-header-title {
    font-size: 14px; font-weight: 700; color: #94A3B8;
    margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;
}
.kpi-header-val { font-size: 32px; font-weight: 600; color: #F8FAFC; line-height: 1; }
.kpi-header-sub {
    font-size: 12px; font-weight: 600; margin-top: 8px;
    padding: 4px 10px; border-radius: 20px; display: inline-block; width: fit-content;
}
.badge-gray { background-color: rgba(100, 116, 139, 0.2); color: #CBD5E1; }
.badge-red { background-color: rgba(239, 68, 68, 0.2); color: #FCA5A5; }
.badge-green { background-color: rgba(16, 185, 129, 0.2); color: #6EE7B7; }
.badge-blue { background-color: rgba(59, 130, 246, 0.2); color: #93C5FD; }
</style>
"""


def aplicar_estilo_sgo() -> None:
    """Injeta o CSS da identidade visual do SGO. Chamar uma unica vez,
    logo apos st.set_page_config(), antes de montar qualquer conteudo."""
    st.markdown(_CSS_SGO, unsafe_allow_html=True)
