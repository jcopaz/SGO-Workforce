"""Carregamento e agregacao de dados para o painel gerencial (Incremento 9).

Le jornadas persistidas (workforce_storage) e usa
workforce_core.consolidacao para os totais - a mesma fonte de calculo
usada no resto do sistema, para que o painel nunca produza um numero que
diverge do motor de dominio. Sem dependencia de Streamlit neste modulo,
para poder ser testado com pytest normalmente.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests

from workforce_core import MotorJornada, TipoEventoSecundario
from workforce_core.catalogo import Categoria, CatalogoMotivos, catalogo_completo
from workforce_core.consolidacao import LinhaEvento, ResumoConsolidado, linhas_eventos_classificadas, resumo_consolidado
from workforce_core.entities import Jornada, PulsoGps
from workforce_storage import ArquivoCorrompidoError, RepositorioJornadaArquivo
from workforce_storage.repositorio_pulsos_gps import RepositorioPulsosGpsArquivo
from workforce_storage.serializacao import jornada_de_dict


def carregar_jornadas(diretorio: Union[str, Path]) -> Tuple[List[Jornada], List[str]]:
    """Carrega todas as jornadas persistidas em um diretorio.

    Retorna (jornadas_validas, ids_com_erro). Arquivos corrompidos sao
    reportados para quem chama decidir o que exibir - nunca apagados nem
    escondidos silenciosamente (mesma regra de ouro de workforce_storage).
    """
    repo = RepositorioJornadaArquivo(diretorio)
    jornadas: List[Jornada] = []
    com_erro: List[str] = []
    for jornada_id in repo.listar_ids():
        try:
            jornadas.append(repo.carregar(jornada_id))
        except ArquivoCorrompidoError:
            com_erro.append(str(jornada_id))
    return jornadas, com_erro


def carregar_jornadas_via_api(url_base: str, token: str) -> Tuple[List[Jornada], List[str]]:
    """Busca as jornadas do backend real (workforce_api) em vez de ler
    arquivos locais - usado quando o painel esta configurado com a fonte
    de dados "API (nuvem)" (docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md).

    Mesma assinatura de retorno de carregar_jornadas() (jornadas validas,
    ids/identificadores com erro) para o resto do painel nao precisar saber
    de qual fonte os dados vieram. Erros de rede/autenticacao (backend
    fora do ar, token errado) propagam como requests.exceptions.RequestException
    - quem chama decide como exibir isso (nunca escondido silenciosamente).
    """
    resposta = requests.get(
        f"{url_base.rstrip('/')}/jornadas",
        headers={"X-Sync-Token": token},
        # Render free tier "dorme" o backend apos ~15 min sem uso - a
        # primeira chamada depois disso pode levar dezenas de segundos
        # para acordar o servico. Timeout generoso para nao falhar so por
        # causa do cold start (nao e erro de verdade, e so lentidao).
        timeout=60,
    )
    resposta.raise_for_status()

    jornadas: List[Jornada] = []
    com_erro: List[str] = []
    for item in resposta.json():
        try:
            jornadas.append(jornada_de_dict(item))
        except (KeyError, ValueError, TypeError):
            com_erro.append(str(item.get("id", "desconhecido")))
    return jornadas, com_erro


def montar_resumo(jornadas: List[Jornada], catalogo: CatalogoMotivos | None = None) -> ResumoConsolidado:
    """Usa catalogo_completo() por padrao (motivos de teste + codigos reais
    EE01-EE23, ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md).
    Usar so catalogo_padrao() aqui fazia toda pausa registrada de verdade
    pela interface de campo (codigos EE02/EE07/EE11/EE21/EE23) cair em
    "sem categoria conhecida", porque esses codigos nao estavam no
    catalogo de teste.
    """
    return resumo_consolidado(jornadas, catalogo or catalogo_completo())


def montar_linhas_eventos(
    jornadas: List[Jornada], catalogo: CatalogoMotivos | None = None
) -> List[LinhaEvento]:
    """Base para os filtros do painel (colaborador, periodo, categoria,
    motivo/justificativa) - uma linha por atividade/pausa/evento
    secundario encerrado. Mesmo catalogo padrao de montar_resumo()."""
    return linhas_eventos_classificadas(jornadas, catalogo or catalogo_completo())


def agrupar_duracao_por_categoria(linhas: List[LinhaEvento]) -> Dict[Optional[Categoria], timedelta]:
    """Agrega LinhaEvento por categoria - usado para recalcular os graficos
    de categoria do painel apos os filtros de categoria/motivo (diferente
    de ResumoConsolidado.por_categoria, que reflete so o filtro de
    colaborador/periodo, ja que e derivado das jornadas inteiras)."""
    totais: Dict[Optional[Categoria], timedelta] = {}
    for linha in linhas:
        totais[linha.categoria] = totais.get(linha.categoria, timedelta()) + linha.duracao
    return totais


def formatar_data_hora(data: Optional[datetime]) -> str:
    """Formato dd/mm/aaaa hh:mm:ss para exibicao - nunca usado como fonte
    de calculo, so apresentacao de um datetime ja persistido."""
    if data is None:
        return "--"
    return data.strftime("%d/%m/%Y %H:%M:%S")


def formatar_horas(duracao: timedelta) -> str:
    """Formato "XhYY" para exibicao - nunca usado como fonte de calculo."""
    total_minutos = round(duracao.total_seconds() / 60)
    horas, minutos = divmod(total_minutos, 60)
    return f"{horas}h{minutos:02d}"


def gerar_jornadas_exemplo(diretorio: Union[str, Path], quantidade: int = 3) -> List[Jornada]:
    """Gera jornadas fabricadas para demonstrar o painel sem depender de dados reais.

    Uso exclusivo de teste/demonstracao do piloto tecnico - os dados nao
    representam nenhuma operacao real e nunca devem ser confundidos com
    apontamentos verdadeiros.
    """
    repo = RepositorioJornadaArquivo(diretorio)
    base = datetime(2026, 1, 1, 8, 0)
    criadas: List[Jornada] = []

    for i in range(quantidade):
        inicio = base + timedelta(days=i)
        motor = MotorJornada(f"MATRICULA-EXEMPLO-{i + 1:03d}")
        motor.iniciar_jornada(inicio)

        motor.iniciar_evento_secundario(
            inicio, TipoEventoSecundario.DESLOCAMENTO, "DESLOCAMENTO_TESTE"
        )
        motor.encerrar_evento_secundario(inicio + timedelta(minutes=30))

        motor.iniciar_atividade(inicio + timedelta(minutes=30))
        motor.iniciar_pausa(inicio + timedelta(hours=1), "PAUSA_TESTE")
        motor.finalizar_pausa(inicio + timedelta(hours=1, minutes=15))
        motor.encerrar_atividade(inicio + timedelta(hours=3))

        if i == 0:
            motor.iniciar_atendimento_falha(inicio + timedelta(hours=3))
            motor.registrar_dados_falha(
                nota="EXEMPLO-1",
                ativo="ATIVO-EXEMPLO",
                sintoma="Sintoma de exemplo",
                objeto="Componente de exemplo",
                observacao="Dado gerado para demonstracao do painel.",
            )
            motor.encerrar_atividade(inicio + timedelta(hours=3, minutes=45))
            motor.encerrar_jornada(inicio + timedelta(hours=3, minutes=45))
        else:
            motor.encerrar_jornada(inicio + timedelta(hours=3))

        repo.salvar(motor.jornada)
        criadas.append(motor.jornada)

    return criadas


def carregar_pulsos(diretorio: Union[str, Path], jornada_id) -> List[PulsoGps]:
    return RepositorioPulsosGpsArquivo(diretorio).ler_pulsos(jornada_id)


def gerar_pulsos_exemplo(
    diretorio: Union[str, Path],
    jornada: Jornada,
    *,
    latitude_base: float = -23.5505,
    longitude_base: float = -46.6333,
    intervalo_segundos: int = 120,
) -> List[PulsoGps]:
    """Gera pulsos GPS fabricados ao longo do periodo de uma jornada de
    exemplo, para demonstrar o mapa operacional sem depender de captura
    real de GPS (que nao existe em interface_campo/js/, ver ADR-0007).

    Coordenadas de partida sao a Praca da Se, em Sao Paulo, apenas como
    ponto de referencia arbitrario para o piloto tecnico - nao representam
    nenhuma localizacao operacional real.
    """
    if jornada.inicio is None or jornada.fim is None:
        return []

    repo = RepositorioPulsosGpsArquivo(diretorio)
    rng = random.Random(str(jornada.id))
    lat, lon = latitude_base, longitude_base
    pulsos: List[PulsoGps] = []

    t = jornada.inicio
    passo = 0
    while t <= jornada.fim:
        if passo % 10 < 7:  # a maior parte do tempo em pequeno deslocamento
            lat += rng.uniform(-0.0006, 0.0006)
            lon += rng.uniform(-0.0006, 0.0006)
        pulso = PulsoGps(
            jornada_id=jornada.id,
            colaborador_matricula=jornada.colaborador_matricula,
            latitude=lat,
            longitude=lon,
            precisao_metros=rng.uniform(5, 15),
            timestamp_dispositivo=t,
        )
        repo.gravar_pulso(pulso)
        pulsos.append(pulso)
        t += timedelta(seconds=intervalo_segundos)
        passo += 1

    return pulsos
