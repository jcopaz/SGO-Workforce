"""Carregamento e agregacao de dados para o painel gerencial (Incremento 9).

Le jornadas persistidas (workforce_storage) e usa
workforce_core.consolidacao para os totais - a mesma fonte de calculo
usada no resto do sistema, para que o painel nunca produza um numero que
diverge do motor de dominio. Sem dependencia de Streamlit neste modulo,
para poder ser testado com pytest normalmente.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests

from workforce_core import MotorJornada, TipoEventoSecundario
from workforce_core.catalogo import Categoria, CatalogoMotivos, ClassificacaoHH, catalogo_completo
from workforce_core.consolidacao import (
    IntervaloClassificado,
    LinhaAtendimentoFalha,
    LinhaEvento,
    ResumoAtendimentosFalha,
    ResumoConsolidado,
    agrupar_ativo_sintoma,
    ativos_reincidentes,
    contagem_por_ativo,
    contagem_por_objeto,
    contagem_por_sintoma,
    duracao_media_por_sintoma,
    linha_do_tempo,
    linhas_atendimento_falha,
    linhas_eventos_classificadas,
    resumo_atendimentos_falha,
    resumo_consolidado,
    resumo_consolidado_por_colaborador,
    utilizacao_hh,
)
from workforce_core.entities import Jornada, PulsoGps
from workforce_core.fuso_horario import para_horario_brasil
from workforce_core.qualidade_gps import avaliar_pulso
from workforce_storage import ArquivoCorrompidoError, RepositorioJornadaArquivo
from workforce_storage.repositorio_pulsos_gps import RepositorioPulsosGpsArquivo
from workforce_storage.serializacao import jornada_de_dict, pulso_gps_de_dict

# Rotulos legiveis para o gestor (pedido em 2026-07-31: "o gestor nao tem
# de cabeca os motivos, precisa ser descritivo") - o gestor via as
# categorias como ATIVIDADE_PLANEJADA/DESLOCAMENTO_A_PE cruas nos
# graficos. Fonte unica usada tanto pelos graficos (painel/graficos.py)
# quanto pelos filtros da tela (painel/telas/dashboard.py), para o rotulo
# de um multiselect e o de uma legenda nunca divergirem. Cobre todos os
# valores de Categoria (workforce_core/catalogo.py) - texto livre em
# portugues, nao e dado de negocio (nao precisa de validacao do
# responsavel do produto, e so apresentacao).
ROTULOS_CATEGORIA: Dict[Categoria, str] = {
    Categoria.ATIVIDADE_PLANEJADA: "Atividade planejada",
    Categoria.ATENDIMENTO_FALHA: "Atendimento de falha",
    Categoria.DESLOCAMENTO_RODOVIARIO: "Deslocamento rodoviário",
    Categoria.DESLOCAMENTO_FERROVIARIO: "Deslocamento ferroviário",
    Categoria.DESLOCAMENTO_A_PE: "Deslocamento a pé",
    Categoria.REFEICAO: "Refeição",
    Categoria.DDS: "DDS",
    Categoria.REUNIAO: "Reunião",
    Categoria.TREINAMENTO: "Treinamento",
    Categoria.AGUARDANDO_MATERIAL: "Aguardando material",
    Categoria.AGUARDANDO_INTERVALO_LIBERACAO: "Aguardando intervalo/liberação",
    Categoria.APOIO_OPERACIONAL: "Apoio operacional",
    Categoria.ATIVIDADE_ADMINISTRATIVA: "Atividade administrativa",
    Categoria.OUTROS_CATALOGADOS: "Outros catalogados",
    Categoria.PREPARACAO_JORNADA: "Preparação para jornada",
    Categoria.AGUARDANDO_CCO: "Aguardando CCO",
    Categoria.TREM_PARADO_FRENTE_SERVICO: "Trem parado na frente de serviço",
    Categoria.RESTRICAO_INFRAESTRUTURA: "Restrição de infraestrutura",
    Categoria.SERVICO_INTERNO_COORDENACAO: "Serviço interno da coordenação",
    Categoria.TRABALHO_NAO_DISTRIBUIDO: "Trabalho não distribuído",
    Categoria.AGUARDANDO_SEQUENCIA_SERVICO: "Aguardando sequência de serviço",
    Categoria.CONSULTA_DOCUMENTACAO_TECNICA: "Consulta à documentação técnica",
    Categoria.PREPARAR_ATIVIDADE: "Preparar atividade",
    Categoria.DESMONTAR_ATIVIDADE: "Desmontar atividade",
    Categoria.CARREGAR_VEICULO: "Carregar veículo",
    Categoria.DESCARREGAR_VEICULO: "Descarregar veículo",
    # Categoria.SMS e o valor historico do codigo EE20 "DDS / APR" no
    # catalogo (nome herdado, nao "Segurança/Meio ambiente/Saúde"
    # generico) - rotulo usa a descricao real do codigo para nao confundir.
    Categoria.SMS: "DDS / APR",
    Categoria.ATIVIDADE_PLANEJADA_NAO_CONCLUIDA: "Atividade planejada não concluída",
}

ROTULO_SEM_CATEGORIA = "Sem categoria"


def rotulo_categoria(categoria: Optional[Categoria]) -> str:
    """Rotulo legivel de uma Categoria - "Sem categoria" para None. Fonte
    unica para graficos e filtros (ver ROTULOS_CATEGORIA acima)."""
    if categoria is None:
        return ROTULO_SEM_CATEGORIA
    return ROTULOS_CATEGORIA.get(categoria, categoria.value)


def rotulo_motivo(codigo: Optional[str], catalogo: CatalogoMotivos | None = None) -> str:
    """Rotulo legivel de um codigo de motivo (pausa/evento secundario) -
    "codigo - descricao" (mesmo formato ja usado nos seletores da
    interface de campo, familiar para a operacao) em vez do codigo cru.
    Cai no proprio codigo se ele nao estiver no catalogo informado (nunca
    quebra por um motivo desconhecido/de teste)."""
    if codigo is None:
        return "Sem motivo"
    entrada = (catalogo or catalogo_completo()).obter(codigo)
    if entrada is None:
        return codigo
    return f"{codigo} - {entrada.descricao}"


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
    EE01-EE23, ver docs/41_ADR_0014_CATALOGO_REAL_RELATORIO_ATIVIDADES.md e
    docs/50_ADR_0023_RECLASSIFICACAO_CATALOGO_RELATORIO_1.md para a
    renumeracao/reclassificacao de 2026-07-27). Usar so catalogo_padrao()
    aqui fazia toda pausa registrada de verdade pela interface de campo
    (codigos EE02/EE07/EE11/EE20/EE22) cair em "sem categoria conhecida",
    porque esses codigos nao estavam no catalogo de teste.
    """
    return resumo_consolidado(jornadas, catalogo or catalogo_completo())


