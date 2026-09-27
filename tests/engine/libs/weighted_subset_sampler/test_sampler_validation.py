"""Проверка границ контракта через публичный интерфейс."""

import math
from collections.abc import Callable
from random import Random

import pytest

from engine.libs.weighted_subset_sampler import (
    sample_weighted_mask,
    sample_weighted_subset,
)
from engine.libs.weighted_subset_sampler._exceptions import (
    SamplingError,
    SamplingSizeError,
    SamplingSubsetSizeError,
    SamplingWeightError,
)
from engine.libs.weighted_subset_sampler._limits import MAX_SIZE, MAX_WEIGHT

Sampler = Callable[..., object]
SAMPLERS = pytest.mark.parametrize(
    "sample",
    [sample_weighted_subset, sample_weighted_mask],
    ids=["subset", "mask"],
)

MIN_WEIGHT = 1 / MAX_WEIGHT


# --------------------------------------------------------------------------- #
# Иерархия исключений
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "error", [SamplingSizeError, SamplingWeightError, SamplingSubsetSizeError]
)
def test_errors_share_base_and_are_value_errors(error: type[Exception]) -> None:
    assert issubclass(error, SamplingError)
    assert issubclass(error, ValueError)


# --------------------------------------------------------------------------- #
# Размер набора весов
# --------------------------------------------------------------------------- #


@SAMPLERS
def test_empty_weights_rejected(sample: Sampler) -> None:
    with pytest.raises(SamplingSizeError):
        sample([], 0, Random(0))


@SAMPLERS
def test_max_size_accepted(sample: Sampler) -> None:
    sample([1.0] * MAX_SIZE, 1, Random(0))


@SAMPLERS
def test_above_max_size_rejected(sample: Sampler) -> None:
    with pytest.raises(SamplingSizeError):
        sample([1.0] * (MAX_SIZE + 1), 1, Random(0))


# --------------------------------------------------------------------------- #
# Значения весов
# --------------------------------------------------------------------------- #


@SAMPLERS
@pytest.mark.parametrize("weight", [MIN_WEIGHT, 1.0, float(MAX_WEIGHT)])
def test_boundary_weights_accepted(sample: Sampler, weight: float) -> None:
    sample([weight, 1.0, 1.0], 1, Random(0))


@SAMPLERS
@pytest.mark.parametrize(
    "weight",
    [
        math.nextafter(MIN_WEIGHT, 0.0),
        math.nextafter(float(MAX_WEIGHT), math.inf),
        0.0,
        -1.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
    ids=["below-min", "above-max", "zero", "negative", "inf", "-inf", "nan"],
)
@pytest.mark.parametrize("position", [0, 1, 2])
def test_out_of_range_weight_rejected(
    sample: Sampler, weight: float, position: int
) -> None:
    weights = [1.0, 1.0, 1.0]
    weights[position] = weight
    with pytest.raises(SamplingWeightError, match=f"weight at {position}"):
        sample(weights, 1, Random(0))


@SAMPLERS
def test_bad_weight_rejected_even_when_k_is_zero(sample: Sampler) -> None:
    with pytest.raises(SamplingWeightError):
        sample([1.0, 0.0], 0, Random(0))


# --------------------------------------------------------------------------- #
# Размер выборки k
# --------------------------------------------------------------------------- #


@SAMPLERS
@pytest.mark.parametrize("k", [-1, 4, 100])
def test_k_out_of_range_rejected(sample: Sampler, k: int) -> None:
    with pytest.raises(SamplingSubsetSizeError):
        sample([1.0, 2.0, 3.0], k, Random(0))


@SAMPLERS
def test_size_checked_before_k(sample: Sampler) -> None:
    """При пустом наборе виноват набор, а не k."""
    with pytest.raises(SamplingSizeError):
        sample([], 5, Random(0))


@SAMPLERS
def test_failed_validation_does_not_touch_rng(sample: Sampler) -> None:
    rng = Random(0)
    state = rng.getstate()
    with pytest.raises(SamplingError):
        sample([1.0, 2.0], 3, rng)
    assert rng.getstate() == state
