from engine.core.domain.exceptions import DomainError


class PartyError(DomainError):
    """Базовый класс ошибок модуля."""


class PartyStateError(PartyError):
    """Ошибка состояния."""


class PartyArgumentError(PartyError):
    """Ошибка переданного аргумента."""
