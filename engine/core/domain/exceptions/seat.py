from engine.core.domain.exceptions import DomainError


class SeatError(DomainError):
    """Базовый класс ошибок модуля."""


class SeatStateError(SeatError):
    """Действие не соотносится с текущим состоянием."""


class SeatArgumentError(SeatError):
    """Ошибка аргумента функции."""
