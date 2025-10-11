# Reddit API Configuration for SmartBet Sentiment Analysis
# Copy these values to your Django settings or environment variables

REDDIT_CONFIG = {
    'CLIENT_ID': 'Tl6PL8QbrVeUxOoyORZO3g',
    'CLIENT_SECRET': 'IMPK4KWi8ruQ13N3lcBC8Ahmyptxcw',
    'USER_AGENT': 'SmartBet Sentiment Analyzer v1.0',
    'REDIRECT_URI': 'http://localhost:8000'
}

# Instructions:
# 1. Add these to your Django settings.py:
# REDDIT_CLIENT_ID = 'Tl6PL8QbrVeUxOoyORZO3g'
# REDDIT_CLIENT_SECRET = 'IMPK4KWi8ruQ13N3lcBC8Ahmyptxcw'
# REDDIT_USER_AGENT = 'SmartBet Sentiment Analyzer v1.0'

# 2. Or set as environment variables:
# export REDDIT_CLIENT_ID=Tl6PL8QbrVeUxOoyORZO3g
# export REDDIT_CLIENT_SECRET=IMPK4KWi8ruQ13N3lcBC8Ahmyptxcw
# export REDDIT_USER_AGENT="SmartBet Sentiment Analyzer v1.0"
