"""Tests for pure helper functions in roi-tuning-2026-07-20.py."""
import importlib.util
import pathlib

import numpy as np

_MODULE_PATH = pathlib.Path(__file__).parent / 'roi-tuning-2026-07-20.py'
_spec = importlib.util.spec_from_file_location('roi_tuning', _MODULE_PATH)
_roi_tuning = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roi_tuning)


def test_module_loads():
    """Sanity check that the tuning script is importable with expected API."""
    assert hasattr(_roi_tuning, 'load_universe')
    assert hasattr(_roi_tuning, 'bootstrap_ci')
    assert hasattr(_roi_tuning, 'classify_verdict')


def test_bootstrap_ci_recovers_known_mean():
    """CI should contain the true mean for a known synthetic distribution."""
    rng = np.random.default_rng(0)
    profits = rng.normal(loc=1.0, scale=8.0, size=500)
    result = _roi_tuning.bootstrap_ci(profits, n_iter=2000, seed=42)
    assert result['ci_lo'] < 10.0 < result['ci_hi']


def test_classify_verdict_ship():
    assert _roi_tuning.classify_verdict(ci_lo=2.0, point=8.0, n=150) == 'SHIP'


def test_classify_verdict_investigate():
    assert _roi_tuning.classify_verdict(ci_lo=-2.0, point=5.0, n=150) == 'INVESTIGATE'


def test_classify_verdict_discard():
    assert _roi_tuning.classify_verdict(ci_lo=-2.0, point=0.5, n=150) == 'DISCARD'


def test_classify_verdict_ship_needs_sample():
    # Point + CI look great but n too low.
    assert _roi_tuning.classify_verdict(ci_lo=2.0, point=8.0, n=50) == 'INVESTIGATE'
