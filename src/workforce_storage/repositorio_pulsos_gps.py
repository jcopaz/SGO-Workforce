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
from pathlib import Path
from typing import List, Union
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

    def ler_pulsos(self, jornada_id: UUID) -> List[PulsoGps]:
        """Le todos os pulsos gravados para a jornada, em ordem de gravacao.

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
        pulsos: List[PulsoGps] = []
        linhas_com_erro: List[int] = []
        with open(caminho, encoding="utf-8") as arquivo:
            for numero_linha, linha in enumerate(arquivo, start=1):
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    dados = json.loads(linha)
                    pulsos.append(pulso_gps_de_dict(dados))
                except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                    linhas_com_erro.append(numero_linha)
        return pulsos, linhas_com_erro

    def contar_pulsos(self, jornada_id: UUID) -> int:
        return len(self.ler_pulsos(jornada_id))
