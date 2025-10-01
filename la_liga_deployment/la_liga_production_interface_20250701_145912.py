#!/usr/bin/env python3
"""
LA LIGA PRODUCTION INTERFACE
Generated: 20250701_145912
Performance: 74.4% hit rate, 138.92% ROI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from LOCKED_PRODUCTION_la_liga_production_ready import LaLigaProductionPredictor

class SafeLaLigaInterface:
    def __init__(self):
        self.predictor = LaLigaProductionPredictor()
        self.verify_production_integrity()
    
    def verify_production_integrity(self):
        expected_version = "20250630_152907"
        if self.predictor.model_version != expected_version:
            raise Exception("Model version mismatch")
        print("Production integrity verified")
    
    def predict_match(self, match_data):
        return self.predictor.predict_match(match_data)
    
    def get_model_status(self):
        return {
            'model_version': self.predictor.model_version,
            'hit_rate': self.predictor.backtest_hit_rate,
            'roi': self.predictor.backtest_roi,
            'status': 'PRIMARY_PRODUCTION',
            'allocation': '70%_PRIMARY'
        }

la_liga_production = SafeLaLigaInterface()

def predict_la_liga_match(match_data):
    return la_liga_production.predict_match(match_data)

def get_production_status():
    return la_liga_production.get_model_status()

if __name__ == "__main__":
    print("La Liga Production Interface - Ready")
    status = get_production_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
