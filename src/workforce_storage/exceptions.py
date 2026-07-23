"""Excecoes da camada de persistencia local."""


class ErroPersistencia(Exception):
    """Base para todas as excecoes da camada de persistencia."""


class ArquivoCorrompidoError(ErroPersistencia):
    """O arquivo de estado existe mas nao pode ser lido com seguranca.

    Cobre tanto JSON sintaticamente invalido quanto uma estrutura que nao
    corresponde ao contrato esperado. Em nenhum dos dois casos o arquivo
    original e apagado ou sobrescrito automaticamente - a regra de ouro
    "falha nao pode apagar dados ja registrados" (CLAUDE.md) tambem se
    aplica aqui.
    """


class JornadaNaoEncontradaError(ErroPersistencia):
    """Nao existe arquivo de estado para o identificador de jornada informado."""
