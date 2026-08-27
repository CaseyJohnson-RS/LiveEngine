from enum import Enum


class ChamberState(Enum):
    """Состояние каморы

    `EMPTY`     — патрона нет; \\
    `LOADED`    — патрон есть; \\
    `SPENT`     — камора отстреляна, содержимое израсходовано;
    """

    EMPTY = 0
    LOADED = 1
    SPENT = 2
