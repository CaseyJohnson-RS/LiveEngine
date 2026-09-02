from engine.core.domain.exceptions import DomainError


class PlayerError(DomainError):
    """Базовый класс ошибок модуля."""


class PlayerStateError(PlayerError):
    """Действие не соотносится с текущим состоянием игрока."""


class PlayerArgumentError(PlayerError):
    """Ошибка аргумента функции."""
