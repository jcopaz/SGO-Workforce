"""Conversao entre entidades de dominio (workforce_core) e dict serializavel em JSON.

Formato provisorio - ver docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md.
Mantido separado do dominio para que workforce_core nao dependa de detalhes
de formato de persistencia (arquivo local hoje, IndexedDB/API amanha).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from workforce_core.catalogo import Categoria, ClassificacaoHH, EntradaCatalogo
from workforce_core.entities import (
    Atividade,
    DadosFalha,
    EventoSecundario,
    Jornada,
    Pausa,
    PulsoGps,
)
from workforce_core.enums import (
    EstadoAtividade,
    EstadoEventoSecundario,
    EstadoJornada,
    EstadoPausa,
    QualidadePulso,
    TipoEventoSecundario,
)
from workforce_core.integracao_sgo import ReferenciaOS

# v2 adiciona eventos_secundarios (Incremento 5).
# v3 adiciona dados_falha em Atividade (Incremento 6).
# v4 adiciona os_referencia em DadosFalha (Incremento 13).
# Arquivos de versoes anteriores nao tem esses campos - jornada_de_dict e
# atividade_de_dict tratam isso com .get(..., valor_padrao) por
# compatibilidade retroativa, sem exigir migracao dos arquivos ja gravados.
FORMATO_VERSAO = 4


def _dt_para_str(valor: Optional[datetime]) -> Optional[str]:
    return valor.isoformat() if valor is not None else None


def _str_para_dt(valor: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(valor) if valor is not None else None


def pausa_para_dict(pausa: Pausa) -> Dict[str, Any]:
    return {
        "id": str(pausa.id),
        "atividade_id": str(pausa.atividade_id),
        "motivo": pausa.motivo,
        "inicio": _dt_para_str(pausa.inicio),
        "fim": _dt_para_str(pausa.fim),
        "estado": pausa.estado.value,
    }


def pausa_de_dict(dados: Dict[str, Any]) -> Pausa:
    return Pausa(
        id=UUID(dados["id"]),
        atividade_id=UUID(dados["atividade_id"]),
        motivo=dados["motivo"],
        inicio=_str_para_dt(dados["inicio"]),
        fim=_str_para_dt(dados["fim"]),
        estado=EstadoPausa(dados["estado"]),
    )


def referencia_os_para_dict(referencia: Optional[ReferenciaOS]) -> Optional[Dict[str, Any]]:
    if referencia is None:
        return None
    return {
        "numero": referencia.numero,
        "ciclo_ou_plano": referencia.ciclo_ou_plano,
        "data_importacao": _dt_para_str(referencia.data_importacao),
    }


def referencia_os_de_dict(dados: Optional[Dict[str, Any]]) -> Optional[ReferenciaOS]:
    if dados is None:
        return None
    return ReferenciaOS(
        numero=dados["numero"],
        ciclo_ou_plano=dados["ciclo_ou_plano"],
        data_importacao=_str_para_dt(dados.get("data_importacao")),
    )


def dados_falha_para_dict(dados: Optional[DadosFalha]) -> Optional[Dict[str, Any]]:
    if dados is None:
        return None
    return {
        "nota": dados.nota,
        "ativo": dados.ativo,
        "sintoma": dados.sintoma,
        "causa": dados.causa,
        "acao": dados.acao,
        "observacao": dados.observacao,
        "os_referencia": referencia_os_para_dict(dados.os_referencia),
    }


def dados_falha_de_dict(dados: Optional[Dict[str, Any]]) -> Optional[DadosFalha]:
    if dados is None:
        return None
    return DadosFalha(
        nota=dados.get("nota"),
        ativo=dados.get("ativo"),
        sintoma=dados.get("sintoma"),
        causa=dados.get("causa"),
        acao=dados.get("acao"),
        observacao=dados.get("observacao"),
        os_referencia=referencia_os_de_dict(dados.get("os_referencia")),
    )


def atividade_para_dict(atividade: Atividade) -> Dict[str, Any]:
    return {
        "id": str(atividade.id),
        "inicio": _dt_para_str(atividade.inicio),
        "fim": _dt_para_str(atividade.fim),
        "estado": atividade.estado.value,
        "pausas": [pausa_para_dict(pausa) for pausa in atividade.pausas],
        "dados_falha": dados_falha_para_dict(atividade.dados_falha),
    }


def atividade_de_dict(dados: Dict[str, Any]) -> Atividade:
    return Atividade(
        id=UUID(dados["id"]),
        inicio=_str_para_dt(dados["inicio"]),
        fim=_str_para_dt(dados["fim"]),
        estado=EstadoAtividade(dados["estado"]),
        pausas=[pausa_de_dict(p) for p in dados["pausas"]],
        dados_falha=dados_falha_de_dict(dados.get("dados_falha")),
    )


def evento_secundario_para_dict(evento: EventoSecundario) -> Dict[str, Any]:
    return {
        "id": str(evento.id),
        "tipo": evento.tipo.value,
        "motivo": evento.motivo,
        "inicio": _dt_para_str(evento.inicio),
        "fim": _dt_para_str(evento.fim),
        "estado": evento.estado.value,
    }


def evento_secundario_de_dict(dados: Dict[str, Any]) -> EventoSecundario:
    return EventoSecundario(
        id=UUID(dados["id"]),
        tipo=TipoEventoSecundario(dados["tipo"]),
        motivo=dados["motivo"],
        inicio=_str_para_dt(dados["inicio"]),
        fim=_str_para_dt(dados["fim"]),
        estado=EstadoEventoSecundario(dados["estado"]),
    )


def jornada_para_dict(jornada: Jornada) -> Dict[str, Any]:
    return {
        "formato_versao": FORMATO_VERSAO,
        "id": str(jornada.id),
        "colaborador_matricula": jornada.colaborador_matricula,
        "inicio": _dt_para_str(jornada.inicio),
        "fim": _dt_para_str(jornada.fim),
        "estado": jornada.estado.value,
        "atividades": [atividade_para_dict(a) for a in jornada.atividades],
        "eventos_secundarios": [
            evento_secundario_para_dict(e) for e in jornada.eventos_secundarios
        ],
    }


def jornada_de_dict(dados: Dict[str, Any]) -> Jornada:
    return Jornada(
        id=UUID(dados["id"]),
        colaborador_matricula=dados["colaborador_matricula"],
        inicio=_str_para_dt(dados["inicio"]),
        fim=_str_para_dt(dados["fim"]),
        estado=EstadoJornada(dados["estado"]),
        atividades=[atividade_de_dict(a) for a in dados["atividades"]],
        eventos_secundarios=[
            evento_secundario_de_dict(e) for e in dados.get("eventos_secundarios", [])
        ],
    )


def pulso_gps_para_dict(pulso: PulsoGps) -> Dict[str, Any]:
    return {
        "id": str(pulso.id),
        "jornada_id": str(pulso.jornada_id),
        "colaborador_matricula": pulso.colaborador_matricula,
        "latitude": pulso.latitude,
        "longitude": pulso.longitude,
        "precisao_metros": pulso.precisao_metros,
        "timestamp_dispositivo": _dt_para_str(pulso.timestamp_dispositivo),
        "velocidade_metros_segundo": pulso.velocidade_metros_segundo,
        "direcao_graus": pulso.direcao_graus,
        "fonte": pulso.fonte,
        "status_aplicativo": pulso.status_aplicativo,
        "bateria_percentual": pulso.bateria_percentual,
        "timestamp_recebimento_servidor": _dt_para_str(pulso.timestamp_recebimento_servidor),
        "qualidade": pulso.qualidade.value,
    }


def pulso_gps_de_dict(dados: Dict[str, Any]) -> PulsoGps:
    return PulsoGps(
        id=UUID(dados["id"]),
        jornada_id=UUID(dados["jornada_id"]),
        colaborador_matricula=dados["colaborador_matricula"],
        latitude=dados["latitude"],
        longitude=dados["longitude"],
        precisao_metros=dados["precisao_metros"],
        timestamp_dispositivo=_str_para_dt(dados["timestamp_dispositivo"]),
        velocidade_metros_segundo=dados.get("velocidade_metros_segundo"),
        direcao_graus=dados.get("direcao_graus"),
        fonte=dados.get("fonte"),
        status_aplicativo=dados.get("status_aplicativo"),
        bateria_percentual=dados.get("bateria_percentual"),
        timestamp_recebimento_servidor=_str_para_dt(dados.get("timestamp_recebimento_servidor")),
        qualidade=QualidadePulso(dados.get("qualidade", QualidadePulso.NAO_AVALIADO.value)),
    )


def entrada_catalogo_para_dict(entrada: EntradaCatalogo) -> Dict[str, Any]:
    return {
        "codigo": entrada.codigo,
        "descricao": entrada.descricao,
        "categoria": entrada.categoria.value if entrada.categoria is not None else None,
        "classificacao_hh": entrada.classificacao_hh.value,
        "tipo_registro": entrada.tipo_registro,
        "ativo": entrada.ativo,
    }


def entrada_catalogo_de_dict(dados: Dict[str, Any]) -> EntradaCatalogo:
    categoria_bruta = dados.get("categoria")
    return EntradaCatalogo(
        codigo=dados["codigo"],
        descricao=dados["descricao"],
        categoria=Categoria(categoria_bruta) if categoria_bruta else None,
        classificacao_hh=ClassificacaoHH(
            dados.get("classificacao_hh", ClassificacaoHH.NAO_DEFINIDO.value)
        ),
        tipo_registro=dados.get("tipo_registro", "pausa"),
        ativo=dados.get("ativo", True),
    )
