"""Capacidade PCM - piloto tecnico (Incremento 12).

Formula de docs/15_CAPACIDADE_PCM.md. Buckets e mapeamento categoria ->
bucket vem da planilha real de PCM da MRS Logistica, fornecida pelo
responsavel pelo produto em 2026-07-23 - ver
docs/42_ADR_0015_BUCKETS_REAIS_PCM.md. Fonte oficial de escala e de
ausencias externas (ferias/motivos legais) continuam pendentes
(docs/27 secao 15.3) - por isso continuam sendo entrada manual aqui.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st

from dados import carregar_jornadas_via_api, formatar_horas, montar_resumo
from workforce_core.catalogo import catalogo_relatorio_1_manutencao
from workforce_core.pcm import (
    mapeamento_categoria_bucket_relatorio_1_manutencao,
    simular_cenario_relatorio_1_manutencao,
)


def _obter_secret_seguro(chave: str, default: str = "") -> str:
    try:
        return st.secrets.get(chave, default)
    except Exception:
        return default


st.warning(
    "Piloto tecnico. Os buckets de perda e o mapeamento categoria -> bucket "
    "abaixo vem da planilha real de PCM da MRS Logistica (ver "
    "docs/42_ADR_0015_BUCKETS_REAIS_PCM.md), mas fonte oficial de escala e "
    "de ausencias externas (ferias/motivos legais) ainda sao decisoes "
    "pendentes (docs/27 secao 15.3) - por isso continuam sendo digitadas "
    "manualmente aqui."
)

st.title("SGO Workforce | Capacidade PCM (piloto)")

# Fonte de dados fixa em API (nuvem, ADR-0041) - mesmo padrao das demais
# telas (dashboard/falhas/mapa); esta tela ainda pedia um diretorio local
# ("Informe o diretório de jornadas") que nunca funcionou no Streamlit
# Cloud (sem disco persistente la) - corrigido junto da lapidacao geral do
# painel, 2026-08-12.
url_api = _obter_secret_seguro("SYNC_API_URL")
token_api = _obter_secret_seguro("SYNC_TOKEN")

if not url_api or not token_api:
    st.error(
        "Backend não configurado. Defina os secrets `SYNC_API_URL` e "
        "`SYNC_TOKEN` (Streamlit Cloud: Settings → Secrets) para o "
        "painel funcionar."
    )
    st.stop()

try:
    jornadas, com_erro = carregar_jornadas_via_api(url_api, token_api)
except requests.exceptions.RequestException as exc:
    st.error(f"Não foi possível buscar dados do backend: {exc}")
    st.stop()

if com_erro:
    st.error(
        f"{len(com_erro)} jornada(s) recebida(s) do backend com estrutura "
        f"inválida, ignorada(s): {', '.join(com_erro)}"
    )

if not jornadas:
    st.info("Nenhuma jornada encerrada no backend ainda.")
    st.stop()

catalogo = catalogo_relatorio_1_manutencao()
resumo = montar_resumo(jornadas, catalogo)

st.subheader("1. Premissas de escala (sempre exibidas - docs/15, 'Simulacao')")
col1, col2, col3 = st.columns(3)
with col1:
    pessoas_previstas = st.number_input(
        "Pessoas previstas", min_value=0, value=1, step=1, key="pcm_pessoas_previstas"
    )
with col2:
    horas_escala = st.number_input(
        "Horas de escala (por pessoa, no periodo)", min_value=0.0, value=8.0, step=0.5, key="pcm_horas_escala"
    )
with col3:
    ausencias_externas_horas = st.number_input(
        "Ausencias externas: ferias + motivos legais (horas) - sem fonte no sistema ainda",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="pcm_ausencias_externas",
    )

st.subheader("2. Mapeamento categoria -> bucket (planilha real MRS, ADR-0015)")
st.caption(
    "Manutencao Programada (EE17), Atendimento de Falha (EE21) e "
    "Manutencao Programada Nao Concluida (EE23) nao aparecem aqui: na "
    "planilha real, so contam como perda quando NAO vinculadas a uma OS "
    "planejada valida - o sistema ainda nao verifica isso automaticamente, "
    "entao ficam fora de qualquer bucket de perda por padrao (tratadas "
    "como capacidade efetiva). Ver ADR-0023 para a renumeracao de codigos."
)
mapeamento = mapeamento_categoria_bucket_relatorio_1_manutencao()
st.dataframe(
    [{"categoria": c.value, "bucket": b.value} for c, b in mapeamento.items()],
    width="stretch",
)

resultado = simular_cenario_relatorio_1_manutencao(
    pessoas_previstas=int(pessoas_previstas),
    horas_escala=timedelta(hours=float(horas_escala)),
    resumo=resumo,
    ausencias_externas=timedelta(hours=float(ausencias_externas_horas)),
)

st.subheader("3. Buckets observados (a partir das jornadas carregadas)")
st.dataframe(
    [
        {
            "bucket": (bucket.value if bucket is not None else "SEM_PERDA (produtivo/rentavel)"),
            "horas": formatar_horas(duracao),
        }
        for bucket, duracao in sorted(
            resultado.por_bucket.items(), key=lambda kv: kv[1], reverse=True
        )
    ],
    width="stretch",
)

st.subheader("4. Resultado")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Capacidade bruta", formatar_horas(resultado.capacidade_bruta))
col_b.metric("Capacidade efetiva", formatar_horas(resultado.capacidade_efetiva))
col_c.metric("Ausencias totais (externas + refeicao apontada)", formatar_horas(resultado.premissas.ausencias))

st.caption(
    "Pausas nao computaveis, improdutividade e atividades nao aplicaveis ao "
    "plano agora sao derivadas automaticamente do apontamento real via os "
    "buckets acima (ADR-0015) - so as ausencias externas (ferias/motivos "
    "legais) continuam manuais, por falta de fonte de RH/escala conectada."
)
