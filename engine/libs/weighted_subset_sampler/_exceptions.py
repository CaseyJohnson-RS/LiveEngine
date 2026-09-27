class SamplingError(ValueError):
    """Базовый класс ошибок модуля."""


class SamplingSizeError(SamplingError):
    """Число весов вне [1; MAX_SIZE]."""


class SamplingWeightError(SamplingError):
    """Вес вне [1/MAX_WEIGHT; MAX_WEIGHT]."""


class SamplingSubsetSizeError(SamplingError):
    """k вне [0; n]."""
