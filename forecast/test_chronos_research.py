import math

import pytest

from forecast.chronos_research import causal_context, usd_quantiles, model_options


def test_context_never_reads_future_and_keeps_origin():
    prices = [10.0, 20.0, 30.0, float("nan")]
    assert causal_context(prices, 2, 2) == [math.log(20), math.log(30)]


def test_context_rejects_invalid_observed_prices():
    with pytest.raises(ValueError):
        causal_context([10.0, float("nan")], 1)


def test_quantiles_are_exponentiated_without_resorting():
    row = [math.log(x) for x in [10, 20, 30, 40, 50]]
    assert usd_quantiles([row] * 52)[0] == pytest.approx([10, 20, 30, 40, 50])
    with pytest.raises(ValueError):
        usd_quantiles([list(reversed(row))] * 52)


def test_quantiles_require_all_horizons_and_finite_values():
    with pytest.raises(ValueError):
        usd_quantiles([[1.0] * 5])
    with pytest.raises(ValueError):
        usd_quantiles([[float("nan")] * 5] * 52)


def test_chronos2_has_explicit_single_series_cpu_context_options():
    assert model_options("autogluon/chronos-2-small") == {
        "batch_size": 1,
        "context_length": 2048,
    }
    assert model_options("amazon/chronos-bolt-tiny") == {}
    with pytest.raises(ValueError):
        model_options("unknown")