def montar_linhas_eventos(
    jornadas: List[Jornada], catalogo: CatalogoMotivos | None = None
) -> List[LinhaEvento]:
    """Base para os filtros do painel (colaborador, periodo, categoria,
    motivo/justificativa) - uma linha por atividade/pausa/evento
    secundario encerrado. Mesmo catalogo padrao de montar_resumo()."""
    return linhas_eventos_classificadas(jornadas, catalogo or catalogo_completo())


def montar_linhas_atendimento_falha(jornadas: List[Jornada]) -> List[LinhaAtendimentoFalha]:
    """Base para a aba "Falhas" do painel (ADR-0029) - uma linha por
    atendimento de falha encerrado. Diferente de montar_linhas_eventos,
    inclui jornadas ainda abertas (ver linhas_atendimento_falha)."""
    return linhas_atendimento_falha(jornadas)


def resumo_atendimentos_falha_do_periodo(linhas: List[LinhaAtendimentoFalha]) -> ResumoAtendimentosFalha:
    """KPIs (quantidade, duração total/média, maior duração) de uma lista
    de LinhaAtendimentoFalha já filtrada pelo período/colaborador
    selecionados no painel."""
    return resumo_atendimentos_falha(linhas)


def contagem_atendimentos_por_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    return contagem_por_sintoma(linhas)


