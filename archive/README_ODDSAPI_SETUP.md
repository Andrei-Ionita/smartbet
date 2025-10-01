# OddsAPI Integration Setup Guide

## Step 1: Get API Access

1. **Visit**: https://the-odds-api.com/
2. **Sign up** for a paid plan (historical data requires paid subscription):
   - **20K Plan**: $30/month - 20,000 credits
   - **100K Plan**: $59/month - 100,000 credits
   - **5M Plan**: $119/month - 5M credits

3. **Receive API key** via email
4. **Add to .env file**:
   ```
   ODDSAPI_KEY=your_api_key_here
   ```

## Step 2: Understanding Costs

**Historical Odds**: 10 credits per region per market
- **Example**: Premier League, UK bookmakers, h2h market = 10 credits per date
- **Your Dataset**: ~1,500 fixtures across multiple seasons
- **Estimated Cost**: 15,000-20,000 credits for full historical coverage

## Step 3: Sport Key and Parameters

- **Sport**: `soccer_epl` (English Premier League)
- **Regions**: `uk` (UK bookmakers), `eu` (EU bookmakers), `us` (US bookmakers)
- **Markets**: 
  - `h2h` (Match Winner / 1X2)
  - `totals` (Over/Under 2.5 Goals)
  - Multiple markets increase cost

## Step 4: Historical Data Coverage

- **Available From**: June 6, 2020
- **Your Training Data**: 2014-2024
- **Coverage**: Seasons 2020/21-2023/24 will have good odds coverage
- **Missing**: Seasons 2014/15-2019/20 (pre-OddsAPI historical data)

## Step 5: Implementation Strategy

1. **Test with small sample** (10-20 fixtures)
2. **Validate data quality** and coverage
3. **Scale up gradually** to avoid quota exhaustion
4. **Focus on recent seasons** (2020-2024) for best coverage

## Next Steps

Once you have the API key, run the test scripts to validate setup and begin data collection. 