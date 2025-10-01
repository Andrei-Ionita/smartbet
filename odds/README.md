# OddsAPI Integration for SmartBet

This module provides integration with The Odds API to fetch high-quality odds from Pinnacle and other sharp bookmakers.

## Setup

1. Get an API key from [The Odds API](https://the-odds-api.com)
2. Add the API key to your `.env` file:
   ```
   ODDSAPI_KEY=your_api_key_here
   ```

## Features

- Fetches odds from Pinnacle (primary) and Bet365 (fallback)
- Focuses on Romanian leagues by default
- Handles rate limiting and retries
- Matches odds to existing matches in the database
- Stores odds in the `OddsSnapshot` model

## Usage

### Command Line

Fetch odds for all Romanian leagues:
```bash
python manage.py fetch_oddsapi_odds
```

Fetch odds for specific leagues:
```bash
python manage.py fetch_oddsapi_odds --leagues "romania_liga_1" "romania_liga_2"
```

### Python Code

```python
from odds.fetch_oddsapi import fetch_oddsapi_odds

# Fetch odds for all Romanian leagues
odds_snapshots = fetch_oddsapi_odds()

# Fetch odds for specific leagues
odds_snapshots = fetch_oddsapi_odds(league_keys=["romania_liga_1"])
```

## Rate Limits

The Odds API has the following rate limits:
- 500 requests per month (free tier)
- 1 request per second

The integration handles these limits by:
- Implementing retry logic with exponential backoff
- Checking remaining requests from response headers
- Logging warnings when running low on requests

## Supported Leagues

By default, the integration focuses on Romanian leagues:
- `romania_liga_1`
- `romania_liga_2`
- `romania_cup`

You can fetch odds for any league supported by The Odds API by specifying the league key.

## Error Handling

The integration includes comprehensive error handling:
- API request failures
- Rate limit exceeded
- Invalid response data
- Missing or incomplete odds
- Match not found in database

All errors are logged with appropriate context for debugging. 