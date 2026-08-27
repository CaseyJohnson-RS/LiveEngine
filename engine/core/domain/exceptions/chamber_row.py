from engine.core.domain.exceptions import DomainError


class ChamberError(DomainError):
    """Базовый класс ошибок модуля."""


class ChamberStateError(ChamberError):
    """Неверный переход состояния."""


class ChamberRowError(ChamberError):
    """Ошибка выполнения операции."""
