"""Конфигурация раунда `RoundConfig`: допустимые значения."""

import dataclasses

import pytest

from engine.core.domain.exceptions import DomainError
from engine.core.domain.value_objects import RoundConfig


def test_valid_config_stored() -> None:
    config = RoundConfig(chambers=8, cartridges=2, layers=(1, 1, 2))
    assert config.chambers == 8
    assert config.cartridges == 2
    assert config.layers == (1, 1, 2)


@pytest.mark.parametrize("cartridges", [0, 4])
def test_boundary_cartridges_accepted(cartridges: int) -> None:
    RoundConfig(chambers=4, cartridges=cartridges, layers=())


def test_empty_layers_accepted() -> None:
    assert RoundConfig(chambers=1, cartridges=0, layers=()).layers == ()


@pytest.mark.parametrize(
    ("chambers", "cartridges", "layers"),
    [
        (0, 0, ()),
        (-1, 0, ()),
        (4, -1, ()),
        (4, 5, ()),
        (4, 1, (0,)),
        (4, 1, (1, 4)),
    ],
    ids=[
        "no-chambers",
        "negative-chambers",
        "negative-cartridges",
        "too-many-cartridges",
        "layer-zero",
        "layer-four",
    ],
)
def test_invalid_config_is_engine_bug(
    chambers: int, cartridges: int, layers: tuple[int, ...]
) -> None:
    with pytest.raises(ValueError) as info:
        RoundConfig(chambers=chambers, cartridges=cartridges, layers=layers)
    assert not isinstance(info.value, DomainError)


def test_frozen_and_equal_by_value() -> None:
    config = RoundConfig(chambers=4, cartridges=1, layers=(1,))
    same = RoundConfig(chambers=4, cartridges=1, layers=(1,))
    assert config == same
    assert len({config, same}) == 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.chambers = 5  # type: ignore[misc]
