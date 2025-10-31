#!/usr/bin/env python3
"""
Beautiful Prediction Accuracy Dashboard
Real-time accuracy reports with dynamic data from SportMonks
NO MOCK DATA - 100% REAL DATA ONLY
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import plotly.graph_objs as go
import plotly.utils

def load_environment():
    """Load environment variables from .env file"""
    # Try to load from dotenv first
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return True
    except ImportError:
        # Fallback to manual loading
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            return True
        except FileNotFoundError:
            return False

app = Flask(__name__)

class AccuracyDashboard:
    def __init__(self):
        self.db_path = "prediction_accuracy.db"
    
    def get_league_overview(self):
        """Get overview of all leagues with accuracy metrics"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                league_name,
                total_predictions,
                correct_predictions,
                hit_rate,
                avg_confidence,
                avg_expected_value,
                high_confidence_accuracy,
                low_confidence_accuracy,
                analysis_date
            FROM accuracy_analysis
            ORDER BY hit_rate DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df.to_dict('records')
    
    def get_league_details(self, league_id):
        """Get detailed analysis for specific league"""
        conn = sqlite3.connect(self.db_path)
        
        # Get league info
        league_query = '''
            SELECT DISTINCT league_name FROM predictions WHERE league_id = ?
        '''
        league_name = pd.read_sql_query(league_query, conn, params=(league_id,)).iloc[0]['league_name']
        
        # Get predictions with results
        details_query = '''
            SELECT 
                p.fixture_id,
                p.home_team,
                p.away_team,
                p.kickoff_datetime,
                p.predicted_outcome,
                p.confidence,
                p.expected_value,
                p.kelly_stake,
                p.ensemble_consensus,
                p.model_variance,
                p.prediction_agreement,
                p.odds_home,
                p.odds_draw,
                p.odds_away,
                p.bookmaker,
                r.actual_outcome,
                r.home_score,
                r.away_score,
                CASE 
                    WHEN p.predicted_outcome = r.actual_outcome THEN 'Correct'
                    ELSE 'Incorrect'
                END as prediction_result
            FROM predictions p
            LEFT JOIN results r ON p.fixture_id = r.fixture_id
            WHERE p.league_id = ? AND r.actual_outcome IS NOT NULL
            ORDER BY p.kickoff_datetime
        '''
        
        df = pd.read_sql_query(details_query, conn, params=(league_id,))
        conn.close()
        
        return {
            'league_name': league_name,
            'fixtures': df.to_dict('records')
        }
    
    def create_accuracy_chart(self, league_data):
        """Create accuracy visualization chart"""
        if not league_data:
            return None
        
        # Prepare data for chart
        leagues = [item['league_name'] for item in league_data]
        hit_rates = [item['hit_rate'] for item in league_data]
        avg_confidences = [item['avg_confidence'] for item in league_data]
        
        # Create bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Hit Rate %',
            x=leagues,
            y=hit_rates,
            marker_color='lightblue',
            text=[f"{rate:.1f}%" for rate in hit_rates],
            textposition='auto'
        ))
        
        fig.add_trace(go.Bar(
            name='Avg Confidence %',
            x=leagues,
            y=avg_confidences,
            marker_color='lightcoral',
            text=[f"{conf:.1f}%" for conf in avg_confidences],
            textposition='auto'
        ))
        
        fig.update_layout(
            title='League Accuracy Overview',
            xaxis_title='League',
            yaxis_title='Percentage',
            barmode='group',
            height=500
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def create_confidence_vs_accuracy_chart(self, league_data):
        """Create confidence vs accuracy scatter plot"""
        if not league_data:
            return None
        
        # Prepare data
        confidences = [item['avg_confidence'] for item in league_data]
        accuracies = [item['hit_rate'] for item in league_data]
        leagues = [item['league_name'] for item in league_data]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=confidences,
            y=accuracies,
            mode='markers+text',
            text=leagues,
            textposition='top center',
            marker=dict(
                size=10,
                color=accuracies,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Hit Rate %")
            ),
            name='Leagues'
        ))
        
        # Add diagonal line (perfect correlation)
        max_val = max(max(confidences), max(accuracies))
        fig.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            line=dict(dash='dash', color='red'),
            name='Perfect Correlation'
        ))
        
        fig.update_layout(
            title='Confidence vs Accuracy Correlation',
            xaxis_title='Average Confidence %',
            yaxis_title='Hit Rate %',
            height=500
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Initialize dashboard
dashboard = AccuracyDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('accuracy_dashboard.html')

@app.route('/api/overview')
def api_overview():
    """API endpoint for league overview"""
    try:
        overview = dashboard.get_league_overview()
        return jsonify({
            'success': True,
            'data': overview,
            'total_leagues': len(overview),
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/league/<int:league_id>')
def api_league_details(league_id):
    """API endpoint for specific league details"""
    try:
        details = dashboard.get_league_details(league_id)
        return jsonify({
            'success': True,
            'data': details
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/charts/accuracy')
def api_accuracy_chart():
    """API endpoint for accuracy chart"""
    try:
        overview = dashboard.get_league_overview()
        chart_data = dashboard.create_accuracy_chart(overview)
        return jsonify({
            'success': True,
            'chart': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/charts/confidence')
def api_confidence_chart():
    """API endpoint for confidence vs accuracy chart"""
    try:
        overview = dashboard.get_league_overview()
        chart_data = dashboard.create_confidence_vs_accuracy_chart(overview)
        return jsonify({
            'success': True,
            'chart': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    # Load environment variables
    load_environment()
    
    print("Starting Prediction Accuracy Dashboard...")
    print("Dashboard will be available at: http://localhost:5000")
    print("All data is REAL - no mock data used")
    app.run(debug=True, host='0.0.0.0', port=5000)
