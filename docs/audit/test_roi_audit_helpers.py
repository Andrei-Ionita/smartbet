"""Tests for pure helper functions in roi-audit-2026-07-16.py."""
import importlib.util
import pathlib

import numpy as np
import pytest

_MODULE_PATH = pathlib.Path(__file__).parent / 'roi-audit-2026-07-16.py'
_spec = importlib.util.spec_from_file_location('roi_audit', _MODULE_PATH)
_roi_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roi_audit)


def test_module_loads():
    """Sanity check that the audit script is importable."""
    assert hasattr(_roi_audit, 'load_and_filter')
    assert hasattr(_roi_audit, 'q1_sample_size')
    assert hasattr(_roi_audit, 'q1_gate')


def test_bootstrap_ci_recovers_known_mean():
    """CI should contain the true mean for a known synthetic distribution."""
    rng = np.random.default_rng(0)
    # 500 bets with mean profit_loss_10 = +1.0 (i.e., 10% ROI at $10 stake)
    profits = rng.normal(loc=1.0, scale=8.0, size=500)
    result = _roi_audit.q2_bootstrap_ci(profits, n_iter=2000, seed=42)
    assert 'point_roi_pct' in result
    assert 'ci_lo' in result and 'ci_hi' in result
    # True ROI is 10%. CI should straddle it.
    assert result['ci_lo'] < 10.0 < result['ci_hi'], f"CI {result} does not contain true ROI"


def test_bootstrap_ci_empty_input():
    """Empty input should return NaN cleanly, not crash."""
    result = _roi_audit.q2_bootstrap_ci(np.array([]), n_iter=100)
    assert np.isnan(result['point_roi_pct'])
    assert np.isnan(result['ci_lo'])
    assert np.isnan(result['ci_hi'])
