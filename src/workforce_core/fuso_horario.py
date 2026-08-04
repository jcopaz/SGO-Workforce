"""Fuso horario de referencia do SGO Workforce (pedido do responsavel
pelo produto em 2026-08-04: "calibre todo o aplicativo para o timezone
do Brasil").

Investigacao do estado atual (antes deste modulo existir) confirmou dois
bugs reais na ponta do painel, nao no motor de dominio nem no app de
campo:

- A interface de campo ja captura e envia o instante certo: `new Date()`
  captura o relogio do proprio aparelho (Brasil, presumivelmente ja
  configurado certo) e `.toISOString()` serializa esse instante em UTC
  (formato padrao, correto) antes de mandar pro backend
  (`interface_campo/js/sincronizacao.js`). O backend (`_str_para_dt`,
  `workforce_storage/serializacao.py`) preserva esse instante certinho ao
  reconstruir via `datetime.fromisoformat` (Python 3.11+ entende o sufixo
  "Z", devolve um datetime com tzinfo=UTC). Ate aqui, tudo correto - o
  instante real de cada evento nunca foi perdido nem distorcido.
- O bug estava em dois lugares que **exibiam/agrupavam esse instante UTC
  sem converter para o horario de Brasilia**: `painel/dados.py::formatar_data_hora`
  mostrava a hora UTC crua (3h adiantada em relacao ao horario real do
  colaborador) e `workforce_core/consolidacao.py` agrupava eventos por
  `data = inicio.date()` tambem em UTC - um evento as 22h de Brasilia (01h
  UTC do dia seguinte) contava para o dia ERRADO em todos os agrupamentos
  por data do painel (evolucao diaria, contagem por dia). O calculo de
  DURACAO (fim - inicio) nunca foi afetado - subtracao de datetimes aware
  no mesmo fuso da sempre o intervalo real, independente de qual fuso.

Este modulo centraliza a conversao, aplicada so no limite de
apresentacao/agrupamento por dia (nunca na captura nem no armazenamento,
que devem continuar em UTC - e a pratica correta, evita ambiguidade de
horario de verao e problemas de fuso ao comparar instantes).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")


def para_horario_brasil(momento: Optional[datetime]) -> Optional[datetime]:
    """Converte um datetime "aware" (com tzinfo, ex.: UTC vindo do
    backend) para o horario de Brasilia. `None` devolve `None`
    (passthrough comum nos campos opcionais de dominio - fim de atividade
    em andamento, etc.).

    Um datetime "naive" (sem tzinfo) e devolvido sem alteracao - convem
    para os testes/dados de exemplo deste repositorio, que constroem
    datetimes diretamente em Python (`datetime(2026, 1, 1, 8, 0)`) ja
    como "o horario certo", sem passar pelo round-trip JS/API que gera
    datetimes UTC-aware. Reinterpretar um naive como UTC quebraria esses
    horarios ja corretos.
    """
    if momento is None:
        return None
    if momento.tzinfo is None:
        return momento
    return momento.astimezone(FUSO_BRASIL)
