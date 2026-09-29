from dataclasses import dataclass


@dataclass(frozen=True)
class RoundConfig:
    """Конфигурация раунда, которую движок вычисляет в начале подготовки.

    - `chambers`    — число камор в ряду.
    - `cartridges`  — сколько патронов получит ряд при зарядке.
    - `layers`      — слои выдачи предметов: 1 — обычный, 2 — редкий,
                      3 — потолочный. Внутренняя логика движка.

    Значения вычисляет движок, а не игрок, поэтому нарушение — баг:
    ValueError.
    """

    chambers: int
    cartridges: int
    layers: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.chambers < 1:
            raise ValueError(f"chambers must be >= 1, got {self.chambers}")
        if not (0 <= self.cartridges <= self.chambers):
            raise ValueError(
                f"cartridges must be in [0; {self.chambers}], "
                f"got {self.cartridges}"
            )
        if any(layer not in (1, 2, 3) for layer in self.layers):
            raise ValueError(f"layers must be 1, 2 or 3, got {self.layers}")
