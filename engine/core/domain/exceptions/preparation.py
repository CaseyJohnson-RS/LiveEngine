from engine.core.domain.exceptions import DomainError


class PreparationError(DomainError):
    """Базовый класс ошибок подготовки."""


class PreparationPhaseError(PreparationError):
    """Решение прислано не в ту фазу."""


class PreparationDecisionError(PreparationError):
    """Решение уже принято или игрок не участвует в подготовке."""


class PreparationArgumentError(PreparationError):
    """Недопустимая раскладка: не та длина или отрицательные фишки."""
