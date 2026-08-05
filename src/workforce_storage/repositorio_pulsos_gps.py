"""Repositorio local de pulsos GPS (Incremento 7).

Um arquivo JSON Lines (uma linha = um pulso, formato `.jsonl`) por
jornada, em vez do arquivo JSON unico usado para Jornada
(RepositorioJornadaArquivo). A escolha e deliberada: pulsos sao gravados
com alta frequencia (potencialmente um a cada 60-120s por horas, ver
docs/08_GPS_PULSOS_E_PRIVACIDADE.md), entao reescrever o arquivo inteiro a
cada gravacao (como o padrao de escrita atomica por substituicao faria)
degradaria com o tempo. Cada pulso e gravado com um `open(..., "a")` +
`flush` + `os.fsync`, e uma linha corrompida no meio do arquivo nao
compromete as demais - reflete a regra de ouro "falha de GPS nao pode
apagar eventos ja registrados" aplicada a leitura.

Ver docs/34_ADR_0007_PULSOS_GPS_QUALIDADE_E_SINCRONIZACAO_LOTE.md.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Union
from uuid import UUID

from workforce_core.entities import PulsoGps

from .serializacao import pulso_gps_de_dict, pulso_gps_para_dict


class RepositorioPulsosGpsArquivo:
    def __init__(self, diretorio: Union[str, Path]):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(parents=True, exist_ok=True)

    def _caminho(self, jornada_id: UUID) -> Path:
        return self.diretorio / f"{jornada_id}.jsonl"

    def gravar_pulso(self, pulso: PulsoGps) -> None:
        """Acrescenta um pulso ao final do arquivo da jornada.

        `flush` + `fsync` garantem que o pulso sobreviva a um fechamento
        abrupto do processo logo em seguida - o mesmo cuidado que a escrita
        atomica de RepositorioJornadaArquivo aplica de outra forma.
        """
        caminho = self._caminho(pulso.jornada_id)
        linha = json.dumps(pulso_gps_para_dict(pulso), ensure_ascii=False)
        with open(caminho, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())

    def gravar_lote(self, pulsos: List[PulsoGps]) -> None:
        """Grava varios pulsos de uma vez, um `gravar_pulso` por item.

        Existe pra este repositorio ter a mesma forma publica de
        `workforce_api.repositorio_pulsos_postgres.RepositorioPulsosGpsPostgres`
        (mesmo espirito de `RepositorioJornadaArquivo`/`RepositorioJornadaPostgres`
        - `salvar`/`carregar`/`listar_ids` identicos nos dois) - o endpoint
        `POST /pulsos` chama `gravar_lote` sem saber (nem precisar saber)
        qual das duas implementacoes esta por tras do Depends."""
        for pulso in pulsos:
            self.gravar_pulso(pulso)

    def ler_pulsos(self, jornada_id: UUID) -> List[PulsoGps]:
        """Le todos os pulsos gravados para a jornada, em ordem cronologica
        pelo timestamp do proprio dispositivo (nao pela ordem em que foram
        gravados no arquivo) - mesma garantia de
        `workforce_api.repositorio_pulsos_postgres.RepositorioPulsosGpsPostgres.ler_pulsos`,
        necessaria pra um lote reenviado fora de ordem (ou um id repetido,
        ver abaixo) nao embaralhar a trajetoria.

        Uma linha corrompida (JSON invalido ou estrutura invalida) e
        ignorada silenciosamente na leitura - nunca apaga nem reescreve o
        arquivo - mas nao interrompe a leitura das demais linhas validas.
        Para diagnostico fino de quais linhas falharam, use
        `ler_pulsos_com_erros`.
        """
        pulsos, _ = self.ler_pulsos_com_erros(jornada_id)
        return pulsos

    def ler_pulsos_com_erros(self, jornada_id: UUID) -> tuple[List[PulsoGps], List[int]]:
        caminho = self._caminho(jornada_id)
        if not caminho.exists():
            return [], []
        # Dict por id (nao lista) - `gravar_pulso`/`gravar_lote` sao so
        # append, sem checar duplicata na escrita (E de proposito, ver
        # docstring da classe: checar antes de cada gravacao reintroduziria
        # o custo de leitura que o append-only existe pra evitar). Reenviar
        # o mesmo pulso (ack perdido na sincronizacao) grava uma segunda
        # linha com o mesmo id - a leitura e que resolve o upsert, ultima
        # ocorrencia vence, mesma semantica do `ON CONFLICT ... DO UPDATE`
        # do lado Postgres.
        por_id: Dict[UUID, PulsoGps] = {}
        linhas_com_erro: List[int] = []
        with open(caminho, encoding="utf-8") as arquivo:
            for numero_linha, linha in enumerate(arquivo, start=1):
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    dados = json.loads(linha)
                    pulso = pulso_gps_de_dict(dados)
                    por_id[pulso.id] = pulso
                except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                    linhas_com_erro.append(numero_linha)
        pulsos = sorted(por_id.values(), key=lambda pulso: pulso.timestamp_dispositivo)
        return pulsos, linhas_com_erro

    def contar_pulsos(self, jornada_id: UUID) -> int:
        return len(self.ler_pulsos(jornada_id))

    def contar_pulsos_anteriores_a(self, data_limite: datetime) -> int:
        """Conta (sem apagar) quantos pulsos `apagar_pulsos_anteriores_a`
        apagaria com a mesma `data_limite` - mesmo papel do equivalente em
        `RepositorioPulsosGpsPostgres`, usado pelo modo `dry_run` do
        endpoint de expurgo (ADR-0057)."""
        total = 0
        for caminho in sorted(self.diretorio.glob("*.jsonl")):
            jornada_id = UUID(caminho.stem)
            pulsos, _ = self.ler_pulsos_com_erros(jornada_id)
            total += sum(1 for p in pulsos if _tz_aware(p.timestamp_dispositivo) < data_limite)
        return total

    def apagar_pulsos_anteriores_a(self, data_limite: datetime) -> int:
        """Mesmo papel de
        `workforce_api.repositorio_pulsos_postgres.RepositorioPulsosGpsPostgres.apagar_pulsos_anteriores_a`
        - existe para o endpoint `POST /pulsos/expurgar` funcionar igual
        nos testes (que injetam este repositorio, nao o Postgres) e em uso
        local sem backend hospedado.

        Sem coluna "recebido pelo servidor" aqui (armazenamento e so um
        `.jsonl` por jornada, sem metadado por linha) - usa
        `timestamp_dispositivo` como aproximacao. Suficiente para um
        mecanismo de limpeza local; a fonte de verdade de producao e
        sempre o Postgres, que usa o momento real de recebimento.
        """
        apagados = 0
        for caminho in sorted(self.diretorio.glob("*.jsonl")):
            jornada_id = UUID(caminho.stem)
            pulsos, _ = self.ler_pulsos_com_erros(jornada_id)
            mantidos = [p for p in pulsos if _tz_aware(p.timestamp_dispositivo) >= data_limite]
            apagados += len(pulsos) - len(mantidos)
            if len(mantidos) == len(pulsos):
                continue
            if not mantidos:
                caminho.unlink()
            else:
                linhas = "\n".join(
                    json.dumps(pulso_gps_para_dict(p), ensure_ascii=False) for p in mantidos
                )
                caminho.write_text(linhas + "\n", encoding="utf-8")
        return apagados


def _tz_aware(momento: datetime) -> datetime:
    """`data_limite` sempre chega com timezone (UTC, ver o endpoint) -
    normaliza um `timestamp_dispositivo` sem timezone (dado antigo/de
    teste) como UTC so para a comparacao, sem alterar o pulso armazenado."""
    return momento if momento.tzinfo is not None else momento.replace(tzinfo=timezone.utc)
