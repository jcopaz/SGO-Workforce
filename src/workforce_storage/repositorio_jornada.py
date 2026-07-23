"""Repositorio de jornadas em arquivo local (Incremento 2).

Cada jornada e gravada em um arquivo JSON proprio, nomeado pelo UUID da
jornada. A escrita e atomica (grava em arquivo temporario e substitui o
arquivo final com os.replace) para que um processo interrompido no meio da
gravacao nunca deixe um arquivo de estado parcialmente escrito no lugar do
anterior.

Politica de retencao apos sincronizacao e formato definitivo de
serializacao sao decisoes provisorias - ver
docs/29_ADR_0002_PERSISTENCIA_LOCAL_PROVISORIA.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union
from uuid import UUID

from workforce_core.engine import MotorJornada
from workforce_core.entities import Jornada
from workforce_core.enums import EstadoJornada
from workforce_core.exceptions import ErroDominio

from .exceptions import ArquivoCorrompidoError, JornadaNaoEncontradaError
from .serializacao import jornada_de_dict, jornada_para_dict


class RepositorioJornadaArquivo:
    def __init__(self, diretorio: Union[str, Path]):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(parents=True, exist_ok=True)

    def _caminho(self, jornada_id: UUID) -> Path:
        return self.diretorio / f"{jornada_id}.json"

    def salvar(self, jornada: Jornada) -> None:
        """Grava o estado atual da jornada de forma atomica.

        Chamar apos cada transicao (inicio/fim de jornada, atividade ou
        pausa) garante que um fechamento abrupto do aplicativo perca, no
        maximo, o evento em andamento no instante da falha - nunca os
        eventos ja confirmados.
        """
        caminho = self._caminho(jornada.id)
        tmp = caminho.with_name(caminho.name + ".tmp")
        dados = jornada_para_dict(jornada)
        tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(caminho)

    def carregar(self, jornada_id: UUID) -> Jornada:
        """Le e reconstroi a Jornada persistida.

        Nunca apaga nem sobrescreve o arquivo original em caso de erro: se
        o conteudo nao puder ser lido com seguranca, levanta
        ArquivoCorrompidoError e deixa o arquivo intacto para inspecao ou
        recuperacao manual.
        """
        caminho = self._caminho(jornada_id)
        if not caminho.exists():
            raise JornadaNaoEncontradaError(
                f"Nao existe jornada persistida com id {jornada_id}."
            )
        texto = caminho.read_text(encoding="utf-8")
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ArquivoCorrompidoError(
                f"Arquivo de jornada corrompido (JSON invalido): {caminho}"
            ) from exc
        try:
            return jornada_de_dict(dados)
        except (KeyError, ValueError, TypeError) as exc:
            raise ArquivoCorrompidoError(
                f"Arquivo de jornada com estrutura invalida: {caminho}"
            ) from exc

    def carregar_motor(self, jornada_id: UUID) -> MotorJornada:
        """Recupera um MotorJornada pronto para uso a partir do disco.

        Alem dos erros de leitura de carregar(), propaga
        EstadoInconsistenteError (de workforce_core) se o conteudo violar as
        invariantes do dominio - por exemplo, duas atividades ativas.
        """
        jornada = self.carregar(jornada_id)
        try:
            return MotorJornada.a_partir_de(jornada)
        except ErroDominio as exc:
            raise ArquivoCorrompidoError(
                f"Jornada {jornada_id} persistida em estado inconsistente: {exc}"
            ) from exc

    def listar_ids(self) -> List[UUID]:
        """Lista os ids de jornada a partir dos arquivos `<uuid>.json` do diretorio.

        Um arquivo `.json` cujo nome nao e um UUID valido (por exemplo, um
        arquivo estranho ao repositorio, colocado manualmente ou por outra
        ferramenta) e ignorado em vez de derrubar a listagem inteira -
        mesma disciplina de resiliencia usada em carregar()/listar_abertas()
        para arquivos corrompidos.
        """
        ids: List[UUID] = []
        for caminho in self.diretorio.glob("*.json"):
            try:
                ids.append(UUID(caminho.stem))
            except ValueError:
                continue
        return ids

    def listar_abertas(self) -> List[Jornada]:
        """Retorna as jornadas com estado ABERTA, para recuperacao apos reinicio.

        Arquivos corrompidos sao ignorados aqui (nao interrompem a listagem
        das demais jornadas), mas o arquivo problematico nao e alterado nem
        removido - use carregar() diretamente sobre o id para diagnosticar.
        """
        abertas: List[Jornada] = []
        for jornada_id in self.listar_ids():
            try:
                jornada = self.carregar(jornada_id)
            except ArquivoCorrompidoError:
                continue
            if jornada.estado == EstadoJornada.ABERTA:
                abertas.append(jornada)
        return abertas

    def excluir(self, jornada_id: UUID) -> None:
        caminho = self._caminho(jornada_id)
        if caminho.exists():
            caminho.unlink()
