# Prediction Accuracy Tracking System

## 🎯 Overview
Real-time prediction accuracy analysis system for weekend football matches using SportMonks API data.

## ✅ Features
- **100% Real Data**: No mock or test data used
- **27 League Reports**: Individual accuracy analysis per league
- **Ensemble Analysis**: Multi-model consensus and variance tracking
- **Beautiful Dashboard**: Interactive web interface with charts
- **Dynamic Updates**: Real-time data from SportMonks API

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Ensure .env file exists with SportMonks token
echo "SPORTMONKS_API_TOKEN=your_token_here" > .env
```

### 2. Install Dependencies
```bash
pip install -r requirements_accuracy.txt
```

### 3. Run Setup
```bash
python setup_accuracy_tracking.py
```

### 4. Start Tracking
```bash
# Before weekend matches
python prediction_tracker.py

# After matches finish
python prediction_tracker.py --results
python accuracy_dashboard.py
```

## 📊 Dashboard Features

### League Overview
- Total leagues analyzed
- Average hit rate across all leagues
- Average confidence levels
- Average expected value performance

### Individual League Reports
- Hit rate per league
- Confidence vs accuracy correlation
- High confidence prediction accuracy
- Fixture-by-fixture breakdown

### Visual Analytics
- League accuracy comparison charts
- Confidence vs accuracy scatter plots
- Performance trend analysis

## 🔧 System Architecture

### Data Flow
1. **Pre-Match**: Fetch weekend fixtures from SportMonks
2. **Analysis**: Apply ensemble model to generate predictions
3. **Storage**: Store predictions in SQLite database
4. **Post-Match**: Fetch actual results from SportMonks
5. **Reporting**: Generate accuracy reports and visualizations

### Database Schema
- `predictions`: Stores ensemble predictions with confidence, EV, Kelly
- `results`: Stores actual match outcomes
- `accuracy_analysis`: Stores calculated accuracy metrics per league

## 📈 Key Metrics Tracked

### Per League
- **Hit Rate**: Correct predictions / Total predictions
- **Confidence Accuracy**: How well confidence correlates with outcomes
- **EV Performance**: Actual returns vs predicted expected value
- **Kelly Performance**: Optimal stake sizing effectiveness
- **Model Agreement**: How consensus affects accuracy

### Visual Elements
- Accuracy charts with league comparison
- Confidence distribution analysis
- EV vs outcome scatter plots
- Time series accuracy trends

## 🎨 Beautiful Reports

### Dashboard Layout
- League selector (27 leagues)
- Key metrics cards
- Interactive charts
- Detailed fixture breakdown tables

### Report Sections
1. **League Overview**: Key performance metrics
2. **Prediction Analysis**: Confidence vs accuracy correlation
3. **Fixture Breakdown**: Individual match results
4. **Model Performance**: Ensemble vs individual model accuracy
5. **Betting Intelligence**: EV and Kelly performance

## 🔍 Real Data Sources

### SportMonks API Integration
- **Fixtures**: Weekend match data
- **Predictions**: Multiple model outputs (types 233, 237, 238)
- **Odds**: Real bookmaker odds
- **Results**: Actual match outcomes

### Ensemble Analysis
- **Consensus Calculation**: Average across multiple models
- **Variance Analysis**: Model disagreement measurement
- **Agreement Assessment**: High/Medium/Low based on variance
- **Model Selection**: Most decisive prediction selection

## 🚀 Benefits

1. **Model Validation**: Test ensemble approach with real data
2. **League Insights**: Identify best-performing leagues
3. **Confidence Calibration**: Improve confidence assessment
4. **User Trust**: Transparent performance reporting
5. **Continuous Improvement**: Data-driven model refinement

## 📊 Usage Examples

### Generate Weekend Predictions
```bash
python prediction_tracker.py
```

### Fetch Results After Matches
```bash
python prediction_tracker.py --results
```

### View Beautiful Dashboard
```bash
python accuracy_dashboard.py
# Open http://localhost:5000
```

## 🔧 Configuration

### Environment Variables
- `SPORTMONKS_API_TOKEN`: Required for API access
- Database: SQLite (prediction_accuracy.db)
- Dashboard: Flask web server (port 5000)

### Customization
- Modify confidence thresholds in prediction_tracker.py
- Adjust chart styling in accuracy_dashboard.py
- Customize report templates in templates/

## 📈 Performance Monitoring

### Real-time Metrics
- Prediction accuracy by league
- Confidence calibration analysis
- Expected value performance
- Kelly Criterion effectiveness

### Historical Analysis
- Trend analysis over time
- League performance comparison
- Model agreement correlation
- Betting intelligence validation

## 🎯 Next Steps

1. **Run Setup**: Execute setup_accuracy_tracking.py
2. **Weekend Tracking**: Use prediction_tracker.py before matches
3. **Result Analysis**: Fetch results after matches complete
4. **Dashboard Review**: Analyze performance via web interface
5. **Model Improvement**: Use insights to refine ensemble approach

## 📞 Support

For issues or questions:
- Check SportMonks API token configuration
- Verify database permissions
- Review console logs for error details
- Ensure all dependencies are installed

---

**Remember: This system uses 100% real data from SportMonks API - no mock or test data!**
