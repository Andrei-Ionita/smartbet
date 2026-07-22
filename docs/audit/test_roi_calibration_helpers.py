"""Tests for pure helpers in roi-calibration-2026-07-22.py."""
import importlib.util
import pathlib

import numpy as np

_MODULE_PATH = pathlib.Path(__file__).parent / 'roi-calibration-2026-07-22.py'
_spec = importlib.util.spec_from_file_location('roi_calibration', _MODULE_PATH)
_roi_calibration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roi_calibration)


def test_module_loads():
    """Sanity check: script imports and exposes the expected API."""
    for name in ['TRUE_STRINGS', 'load_universe', 'bootstrap_ci',
                 'fit_platt', 'apply_platt']:
        assert hasattr(_roi_calibration, name), f"missing {name}"


def test_bootstrap_ci_recovers_known_mean():
    """CI should contain the true mean for a known synthetic distribution."""
    rng = np.random.default_rng(0)
    values = rng.normal(loc=0.5, scale=0.1, size=500)
    result = _roi_calibration.bootstrap_ci(values, n_iter=2000, seed=42)
    assert result['ci_lo'] < 0.5 < result['ci_hi'], \
        f"CI {result} does not contain true mean 0.5"


def test_bootstrap_ci_empty_input():
    result = _roi_calibration.bootstrap_ci(np.array([]), n_iter=100)
    assert np.isnan(result['point'])
    assert np.isnan(result['ci_lo'])
    assert np.isnan(result['ci_hi'])


def test_platt_recovers_identity_on_perfect_data():
    """When confidence exactly equals empirical rate, Platt should recover
    a near-identity mapping (a≈some positive value, b such that sigmoid
    passes through 0.5 at confidence≈0.5)."""
    rng = np.random.default_rng(0)
    # Generate 500 rows: confidence uniform in [0.4, 0.9], outcome ~ Bernoulli(confidence)
    conf = rng.uniform(0.4, 0.9, size=500)
    outcomes = rng.binomial(1, conf).astype(float)
    a, b = _roi_calibration.fit_platt(conf, outcomes)
    # apply_platt at conf=0.5 should be roughly 0.5 (well-calibrated)
    result = _roi_calibration.apply_platt(np.array([0.5]), a, b)
    assert 0.35 < result[0] < 0.65, \
        f"expected calibrated(0.5) ~ 0.5, got {result[0]}"


def test_platt_corrects_overconfidence():
    """When confidence is systematically higher than actual outcomes,
    Platt should map confidence DOWN toward the empirical rate."""
    rng = np.random.default_rng(1)
    # 500 rows: confidence uniform 0.6-0.8, but actual win rate only 0.5
    conf = rng.uniform(0.6, 0.8, size=500)
    outcomes = rng.binomial(1, 0.5, size=500).astype(float)
    a, b = _roi_calibration.fit_platt(conf, outcomes)
    # Calibrated version of 0.7 should be lower than 0.7
    result = _roi_calibration.apply_platt(np.array([0.7]), a, b)
    assert result[0] < 0.7, \
        f"expected calibration to correct overconfidence, got {result[0]}"


def test_apply_platt_bounded_in_zero_one():
    """Regardless of inputs, output should be in [0, 1]."""
    conf = np.linspace(0.0, 1.0, 20)
    result = _roi_calibration.apply_platt(conf, a=5.0, b=-2.0)
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_brier_score_perfect_prediction():
    """Perfect predictions (prob=1 when outcome=1, prob=0 when outcome=0)
    have Brier score 0."""
    probs = np.array([1.0, 0.0, 1.0, 0.0])
    outcomes = np.array([1, 0, 1, 0])
    assert _roi_calibration.brier_score(probs, outcomes) == 0.0


def test_brier_score_worst_prediction():
    """Worst predictions (prob=0 when outcome=1) have Brier score 1."""
    probs = np.array([0.0, 1.0, 0.0, 1.0])
    outcomes = np.array([1, 0, 1, 0])
    assert _roi_calibration.brier_score(probs, outcomes) == 1.0


def test_brier_score_uniform_half():
    """Prob=0.5 with outcome-agnostic gives Brier 0.25."""
    probs = np.array([0.5, 0.5, 0.5, 0.5])
    outcomes = np.array([1, 0, 1, 0])
    assert abs(_roi_calibration.brier_score(probs, outcomes) - 0.25) < 1e-9


def test_ece_perfect_calibration():
    """When mean predicted == mean actual in each bin, ECE is 0."""
    # 100 predictions at prob 0.6, half win (matches predicted rate)
    probs = np.full(100, 0.6)
    outcomes = np.array([1] * 60 + [0] * 40)
    result = _roi_calibration.ece(probs, outcomes, n_bins=10)
    assert result < 0.05  # near-zero (may be tiny due to binning)


def test_ece_maximally_miscalibrated():
    """Prob=0.9 but actual rate 0.1 → ECE ≈ 0.8."""
    probs = np.full(100, 0.9)
    outcomes = np.array([1] * 10 + [0] * 90)
    result = _roi_calibration.ece(probs, outcomes, n_bins=10)
    assert 0.75 < result < 0.85
