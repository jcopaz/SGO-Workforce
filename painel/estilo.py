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

/* Logo do produto - GIF animado via st.logo (ADR-0037/0038/0039).
   `st.logo` sozinho limita a altura renderizada a 32px mesmo com
   `size="large"` (limite documentado do proprio Streamlit) -
   sobrescrito aqui pra dar presenca visual de verdade.

   `data-testid` REAL do logo quando renderizado dentro da sidebar e
   `stSidebarLogo`, NAO `stLogo` (confirmado lendo o bundle JS
   instalado do Streamlit: o mesmo `LogoComponent` recebe
   `dataTestId="stSidebarLogo"` quando chamado a partir do componente
   da sidebar, sobrescrevendo o default `stLogo` do componente -
   `stLogo` sem sobrescrita so e usado no logo do cabecalho principal,
   mostrado quando a sidebar esta recolhida). O CSS do ADR-0038 corrigiu
   o bug do seletor (`img` descendente que nao existia) mas continuou
   testando o testid errado - por isso nao teve efeito nenhum, de novo.
   `data-testid="stSidebarLogo"` fica na propria tag <img> (mesma
   estrutura de `stLogo`), sem wrapper - uma unica regra, centralizacao
   via `margin: auto`. */
[data-testid="stSidebarLogo"] {
    display: block !important;
    height: 240px !important;
    width: auto !important;
    max-width: 100% !important;
    margin: 8px auto !important;
    border-radius: 14px !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5) !important;
    /* Forca o logo a ocupar a linha inteira (ver stSidebarHeader
       abaixo) - com flex-basis 100%, o botao de recolher (irmao
       seguinte no DOM) nao cabe mais na mesma linha e quebra pra
       linha de baixo sozinho, em vez de disputar espaco/sobrepor. */
    flex: 1 1 100% !important;
    order: 1 !important;
}

/* Container pai do logo (ADR-0040): `stSidebarHeader` do Streamlit tem
   `height` FIXA (um token pequeno de tema, pensado pra um logo de
   ~24-32px) e `flex-wrap` desligado por padrao - por isso o logo maior
   (240px) ficava cortado/sobreposto pelo conteudo seguinte em vez de
   empurra-lo pra baixo. `height:auto` deixa a linha crescer de verdade
   pro tamanho do logo; `flex-wrap:wrap` + o logo com `flex-basis:100%`
   acima fazem o botao de recolher quebrar pra proxima linha em vez de
   brigar por espaco horizontal na mesma linha. */
[data-testid="stSidebarHeader"] {
    height: auto !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    row-gap: 4px !important;
    margin-bottom: 16px !important;
}
[data-testid="stSidebarCollapseButton"] {
    order: 2 !important;
    margin-left: auto !important;
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

/* Cards de KPI - CLAROS (2026-08-12): a sidebar e' escura de proposito
   (identidade visual do Gestao_OS), mas o conteudo principal do painel
   usa o tema claro padrao do Streamlit - os cards de KPI copiados
   literalmente do Gestao_OS (fundo quase preto, #1A202C) ficavam como
   "ilhas escuras" boiando num fundo branco, a causa principal do painel
   parecer duas telas coladas em vez de um sistema so. Reestilizado pra
   combinar com o resto do conteudo principal (fundo claro, sombra suave),
   mantendo a borda colorida lateral (unico elemento que ja funcionava
   bem como codificacao visual por categoria). */
.kpi-header-wrapper, .kpi-header-card {
    font-family: "Source Sans Pro", sans-serif;
}
.kpi-header-card {
    border-radius: 12px;
    padding: 16px 20px;
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
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
    font-size: 14px; font-weight: 700; color: #64748B;
    margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;
}
.kpi-header-val { font-size: 32px; font-weight: 600; color: #0F172A; line-height: 1; }
.kpi-header-sub {
    font-size: 12px; font-weight: 600; margin-top: 8px;
    padding: 4px 10px; border-radius: 20px; display: inline-block; width: fit-content;
}
.badge-gray { background-color: rgba(100, 116, 139, 0.12); color: #475569; }
.badge-red { background-color: rgba(239, 68, 68, 0.12); color: #B91C1C; }
.badge-green { background-color: rgba(16, 185, 129, 0.12); color: #047857; }
.badge-blue { background-color: rgba(59, 130, 246, 0.12); color: #1D4ED8; }
</style>
"""


def aplicar_estilo_sgo() -> None:
    """Injeta o CSS da identidade visual do SGO. Chamar uma unica vez,
    logo apos st.set_page_config(), antes de montar qualquer conteudo."""
    st.markdown(_CSS_SGO, unsafe_allow_html=True)