def contagem_atendimentos_por_ativo(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    return contagem_por_ativo(linhas)


def contagem_atendimentos_por_objeto(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    return contagem_por_objeto(linhas)


def duracao_media_atendimentos_por_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, timedelta]:
    return duracao_media_por_sintoma(linhas)


def ativos_reincidentes_do_periodo(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, int]:
    return ativos_reincidentes(linhas)


def agrupar_atendimentos_ativo_sintoma(linhas: List[LinhaAtendimentoFalha]) -> Dict[str, Dict[str, timedelta]]:
    return agrupar_ativo_sintoma(linhas)


def utilizacao_hh_do_resumo(resumo: ResumoConsolidado) -> Optional[float]:
    """Utilizacao HH (ADR-0027) = Horas Produtivas / Horas Totais, a partir
    de um ResumoConsolidado ja calculado (montar_resumo). Horas Produtivas
    vem de por_classificacao_hh[PRODUTIVA] - desde o ADR-0028, PRODUTIVA e
    especificamente "produtiva rentavel" (ex.: EE17/EE21), separada de
    PRODUTIVA_NAO_RENTAVEL (deslocamento, preparar/desmontar atividade
    etc.) - esta funcao NAO soma as duas, de proposito (ver
    horas_produtiva_nao_rentavel_do_resumo para o outro numero). Horas
    Totais e jornada_bruta_total. Retorna None quando jornada_bruta_total
    e zero (nenhuma jornada encerrada valida no filtro) - nunca
    ZeroDivisionError."""
    horas_produtivas = resumo.por_classificacao_hh.get(ClassificacaoHH.PRODUTIVA, timedelta())
    return utilizacao_hh(horas_produtivas, resumo.jornada_bruta_total)


def utilizacao_hh_por_colaborador(
    jornadas: List[Jornada], catalogo: CatalogoMotivos | None = None
) -> Dict[str, Optional[float]]:
    """Utilizacao HH (ADR-0027) individual, um valor por colaborador -
    permite comparar quem esta convertendo mais/menos periodo de trabalho
    em manutencao rentavel, em vez de so o agregado do periodo inteiro.
    None para um colaborador especifico so aconteceria com jornada_bruta
    zero, o que resumo_consolidado_por_colaborador ja evita ao excluir
    colaboradores sem nenhuma jornada encerrada."""
    por_colaborador = resumo_consolidado_por_colaborador(jornadas, catalogo or catalogo_completo())
    return {
        colaborador: utilizacao_hh_do_resumo(resumo) for colaborador, resumo in por_colaborador.items()
    }


def horas_produtiva_nao_rentavel_do_resumo(resumo: ResumoConsolidado) -> timedelta:
    """Horas classificadas como PRODUTIVA_NAO_RENTAVEL (ADR-0028) num
    ResumoConsolidado ja calculado - deslocamento, preparar/desmontar
    atividade, carregar/descarregar veiculo, SMS, treinamento e consulta a
    documentacao tecnica (EE11-EE16, EE18-EE20, EE22). Exibida ao lado de
    Utilizacao HH no painel para o gestor ver as duas fatias do tempo
    produtivo separadas, nunca misturadas."""
    return resumo.por_classificacao_hh.get(ClassificacaoHH.PRODUTIVA_NAO_RENTAVEL, timedelta())


def agrupar_duracao_por_categoria(linhas: List[LinhaEvento]) -> Dict[Optional[Categoria], timedelta]:
    """Agrega LinhaEvento por categoria - usado para recalcular os graficos
    de categoria do painel apos os filtros de categoria/motivo (diferente
    de ResumoConsolidado.por_categoria, que reflete so o filtro de
    colaborador/periodo, ja que e derivado das jornadas inteiras)."""
    totais: Dict[Optional[Categoria], timedelta] = {}
    for linha in linhas:
        totais[linha.categoria] = totais.get(linha.categoria, timedelta()) + linha.duracao
    return totais


def contagem_e_duracao_media_por_motivo(linhas: List[LinhaEvento]) -> Dict[str, Tuple[int, timedelta]]:
    """Frequencia (numero de ocorrencias) e duracao media por motivo -
    base do scatter "duracao x frequencia" (docs/12_DASHBOARDS_ECHARTS.md).
    So considera linhas com motivo preenchido (pausas/eventos secundarios
    - atividades nao tem motivo, ver LinhaEvento)."""
    total_por_motivo: Dict[str, timedelta] = {}
    contagem: Dict[str, int] = {}
    for linha in linhas:
        if linha.motivo is None:
            continue
        total_por_motivo[linha.motivo] = total_por_motivo.get(linha.motivo, timedelta()) + linha.duracao
        contagem[linha.motivo] = contagem.get(linha.motivo, 0) + 1
    return {
        motivo: (contagem[motivo], total / contagem[motivo]) for motivo, total in total_por_motivo.items()
    }


def formatar_data_hora(data: Optional[datetime]) -> str:
    """Formato dd/mm/aaaa hh:mm:ss para exibicao - nunca usado como fonte
    de calculo, so apresentacao de um datetime ja persistido.

    Converte para o horario de Brasilia antes de formatar
    (`workforce_core.fuso_horario.para_horario_brasil`) - os timestamps
    que chegam aqui vindo do backend sao "aware" em UTC (a interface de
    campo serializa via `.toISOString()`); sem essa conversao, o painel
    mostrava o horario UTC cru, 3h adiantado em relacao ao horario real
    do colaborador."""
    if data is None:
        return "--"
    return para_horario_brasil(data).strftime("%d/%m/%Y %H:%M:%S")


def formatar_data(data: Optional[datetime]) -> str:
    """Formato dd/mm/aaaa (sem hora) - mesma conversao pro horario de
    Brasilia de `formatar_data_hora`, so mais curto para listas onde o
    horario exato nao ajuda a diferenciar visualmente (ex.: selectbox de
    Jornada, ADR-0053 - pedido do responsavel pelo produto em
    2026-08-05: o rotulo completo com segundos ficava verboso demais)."""
    if data is None:
        return "--"
    return para_horario_brasil(data).strftime("%d/%m/%Y")


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


# Simulador ETL (ADR-0033) - ativos/sintomas/objetos fabricados para
# atendimentos de falha simulados, contexto ferroviario (MRS) coerente com
# o resto do catalogo (Deslocamento ferroviario, Trem parado na frente de
# servico etc.) - nunca confundir com ativo real, sempre rotulado "(dado
# simulado)" na observacao.
_ATIVOS_SIMULADOS = [
    "Locomotiva 1042", "Locomotiva 2087", "Locomotiva 3311", "Locomotiva 4456",
    "Vagão HFT-208", "Vagão HFT-311", "Vagão GDT-522",
    "Chave 12B", "Sinaleira KM 340", "AMV 07",
]
_SINTOMAS_SIMULADOS = [
    "Falha no sistema de freios", "Motor não liga", "Vazamento hidráulico",
    "Sensor de velocidade com defeito", "Painel de controle travado",
    "Superaquecimento do motor", "Ruído anormal no truque", "Perda de tração",
]
_OBJETOS_SIMULADOS = [
    "Motor de tração", "Sistema de freios", "Compressor de ar",
    "Bateria auxiliar", "Sistema elétrico", "Suspensão", "Acoplamento",
]


def gerar_jornadas_exemplo_volumoso(
    diretorio: Union[str, Path],
    quantidade_colaboradores: int = 20,
    dias: int = 30,
    semente: int = 42,
) -> List[Jornada]:
    """Simulador ETL de volume maior (ADR-0033) - gera muitas jornadas
    variadas (colaboradores x dias, motivo/categoria sorteado entre os
    ~19 codigos EE01-EE22 realmente usaveis pelo motor) para ver como os
    graficos do painel se comportam com dado em escala, em vez dos 3
    exemplos minimos de `gerar_jornadas_exemplo` - útil especificamente
    para verificar se a legenda com paginacao, o eixo rotacionado e o
    sankey/scatter com muitas series continuam legiveis quando o numero
    de categorias/colaboradores/motivos cresce de verdade.

    Cada jornada gerada segue exatamente as mesmas regras do motor de
    dominio (`MotorJornada` - a mesma classe usada pela interface de
    campo real): evento secundario (Deslocamento/Espera/Apoio) sempre
    fora de uma atividade principal, pausa sempre dentro de uma atividade
    ativa - nao ha atalho que pule essas regras so por ser dado de teste.

    EE23 (Manutencao Programada Nao Concluida, fecha por
    `encerrar_atividade_nao_concluida` em vez de `encerrar_atividade`) e
    deliberadamente deixado fora - caso raro em uso real, sem valor extra
    pra este simulador (o objetivo e volume/variedade visual dos
    graficos, nao cobertura exaustiva do catalogo).

    Uso exclusivo de teste/demonstracao do piloto tecnico - os dados nao
    representam nenhuma operacao real e nunca devem ser confundidos com
    apontamentos verdadeiros (toda observacao de falha simulada e
    marcada "(dado simulado)")."""
    aleatorio = random.Random(semente)
    # So os codigos EE reais (catalogo_relatorio_1_manutencao) - exclui os
    # motivos legados de catalogo_padrao() (PAUSA_TESTE, REFEICAO, DDS,
    # REUNIAO, TREINAMENTO etc., todos com tipo_registro default "pausa"),
    # senao o simulador mistura dois codigos diferentes pro mesmo motivo
    # real (ex.: "REFEICAO" e "EE02 - Refeição 1 hora" como bars separadas).
    catalogo = catalogo_completo()
    eventos_secundarios = [
        e for e in catalogo.todos() if e.tipo_registro == "evento_secundario" and e.codigo.startswith("EE")
    ]
    pausas = [e for e in catalogo.todos() if e.tipo_registro == "pausa" and e.codigo.startswith("EE")]

    repo = RepositorioJornadaArquivo(diretorio)
    base = datetime(2026, 6, 1, 7, 0)
    criadas: List[Jornada] = []
    contador_falha = 0

    for colaborador_idx in range(quantidade_colaboradores):
        matricula = f"SIM-{colaborador_idx + 1:03d}"
        for dia_idx in range(dias):
            if aleatorio.random() < 0.15:
                continue  # nem todo colaborador trabalha todo dia - folga/férias simulada

            agora = base + timedelta(days=dia_idx, minutes=aleatorio.randint(0, 45))
            motor = MotorJornada(matricula)
            motor.iniciar_jornada(agora)

            for entrada in aleatorio.sample(eventos_secundarios, k=aleatorio.randint(1, 3)):
                motor.iniciar_evento_secundario(agora, entrada.tipo_evento_secundario, entrada.codigo)
                agora += timedelta(minutes=aleatorio.randint(10, 40))
                motor.encerrar_evento_secundario(agora)

            motor.iniciar_atividade(agora)
            for entrada in aleatorio.sample(pausas, k=aleatorio.randint(0, 2)):
                motor.iniciar_pausa(agora, entrada.codigo)
                agora += timedelta(minutes=aleatorio.randint(10, 60))
                motor.finalizar_pausa(agora)
            agora += timedelta(minutes=aleatorio.randint(60, 210))
            motor.encerrar_atividade(agora)

            if aleatorio.random() < 0.18:
                # `iniciar_atendimento_falha` abre a sua propria atividade
                # principal (nao aninha na EE17 acima) - por isso a EE17
                # precisa estar encerrada antes de chegar aqui.
                contador_falha += 1
                motor.iniciar_atendimento_falha(agora)
                motor.registrar_dados_falha(
                    nota=f"SIM-FALHA-{contador_falha:04d}",
                    ativo=aleatorio.choice(_ATIVOS_SIMULADOS),
                    sintoma=aleatorio.choice(_SINTOMAS_SIMULADOS),
                    objeto=aleatorio.choice(_OBJETOS_SIMULADOS),
                    observacao="Atendimento de falha (dado simulado - simulador ETL, ADR-0033).",
                )
                agora += timedelta(minutes=aleatorio.randint(20, 90))
                motor.encerrar_atividade(agora)

            motor.encerrar_jornada(agora)

            repo.salvar(motor.jornada)
            criadas.append(motor.jornada)

    return criadas


def carregar_pulsos(diretorio: Union[str, Path], jornada_id) -> List[PulsoGps]:
    return RepositorioPulsosGpsArquivo(diretorio).ler_pulsos(jornada_id)


def carregar_pulsos_via_api(url_base: str, token: str, jornada_id) -> Tuple[List[PulsoGps], List[str]]:
    """Busca os pulsos GPS de uma jornada do backend real (workforce_api)
    em vez de ler arquivo local - mesmo papel de carregar_jornadas_via_api
    (ver docs/70_ADR_0043_DECISOES_CAPTACAO_PERIODICA_PULSO_GPS.md e o ADR
    seguinte, da Fase 1 do backend de pulsos).

    `jornada_id` e obrigatorio - GET /pulsos nunca devolve os pulsos de
    todo mundo de uma vez so. Mesma assinatura de retorno de
    carregar_jornadas_via_api (itens validos, ids com erro de estrutura) -
    nunca esconde erro silenciosamente."""
    resposta = requests.get(
        f"{url_base.rstrip('/')}/pulsos",
        params={"jornada_id": str(jornada_id)},
        headers={"X-Sync-Token": token},
        # Mesmo motivo do timeout generoso de carregar_jornadas_via_api:
        # o Render free tier "dorme" o backend apos ~15 min sem uso.
        timeout=60,
    )
    resposta.raise_for_status()

    pulsos: List[PulsoGps] = []
    com_erro: List[str] = []
    for item in resposta.json():
        try:
            pulsos.append(pulso_gps_de_dict(item))
        except (KeyError, ValueError, TypeError):
            com_erro.append(str(item.get("id", "desconhecido")))
    return pulsos, com_erro


def obter_url_foto_falha(url_base: str, token: str, caminho: str) -> str:
    """Busca uma URL assinada (valida por tempo limitado) para exibir a
    foto de um atendimento de falha (ADR-0054 - a foto ja era enviada
    desde o ADR-0022, mas nunca tinha tela de exibicao no painel).

    `caminho` e a referencia permanente devolvida por `POST /fotos`
    (`DadosFalha.foto_caminho`), nunca uma URL - o painel nunca fala
    direto com o Supabase Storage nem guarda a service_role key; sempre
    passa por `GET /fotos/url` do backend (mesmo token de sincronizacao
    dos demais endpoints). Deliberadamente sem `st.cache_data`: a URL
    expira (`expira_em_segundos` no backend, 1h por padrao) - cachear por
    mais tempo que isso devolveria um link morto.
    """
    resposta = requests.get(
        f"{url_base.rstrip('/')}/fotos/url",
        params={"caminho": caminho},
        headers={"X-Sync-Token": token},
        timeout=60,
    )
    resposta.raise_for_status()
    return resposta.json()["url"]


def filtrar_pulsos_por_periodo(
    pulsos: List[PulsoGps], data_inicio: date, data_fim: date, hora_inicial: time, hora_final: time
) -> List[PulsoGps]:
    """Filtro de periodo (data inicio/fim) + faixa de horario do mapa
    operacional (pedido do responsavel pelo produto em 2026-08-04, ver
    ADR-0047; ampliado de data unica para intervalo em 2026-08-12, ADR-0067
    - uma jornada que atravessa a meia-noite de Brasilia sumia do mapa
    depois das 00h01 do dia seguinte, ja que o filtro so aceitava 1 dia).

    Converte cada timestamp para o horario de Brasilia
    (`workforce_core.fuso_horario.para_horario_brasil`) antes de comparar
    - filtrar pela data/hora UTC crua faria um pulso das 23h de Brasilia
    (ja virou o dia seguinte em UTC) sumir do filtro do dia certo.
    Inclusivo nos limites de data (`data_inicio <= X <= data_fim`) e de
    horario (`hora_inicial <= X <= hora_final`, aplicado a CADA dia do
    intervalo - util para recortar "so o turno da manha" ao longo de
    varios dias, por exemplo). `data_inicio == data_fim` reproduz o
    comportamento antigo de dia unico.
    """
    resultado = []
    for pulso in pulsos:
        momento_brasil = para_horario_brasil(pulso.timestamp_dispositivo)
        if not (data_inicio <= momento_brasil.date() <= data_fim):
            continue
        if not (hora_inicial <= momento_brasil.time() <= hora_final):
            continue
        resultado.append(pulso)
    return resultado


# Limiares de qualidade de GPS aprovados pelo responsavel do produto em
# 2026-08-05 (ADR-0054), respondendo a decisao de negocio que
# workforce_core.qualidade_gps deixa deliberadamente em aberto
# ("engenharia propoe, produto aprova", ver docs/70_ADR_0043... e o
# proprio modulo). Ficam aqui (fronteira de apresentacao), nao dentro de
# qualidade_gps.py - mesmo padrao ja usado para fuso_horario (dominio
# nunca embute constante de negocio, quem chama decide).
PRECISAO_MAXIMA_ACEITAVEL_METROS = 100.0
VELOCIDADE_MAXIMA_PLAUSIVEL_METROS_SEGUNDO = 50.0  # ~180 km/h, folga para deslocamento rodoviario


def reclassificar_qualidade_pulsos(pulsos: List[PulsoGps]) -> List[PulsoGps]:
    """Recalcula `PulsoGps.qualidade` de toda a sequencia usando
    `workforce_core.qualidade_gps.avaliar_pulso` e os limiares aprovados
    acima (ADR-0054).

    Nunca sobrescreve o pulso original recebido do backend - devolve uma
    lista nova (`dataclasses.replace`), mesmo espirito de "marcar, nao
    apagar" de docs/08_GPS_PULSOS_E_PRIVACIDADE.md. Recalcula a cada
    carregamento (nao existe migracao/backfill no Postgres) - por isso
    precisa rodar sobre a sequencia INTEIRA da jornada, ordenada por
    horario, antes de qualquer filtro de periodo recortar pontos e
    quebrar a nocao de "pulso anterior" usada no calculo de velocidade
    implicita entre dois pontos consecutivos.
    """
    ordenados = sorted(pulsos, key=lambda p: p.timestamp_dispositivo)
    resultado: List[PulsoGps] = []
    anterior: Optional[PulsoGps] = None
    for pulso in ordenados:
        qualidade = avaliar_pulso(
            pulso,
            anterior,
            precisao_maxima_aceitavel_metros=PRECISAO_MAXIMA_ACEITAVEL_METROS,
            velocidade_maxima_plausivel_metros_segundo=VELOCIDADE_MAXIMA_PLAUSIVEL_METROS_SEGUNDO,
        )
        resultado.append(replace(pulso, qualidade=qualidade))
        anterior = pulso
    return resultado


@dataclass(frozen=True)
class SegmentoLinhaDoTempo:
    """Um pedaco da linha do tempo ja recortado dentro de um unico dia
    calendario de Brasilia - base do grafico "o que foi feito durante a
    jornada" (ADR-0051). `minuto_inicio`/`minuto_fim` sao minutos desde
    00:00 daquele dia (0 a 1440), com fracao de minuto preservada (nao
    arredondada) para o grafico posicionar com precisao."""

    data: date
    minuto_inicio: float
    minuto_fim: float
    tipo: str
    motivo: Optional[str]


def _minuto_do_dia(momento: datetime) -> float:
    return momento.hour * 60 + momento.minute + momento.second / 60


def fatiar_linha_do_tempo_por_dia(
    intervalos: List[IntervaloClassificado],
) -> Dict[date, List[SegmentoLinhaDoTempo]]:
    """Converte a linha do tempo de uma jornada (`workforce_core.consolidacao.linha_do_tempo`,
    instantes UTC-aware vindos do backend) para o horario de Brasilia e
    fatia por dia calendario - um intervalo que atravessa a meia-noite de
    Brasilia vira 2 (ou mais) segmentos, um por dia, cada um clicado nos
    limites do proprio dia (0 a 1440 minutos).

    Devolve um dict ordenavel por data (`sorted(resultado)`) - cada valor
    e a lista de segmentos daquele dia, na ordem cronologica em que
    aconteceram (a mesma ordem de `linha_do_tempo`, preservada aqui).
    """
    por_dia: Dict[date, List[SegmentoLinhaDoTempo]] = {}
    for intervalo in intervalos:
        cursor = para_horario_brasil(intervalo.inicio)
        fim = para_horario_brasil(intervalo.fim)
        while cursor < fim:
            proximo_dia = cursor.date() + timedelta(days=1)
            inicio_proximo_dia = datetime(
                proximo_dia.year, proximo_dia.month, proximo_dia.day, tzinfo=cursor.tzinfo
            )
            fim_do_pedaco = min(fim, inicio_proximo_dia)
            minuto_fim = 1440.0 if fim_do_pedaco.date() != cursor.date() else _minuto_do_dia(fim_do_pedaco)
            por_dia.setdefault(cursor.date(), []).append(
                SegmentoLinhaDoTempo(
                    data=cursor.date(),
                    minuto_inicio=_minuto_do_dia(cursor),
                    minuto_fim=minuto_fim,
                    tipo=intervalo.tipo,
                    motivo=intervalo.motivo,
                )
            )
            cursor = fim_do_pedaco
    return por_dia


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
