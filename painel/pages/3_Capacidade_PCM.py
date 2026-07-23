"""Capacidade PCM - piloto tecnico (Incremento 12).

Formula e buckets de docs/15_CAPACIDADE_PCM.md. Fonte oficial de escala,
ausencias/ferias e buckets oficiais de perdas sao decisoes pendentes
(docs/27 secao 15.3) - ver docs/39_ADR_0012_CAPACIDADE_PCM.md. O
mapeamento categoria->bucket nesta pagina e apenas um EXEMPLO, nunca uma
classificacao oficial.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ_PROJETO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dados import carregar_jornadas, formatar_horas, montar_resumo
from workforce_core.catalogo import Categoria, catalogo_padrao
from workforce_core.pcm import BucketCapacidade, PremissasCenario, simular_cenario

st.set_page_config(page_title="SGO Workforce | Capacidade PCM (piloto)", layout="wide")

st.warning(
    "Piloto tecnico. Fonte oficial de escala, ausencias/ferias e buckets "
    "oficiais de perdas ainda sao decisoes pendentes "
    "(ver docs/39_ADR_0012_CAPACIDADE_PCM.md). O mapeamento categoria -> "
    "bucket abaixo e um EXEMPLO para demonstrar o simulador, nao uma "
    "classificacao validada com a operacao."
)

st.title("SGO Workforce | Capacidade PCM (piloto)")

if "painel_diretorio_jornadas" not in st.session_state:
    st.session_state.painel_diretorio_jornadas = str(_RAIZ_PROJETO / "dados_locais" / "jornadas")

diretorio_jornadas = st.text_input("Diretorio de jornadas persistidas", key="painel_diretorio_jornadas")
if not diretorio_jornadas:
    st.warning("Informe o diretorio de jornadas para continuar.")
    st.stop()

jornadas, com_erro = carregar_jornadas(diretorio_jornadas)
if com_erro:
    st.error(f"{len(com_erro)} arquivo(s) de jornada corrompido(s), ignorado(s) sem apagar.")

if not jornadas:
    st.info("Nenhuma jornada encontrada nesse diretorio.")
    st.stop()

resumo = montar_resumo(jornadas)

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
    ausencias_horas = st.number_input(
        "Ausencias (horas, total do periodo)", min_value=0.0, value=0.0, step=0.5, key="pcm_ausencias"
    )

st.subheader("2. Mapeamento categoria -> bucket (EXEMPLO, nao oficial)")
_MAPEAMENTO_EXEMPLO = {
    Categoria.ATIVIDADE_PLANEJADA: BucketCapacidade.PRESENTE_PRODUTIVO_APLICAVEL,
    Categoria.ATENDIMENTO_FALHA: BucketCapacidade.FALHA_CORRETIVA,
    Categoria.DESLOCAMENTO_RODOVIARIO: BucketCapacidade.DESLOCAMENTO,
    Categoria.DESLOCAMENTO_FERROVIARIO: BucketCapacidade.DESLOCAMENTO,
    Categoria.AGUARDANDO_MATERIAL: BucketCapacidade.ESPERA_OPERACIONAL,
    Categoria.AGUARDANDO_INTERVALO_LIBERACAO: BucketCapacidade.ESPERA_OPERACIONAL,
    Categoria.APOIO_OPERACIONAL: BucketCapacidade.PRESENTE_PRODUTIVO_NAO_APLICAVEL,
    Categoria.REFEICAO: BucketCapacidade.PAUSA_LEGAL_REFEICAO,
    Categoria.DDS: BucketCapacidade.TREINAMENTO_DDS_REUNIAO,
    Categoria.REUNIAO: BucketCapacidade.TREINAMENTO_DDS_REUNIAO,
    Categoria.TREINAMENTO: BucketCapacidade.TREINAMENTO_DDS_REUNIAO,
    Categoria.ATIVIDADE_ADMINISTRATIVA: BucketCapacidade.PRESENTE_PRODUTIVO_NAO_APLICAVEL,
}
st.dataframe(
    [{"categoria": c.value, "bucket": b.value} for c, b in _MAPEAMENTO_EXEMPLO.items()],
    width="stretch",
)

resultado = simular_cenario(
    PremissasCenario(
        pessoas_previstas=int(pessoas_previstas),
        horas_escala=timedelta(hours=float(horas_escala)),
        ausencias=timedelta(hours=float(ausencias_horas)),
    ),
    resumo,
    _MAPEAMENTO_EXEMPLO,
)

st.subheader("3. Buckets observados (a partir das jornadas carregadas)")
st.dataframe(
    [
        {
            "bucket": (bucket.value if bucket is not None else "SEM_BUCKET_CONHECIDO"),
            "horas": formatar_horas(duracao),
        }
        for bucket, duracao in sorted(
            resultado.por_bucket.items(), key=lambda kv: kv[1], reverse=True
        )
    ],
    width="stretch",
)

st.subheader("4. Resultado")
col_a, col_b = st.columns(2)
col_a.metric("Capacidade bruta", formatar_horas(resultado.capacidade_bruta))
col_b.metric("Capacidade efetiva (so desconta ausencias nesta pagina)", formatar_horas(resultado.capacidade_efetiva))

st.caption(
    "Pausas nao computaveis, improdutividade e atividades nao aplicaveis "
    "da formula de docs/15 nao sao descontadas automaticamente aqui - "
    "isso exigiria decidir quais buckets contam como cada termo, o que e "
    "parte da classificacao produtiva/improdutiva ainda pendente "
    "(ADR-0005). Use os buckets observados acima para decidir manualmente."
)
