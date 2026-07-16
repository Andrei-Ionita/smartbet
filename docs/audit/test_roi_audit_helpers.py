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
