from engine.core.domain.exceptions import DomainError


class ChamberRowError(DomainError):
    """Базовый класс ошибок каморного ряда."""


class ChamberPositionError(ChamberRowError):
    """Позиции нет в ряду."""


class ChamberSpentError(ChamberRowError):
    """Камора уже отстреляна: с ней больше ничего нельзя сделать."""


class ChamberUnavailableError(ChamberRowError):
    """В ряду нет камор, подходящих для операции.

    Например: некуда добавить патрон, нечего убрать, нечего перемешать.
    """
