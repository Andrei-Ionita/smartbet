"""
Sentiment Analysis & Trap Detection Service for SmartBet

This service analyzes social media sentiment to detect "trap games" where
public sentiment is heavily skewed compared to our predictions.

IMPORTANT: This is for EDUCATIONAL CONTEXT ONLY - does not adjust predictions.
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import praw
from django.conf import settings
from django.utils import timezone
from datetime import timezone as dt_timezone

logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    """Data structure for sentiment analysis results"""
    home_mentions_count: int
    away_mentions_count: int
    home_sentiment_score: float  # -1 to +1
    away_sentiment_score: float  # -1 to +1
    public_attention_ratio: float  # 0 to 1
    total_mentions: int
    top_keywords: List[str]
    data_sources: List[str]


@dataclass
class TrapAnalysis:
    """Data structure for trap detection results"""
    trap_score: int  # 0 to 10
    trap_level: str  # 'low', 'medium', 'high', 'extreme'
    alert_message: str
    recommendation: str
    confidence_divergence: float
    public_attention_ratio: float


class SentimentAnalyzer:
    """
    Analyzes social media sentiment to detect trap games.
    
    Trap games are matches where public sentiment is heavily skewed
    compared to our predictions, potentially indicating value opportunities
    or dangerous betting situations.
    """
    
    def __init__(self):
        """Initialize the sentiment analyzer with Reddit API credentials"""
        self.reddit = None
        self._init_reddit_client()
        
        # Sentiment keywords for simple analysis
        self.positive_keywords = {
            'win', 'winning', 'confident', 'dominate', 'strong', 'form', 
            'excellent', 'great', 'unstoppable', 'easy', 'clinical', 'sharp', 
            'ready', 'momentum', 'destroying', 'crushing', 'brilliant', 
            'outstanding', 'superb', 'favorite', 'guaranteed', 'sure'
        }
        
        self.negative_keywords = {
            'lose', 'losing', 'struggle', 'weak', 'poor', 'injured', 'crisis', 
            'terrible', 'worried', 'shaky', 'nervous', 'doubt', 'struggling', 
            'inconsistent', 'awful', 'horrible', 'disaster', 'nightmare', 
            'concerned', 'unreliable', 'vulnerable', 'exposed', 'fragile'
        }
        
        self.neutral_keywords = {
            'draw', 'tough', 'equal', 'balanced', '50-50', 'could go either way',
            'close', 'tight', 'unpredictable', 'even', 'fair'
        }
    
    def _init_reddit_client(self):
        """Initialize Reddit API client"""
        try:
            # Use read-only mode for public data access
            self.reddit = praw.Reddit(
                client_id=getattr(settings, 'REDDIT_CLIENT_ID', ''),
                client_secret=getattr(settings, 'REDDIT_CLIENT_SECRET', ''),
                user_agent=getattr(settings, 'REDDIT_USER_AGENT', 'SmartBet Sentiment Analyzer v1.0'),
                read_only=True  # This allows read-only access to public data
            )
            
            # Test the connection
            if self.reddit.read_only:
                logger.info("Reddit client initialized successfully in read-only mode")
            else:
                logger.warning("Reddit client initialized but not in read-only mode")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None
    
    def scrape_reddit_sentiment(
        self, 
        home_team: str, 
        away_team: str, 
        match_date: datetime
    ) -> Optional[SentimentData]:
        """
        Scrape Reddit for sentiment data about a specific match.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team  
            match_date: Date of the match
            
        Returns:
            SentimentData object with analysis results or None if failed
        """
        try:
            import requests
            
            # Use Reddit's public JSON API without authentication
            subreddits_to_search = ['soccer', 'PremierLeague', 'LaLiga', 'SerieA', 'Bundesliga']
            
            all_home_mentions = []
            all_away_mentions = []
            data_sources = set()  # Use set to avoid duplicates
            
            # Search each subreddit using public API
            for subreddit_name in subreddits_to_search:
                try:
                    # Reddit public JSON endpoint
                    search_query = f"{home_team} {away_team}"
                    url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
                    params = {
                        'q': search_query,
                        'sort': 'new',
                        't': 'day',
                        'limit': 25
                    }
                    headers = {
                        'User-Agent': getattr(settings, 'REDDIT_USER_AGENT', 'SmartBet Sentiment Analyzer v1.0')
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'data' in data and 'children' in data['data']:
                            posts = data['data']['children']
                            
                            for post_data in posts:
                                post = post_data['data']
                                
                                # Skip if post is too old (more than 48 hours)
                                post_time = timezone.datetime.fromtimestamp(post['created_utc'], tz=dt_timezone.utc)
                                if timezone.now() - post_time > timedelta(hours=48):
                                    continue
                                
                                # Analyze post title
                                self._analyze_text(post['title'], home_team, away_team, all_home_mentions, all_away_mentions)
                                
                                # Analyze selftext if available
                                if post.get('selftext'):
                                    self._analyze_text(post['selftext'], home_team, away_team, all_home_mentions, all_away_mentions)
                        
                        # Add subreddit to data sources only once per subreddit
                        if posts:  # Only add if we found posts
                            data_sources.add(f"reddit/r/{subreddit_name}")
                    
                except Exception as e:
                    logger.warning(f"Error searching r/{subreddit_name}: {e}")
                    continue
                
                # Rate limiting
                time.sleep(1)
            
            if not all_home_mentions and not all_away_mentions:
                logger.warning(f"No mentions found for {home_team} vs {away_team}")
                return None
            
            # Calculate sentiment scores
            home_sentiment = self._calculate_sentiment_score(all_home_mentions)
            away_sentiment = self._calculate_sentiment_score(all_away_mentions)
            
            # Calculate attention ratio
            total_mentions = len(all_home_mentions) + len(all_away_mentions)
            public_attention_ratio = min(total_mentions / 100, 1.0)  # Normalize to 0-1
            
            # Extract top keywords
            top_keywords = self._extract_top_keywords(all_home_mentions + all_away_mentions)
            
            logger.info(f"Found {total_mentions} mentions for {home_team} vs {away_team}")
            
            return SentimentData(
                home_mentions_count=len(all_home_mentions),
                away_mentions_count=len(all_away_mentions),
                home_sentiment_score=home_sentiment,
                away_sentiment_score=away_sentiment,
                public_attention_ratio=public_attention_ratio,
                total_mentions=total_mentions,
                top_keywords=top_keywords[:10],  # Top 10 keywords
                data_sources=list(data_sources)  # Convert set back to list
            )
            
        except Exception as e:
            logger.error(f"Error scraping Reddit sentiment: {e}")
            return None
    
    def _analyze_text(
        self, 
        text: str, 
        home_team: str, 
        away_team: str, 
        home_mentions: List[str], 
        away_mentions: List[str]
    ):
        """Analyze text for team mentions and sentiment"""
        if not text or len(text.strip()) < 10:
            return
        
        text_lower = text.lower()
        
        # Check for team mentions
        if home_team.lower() in text_lower:
            home_mentions.append(text)
        if away_team.lower() in text_lower:
            away_mentions.append(text)
    
    def _calculate_sentiment_score(self, mentions: List[str]) -> float:
        """Calculate sentiment score (-1 to +1) from mentions"""
        if not mentions:
            return 0.0
        
        positive_count = 0
        negative_count = 0
        total_words = 0
        
        for mention in mentions:
            words = mention.lower().split()
            total_words += len(words)
            
            for word in words:
                # Remove punctuation
                clean_word = re.sub(r'[^\w]', '', word)
                
                if clean_word in self.positive_keywords:
                    positive_count += 1
                elif clean_word in self.negative_keywords:
                    negative_count += 1
        
        if total_words == 0:
            return 0.0
        
        # Calculate sentiment score
        sentiment_score = (positive_count - negative_count) / total_words
        
        # Clamp to -1 to +1 range
        return max(-1.0, min(1.0, sentiment_score))
    
    def _extract_top_keywords(self, mentions: List[str]) -> List[str]:
        """Extract most frequent keywords from mentions"""
        word_freq = {}
        
        for mention in mentions:
            words = mention.lower().split()
            for word in words:
                clean_word = re.sub(r'[^\w]', '', word)
                if len(clean_word) > 3:  # Only words longer than 3 characters
                    word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10] if freq > 1]
    
    def calculate_trap_score(
        self, 
        prediction_probs: Dict[str, float], 
        sentiment_data: SentimentData,
        odds_data: Optional[Dict[str, float]] = None
    ) -> TrapAnalysis:
        """
        Calculate trap score based on prediction vs sentiment divergence.
        
        Args:
            prediction_probs: Our prediction probabilities {home: 0.72, draw: 0.17, away: 0.11}
            sentiment_data: Sentiment analysis results
            odds_data: Bookmaker odds {home: 2.50, draw: 3.20, away: 2.80}
            
        Returns:
            TrapAnalysis object with trap score and recommendations
        """
        trap_score = 0
        reasons = []
        
        # Get predicted favorite
        predicted_favorite = max(prediction_probs, key=prediction_probs.get)
        predicted_confidence = prediction_probs[predicted_favorite]
        
        # Calculate public sentiment favorite
        if sentiment_data.home_mentions_count > sentiment_data.away_mentions_count:
            public_favorite = 'home'
            public_confidence = abs(sentiment_data.home_sentiment_score)
        elif sentiment_data.away_mentions_count > sentiment_data.home_mentions_count:
            public_favorite = 'away'
            public_confidence = abs(sentiment_data.away_sentiment_score)
        else:
            public_favorite = 'draw'
            public_confidence = 0.5
        
        # Trap Score Calculation Logic
        
        # 1. High public attention + Low prediction confidence = Trap
        if sentiment_data.public_attention_ratio > 0.85 and predicted_confidence < 0.70:
            trap_score += 4
            reasons.append("High public attention with low prediction confidence")
        
        # 2. High public attention in general
        if sentiment_data.public_attention_ratio > 0.75:
            trap_score += 2
            reasons.append("Very high public attention")
        
        # 3. Sentiment vs prediction divergence
        if predicted_favorite != public_favorite:
            trap_score += 3
            reasons.append(f"Public favors {public_favorite}, we predict {predicted_favorite}")
        
        # 4. High sentiment confidence vs low prediction confidence
        if public_confidence > 0.80 and predicted_confidence < 0.70:
            trap_score += 3
            reasons.append("Public very confident, we're cautious")
        
        # 5. Odds divergence (if available)
        if odds_data:
            implied_probs = self._calculate_implied_probabilities(odds_data)
            max_implied = max(implied_probs.values())
            odds_divergence = abs(max_implied - predicted_confidence)
            
            if odds_divergence > 0.15:
                trap_score += 2
                reasons.append(f"Large divergence from bookmaker odds ({odds_divergence:.2f})")
        
        # Determine trap level
        if trap_score >= 7:
            trap_level = 'extreme'
            alert_message = f"⚠️ EXTREME TRAP ALERT: {', '.join(reasons[:2])}"
            recommendation = "This match shows extreme public bias. Proceed with extreme caution."
        elif trap_score >= 5:
            trap_level = 'high'
            alert_message = f"🚨 HIGH TRAP RISK: {', '.join(reasons[:2])}"
            recommendation = "Strong public bias detected. Consider reducing stake size."
        elif trap_score >= 3:
            trap_level = 'medium'
            alert_message = f"⚠️ MEDIUM TRAP RISK: {', '.join(reasons[:1])}"
            recommendation = "Moderate public bias. Monitor closely."
        else:
            trap_level = 'low'
            alert_message = "✅ Low trap risk"
            recommendation = "Public sentiment aligns reasonably with predictions."
        
        return TrapAnalysis(
            trap_score=min(trap_score, 10),  # Cap at 10
            trap_level=trap_level,
            alert_message=alert_message,
            recommendation=recommendation,
            confidence_divergence=abs(public_confidence - predicted_confidence),
            public_attention_ratio=sentiment_data.public_attention_ratio
        )
    
    def _calculate_implied_probabilities(self, odds: Dict[str, float]) -> Dict[str, float]:
        """Calculate implied probabilities from odds"""
        implied_probs = {}
        total_implied = 0
        
        for outcome, odd in odds.items():
            implied_prob = 1.0 / odd
            implied_probs[outcome] = implied_prob
            total_implied += implied_prob
        
        # Normalize to sum to 1
        for outcome in implied_probs:
            implied_probs[outcome] /= total_implied
        
        return implied_probs
    
    def analyze_match_sentiment(
        self, 
        match_id: int,
        home_team: str,
        away_team: str,
        match_date: datetime,
        prediction_probs: Dict[str, float],
        odds_data: Optional[Dict[str, float]] = None
    ) -> Tuple[Optional[SentimentData], Optional[TrapAnalysis]]:
        """
        Main orchestrator method for complete sentiment analysis.
        
        Args:
            match_id: Database ID of the match
            home_team: Home team name
            away_team: Away team name
            match_date: Match date
            prediction_probs: Our prediction probabilities
            odds_data: Optional bookmaker odds
            
        Returns:
            Tuple of (SentimentData, TrapAnalysis) or (None, None) if failed
        """
        try:
            logger.info(f"Analyzing sentiment for match {match_id}: {home_team} vs {away_team}")
            
            # Scrape sentiment data
            sentiment_data = self.scrape_reddit_sentiment(home_team, away_team, match_date)
            
            if not sentiment_data:
                logger.warning(f"No sentiment data available for match {match_id}")
                return None, None
            
            # Calculate trap analysis
            trap_analysis = self.calculate_trap_score(prediction_probs, sentiment_data, odds_data)
            
            logger.info(f"Sentiment analysis complete for match {match_id}. Trap score: {trap_analysis.trap_score}")
            
            return sentiment_data, trap_analysis
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for match {match_id}: {e}")
            return None, None
