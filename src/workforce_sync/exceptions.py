"""Excecoes da camada de sincronizacao."""


class ErroSincronizacao(Exception):
    """Base para todas as excecoes da fila e do sincronizador."""


class RegistroNaoEncontradoError(ErroSincronizacao):
    """Nao existe registro de fila para o id de jornada informado."""


class RegistroCorrompidoError(ErroSincronizacao):
    """O registro de fila existe mas nao pode ser lido com seguranca.

    Assim como em workforce_storage, o arquivo original nunca e apagado ou
    sobrescrito automaticamente ao ser encontrado corrompido.
    """
