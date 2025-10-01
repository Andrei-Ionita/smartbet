#!/usr/bin/env python3
"""
SMARTBET FASTAPI PREDICTION ENDPOINTS
====================================

FastAPI routes for live prediction system that integrates with
the existing Django backend and provides new multi-league prediction
capabilities.

Compatible with existing Django API structure:
- Extends Django endpoints without conflicts
- Uses same data models and serialization format
- Maintains existing frontend compatibility
- Adds new multi-league prediction features

New endpoints:
- POST /api/predict/        # Multi-league prediction
- POST /api/predict/batch/  # Batch predictions
- GET  /api/predict/status/ # Model status across all leagues
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Import our prediction engine
try:
    from prediction_engine import PredictionEngine
except ImportError as e:
    print(f"⚠️ Warning: Could not import prediction_engine: {e}")
    print("💡 Make sure prediction_engine.py is in the same directory")
    PredictionEngine = None

# Pydantic models for request/response validation
class MatchPredictionRequest(BaseModel):
    """Single match prediction request."""
    league: str = Field(..., description="League name (e.g., 'La Liga', 'Serie A', 'Bundesliga')")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    home_win_odds: float = Field(..., gt=1.0, le=50.0, description="Home win betting odds")
    draw_odds: float = Field(..., gt=1.0, le=20.0, description="Draw betting odds")
    away_win_odds: float = Field(..., gt=1.0, le=50.0, description="Away win betting odds")
    
    # Optional league-specific features
    home_recent_form: Optional[float] = Field(None, description="Home team recent form")
    away_recent_form: Optional[float] = Field(None, description="Away team recent form")
    home_avg_goals_for: Optional[float] = Field(None, description="Home team average goals scored")
    away_avg_goals_for: Optional[float] = Field(None, description="Away team average goals scored")
    home_win_rate: Optional[float] = Field(None, description="Home team win rate")
    away_win_rate: Optional[float] = Field(None, description="Away team win rate")
    home_goals_for: Optional[float] = Field(None, description="Home team goals scored per game")
    home_goals_against: Optional[float] = Field(None, description="Home team goals conceded per game")
    away_goals_for: Optional[float] = Field(None, description="Away team goals scored per game")
    away_goals_against: Optional[float] = Field(None, description="Away team goals conceded per game")
    recent_form_diff: Optional[float] = Field(None, description="Recent form difference")

class MatchInsights(BaseModel):
    """Match insights and analysis."""
    home_win_rate: Optional[str] = Field(None, description="Home team win rate")
    away_win_rate: Optional[str] = Field(None, description="Away team win rate")
    home_recent_form: Optional[str] = Field(None, description="Home team recent form display")
    away_recent_form: Optional[str] = Field(None, description="Away team recent form display")
    home_attack: Optional[str] = Field(None, description="Home team attacking stats")
    home_defense: Optional[str] = Field(None, description="Home team defensive stats")
    away_attack: Optional[str] = Field(None, description="Away team attacking stats")
    away_defense: Optional[str] = Field(None, description="Away team defensive stats")
    recent_form_diff: Optional[str] = Field(None, description="Recent form difference")
    market_efficiency: Optional[str] = Field(None, description="Market efficiency")
    bookmaker_margin: Optional[str] = Field(None, description="Bookmaker margin")
    home_implied_prob: Optional[str] = Field(None, description="Home team implied probability")
    draw_implied_prob: Optional[str] = Field(None, description="Draw implied probability")
    away_implied_prob: Optional[str] = Field(None, description="Away team implied probability")
    most_likely_outcome: Optional[str] = Field(None, description="Most likely outcome by odds")
    win_rate_diff: Optional[str] = Field(None, description="Win rate difference")
    expected_value: str = Field(..., description="Expected value calculation")
    alerts: List[str] = Field(..., description="Important alerts and insights")

class BatchPredictionRequest(BaseModel):
    """Batch prediction request for multiple matches."""
    matches: List[MatchPredictionRequest] = Field(..., description="List of matches to predict")

class PredictionResponse(BaseModel):
    """Single prediction response."""
    prediction_available: bool = Field(..., description="Whether prediction is available for this league")
    is_supported_league: bool = Field(..., description="Whether this league is supported")
    league: str = Field(..., description="League name")
    match_id: str = Field(..., description="Match identifier")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    
    # Fields for supported leagues only
    predicted_outcome: Optional[str] = Field(None, description="Predicted outcome: 'Home Win', 'Away Win', or 'Draw'")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Prediction confidence (0-1)")
    predicted_odds: Optional[float] = Field(None, description="Odds for predicted outcome")
    ev: Optional[float] = Field(None, description="Expected value")
    ev_positive: Optional[bool] = Field(None, description="Whether expected value is positive")
    explanation: Optional[str] = Field(None, description="Natural language explanation of the prediction")
    recommend: Optional[bool] = Field(None, description="Whether to recommend betting")
    recommendation_reason: Optional[str] = Field(None, description="Explanation for recommendation")
    
    all_probabilities: Optional[Dict[str, float]] = Field(None, description="Probabilities for all outcomes")
    all_odds: Optional[Dict[str, float]] = Field(None, description="All betting odds")
    model_info: Optional[Dict[str, Any]] = Field(None, description="Model performance and configuration")
    
    # Fields for unsupported leagues
    reason: Optional[str] = Field(None, description="Reason why prediction is not available")
    
    # Common fields
    timestamp: str = Field(..., description="Prediction timestamp")
    reasoning: Optional[str] = Field(None, description="Natural language explanation of the prediction")
    insights: Optional[MatchInsights] = Field(None, description="Detailed match insights and analysis")

class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""
    predictions: List[PredictionResponse]
    summary: Dict[str, Any] = Field(..., description="Batch prediction summary")

class ModelStatusResponse(BaseModel):
    """Model status response."""
    leagues: Dict[str, Dict[str, Any]] = Field(..., description="Status for each league model")
    system_status: str = Field(..., description="Overall system status")
    total_leagues: int = Field(..., description="Number of supported leagues")
    timestamp: str = Field(..., description="Status check timestamp")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")

# Initialize FastAPI app
app = FastAPI(
    title="SmartBet Live Prediction API",
    description="Multi-league sports betting prediction API supporting Premier League, La Liga, Serie A, Bundesliga, and Ligue 1",
    version="1.0.0",
    docs_url="/api/predict/docs",
    redoc_url="/api/predict/redoc"
)

# CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize prediction engine globally
prediction_engine = None
engine_error = None

@app.on_event("startup")
async def startup_event():
    """Initialize prediction engine on startup."""
    global prediction_engine, engine_error
    
    print("🚀 STARTING SMARTBET PREDICTION API")
    print("=" * 35)
    
    try:
        if PredictionEngine is None:
            raise ImportError("PredictionEngine class not available")
        
        prediction_engine = PredictionEngine()
        print("✅ Prediction engine initialized successfully")
        print(f"🎯 Supporting {len(prediction_engine.model_mapper.leagues)} leagues")
        
    except Exception as e:
        engine_error = str(e)
        print(f"❌ Failed to initialize prediction engine: {e}")
        print("⚠️ API will run in limited mode")

@app.get("/api/predict/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Get status of all league models.
    
    Returns information about available models, their performance,
    and current system status.
    """
    
    if prediction_engine is None:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction engine not available: {engine_error}"
        )
    
    try:
        leagues_status = {}
        total_loaded = 0
        
        for league_key, config in prediction_engine.model_mapper.leagues.items():
            try:
                # Check if model is loadable
                model = prediction_engine._get_model(league_key)
                is_loaded = True
                total_loaded += 1
                error_msg = None
            except Exception as e:
                is_loaded = False
                error_msg = str(e)
            
            leagues_status[league_key] = {
                "name": league_key.replace('_', ' ').title(),
                "status": config['status'],
                "performance": config['performance'],
                "confidence_threshold": config['confidence_threshold'],
                "odds_threshold": config['odds_threshold'],
                "model_file": config['model_file'],
                "is_loaded": is_loaded,
                "error": error_msg
            }
        
        system_status = "healthy" if total_loaded > 0 else "degraded"
        
        return ModelStatusResponse(
            leagues=leagues_status,
            system_status=system_status,
            total_leagues=len(prediction_engine.model_mapper.leagues),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.post("/api/predict", response_model=PredictionResponse)
async def predict_match(request: MatchPredictionRequest):
    """
    Predict outcome for a single match.
    
    Automatically identifies the correct model based on league,
    applies confidence and value betting filters, and returns
    structured prediction with betting recommendation.
    
    For unsupported leagues, returns a clear message indicating
    the league is not yet supported for predictions.
    """
    
    if prediction_engine is None:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction engine not available: {engine_error}"
        )
    
    try:
        # Convert Pydantic model to dict
        match_data = request.dict(exclude_unset=True)
        
        # Make prediction
        result = prediction_engine.predict_match(match_data)
        
        # Convert to response model
        return PredictionResponse(**result)
        
    except ValueError as e:
        # Handle input validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        # Handle missing model files
        raise HTTPException(status_code=404, detail=f"Model not found: {str(e)}")
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/api/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """
    Predict outcomes for multiple matches.
    
    Handles mixed leagues by:
    - Processing only supported leagues
    - Returning all matches with clear prediction status
    - Providing summary statistics for supported vs unsupported matches
    
    For unsupported leagues in the batch, returns clear messages
    indicating those leagues are not yet supported.
    """
    
    if prediction_engine is None:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction engine not available: {engine_error}"
        )
    
    try:
        # Convert Pydantic models to dicts
        matches_data = [match.dict(exclude_unset=True) for match in request.matches]
        
        # Make batch predictions
        results = prediction_engine.predict_batch(matches_data)
        
        # Convert to response models
        predictions = [PredictionResponse(**result) for result in results]
        
        # Calculate summary statistics
        total_matches = len(predictions)
        supported_matches = len([p for p in predictions if p.prediction_available])
        unsupported_matches = total_matches - supported_matches
        betting_recommendations = len([p for p in predictions if p.prediction_available and p.recommend])
        
        summary = {
            "total_matches": total_matches,
            "supported_matches": supported_matches,
            "unsupported_matches": unsupported_matches,
            "betting_recommendations": betting_recommendations,
            "support_rate": f"{supported_matches/total_matches:.1%}" if total_matches > 0 else "0%",
            "recommendation_rate": f"{betting_recommendations/supported_matches:.1%}" if supported_matches > 0 else "0%"
        }
        
        return BatchPredictionResponse(predictions=predictions, summary=summary)
        
    except ValueError as e:
        # Handle input validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        # Handle missing model files
        raise HTTPException(status_code=404, detail=f"Model not found: {str(e)}")
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.get("/api/predict/leagues")
async def get_supported_leagues():
    """
    Get list of supported leagues and their information.
    
    Returns detailed information about each supported league
    including model performance and status.
    """
    
    if prediction_engine is None:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Prediction engine not available",
                "detail": engine_error,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    try:
        leagues_info = {}
        
        for league_key, config in prediction_engine.model_mapper.leagues.items():
            leagues_info[league_key] = {
                "name": league_key.replace('_', ' ').title(),
                "status": config['status'],
                "performance": config['performance'],
                "confidence_threshold": config['confidence_threshold'],
                "odds_threshold": config['odds_threshold'],
                "features_count": len(config['features']({})),  # Call with empty dict to get feature count
                "aliases": config['aliases']
            }
        
        return {
            "leagues": leagues_info,
            "total_leagues": len(leagues_info),
            "aliases_count": len(prediction_engine.model_mapper.league_aliases),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leagues info: {str(e)}")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unexpected errors."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )

# Health check endpoint
@app.get("/api/predict/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy" if prediction_engine is not None else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "engine_available": prediction_engine is not None,
        "engine_error": engine_error
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting SmartBet Prediction API Server")
    print("📊 Available endpoints:")
    print("   POST /api/predict        - Single match prediction")
    print("   POST /api/predict/batch  - Batch predictions")
    print("   GET  /api/predict/status - Model status")
    print("   GET  /api/predict/leagues - Supported leagues")
    print("   GET  /api/predict/health  - Health check")
    print("   GET  /api/predict/docs    - API documentation")
    
    uvicorn.run(
        "api_routes:app",
        host="0.0.0.0",
        port=8001,  # Different port from Django (8000)
        reload=True
    ) 