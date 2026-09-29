from enum import Enum


class PreparationPhase(Enum):
    """Фаза подготовки

    `DEALING`  — выдача предметов: игроки выбирают руку; \\
    `PLACING`  — раскладка фишек по каморам;
    """

    DEALING = 0
    PLACING = 1
