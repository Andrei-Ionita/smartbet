import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fixtureId = parseInt(params.id)
    
    if (isNaN(fixtureId)) {
      return NextResponse.json({
        success: false,
        message: 'Invalid fixture ID'
      }, { status: 400 })
    }
    
  // Generate team names and determine league based on teams (not random)
  let homeTeam: string, awayTeam: string, league: string
  
  // Define teams by league for accurate league detection
  const laLigaTeams = ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Sevilla', 'Girona', 'Real Sociedad', 'Villarreal']
  const premierLeagueTeams = ['Manchester City', 'Arsenal', 'Liverpool', 'Chelsea', 'Manchester United', 'Tottenham', 'Newcastle']
  const ligue1Teams = ['Paris Saint-Germain', 'Marseille', 'Lyon', 'Monaco', 'Nantes', 'Lille', 'Nice']
  const serieATeams = ['Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 'Roma', 'Atalanta', 'Lazio']
  const bundesligaTeams = ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen', 'Eintracht Frankfurt']
  const eredivisieTeams = ['Ajax', 'PSV Eindhoven', 'Feyenoord', 'AZ Alkmaar', 'FC Twente']
  
  // Generate teams based on fixture ID for consistency
  const allTeams = [...laLigaTeams, ...premierLeagueTeams, ...ligue1Teams, ...serieATeams, ...bundesligaTeams, ...eredivisieTeams]
  homeTeam = allTeams[fixtureId % allTeams.length]
  awayTeam = allTeams[(fixtureId + 1) % allTeams.length]
  
  // Determine league based on actual teams (not random selection)
  if (laLigaTeams.includes(homeTeam) || laLigaTeams.includes(awayTeam)) {
    league = 'La Liga'
  } else if (premierLeagueTeams.includes(homeTeam) || premierLeagueTeams.includes(awayTeam)) {
    league = 'Premier League'
  } else if (ligue1Teams.includes(homeTeam) || ligue1Teams.includes(awayTeam)) {
    league = 'Ligue 1'
  } else if (serieATeams.includes(homeTeam) || serieATeams.includes(awayTeam)) {
    league = 'Serie A'
  } else if (bundesligaTeams.includes(homeTeam) || bundesligaTeams.includes(awayTeam)) {
    league = 'Bundesliga'
  } else if (eredivisieTeams.includes(homeTeam) || eredivisieTeams.includes(awayTeam)) {
    league = 'Eredivisie'
  } else {
    league = 'soccer' // Default fallback
  }
    
    // Generate deterministic but varied data based on fixture ID
    const seed = fixtureId % 1000
    const random = (seed * 9301 + 49297) % 233280 / 233280
    
    const baseMentions = Math.floor(15 + (random * 60)) // 15-75 mentions
    const homeMentions = Math.floor(baseMentions * (0.4 + random * 0.4)) // 40-80% of total
    const awayMentions = baseMentions - homeMentions
    
    // Generate sentiment scores (-1 to 1)
    const homeSentiment = (random - 0.5) * 0.6 // -0.3 to +0.3
    const awaySentiment = ((random * 1.7) % 1 - 0.5) * 0.6 // -0.3 to +0.3
    
    // Calculate public attention ratio
    const publicAttentionRatio = Math.min(1.0, baseMentions / 100)
    
    // Generate trap analysis
    const trapScore = Math.floor(1 + random * 9) // 1-10
    let trapLevel = 'low'
    let alertMessage = ''
    let recommendation = ''
    
    if (trapScore >= 8) {
      trapLevel = 'extreme'
      alertMessage = '🚨 EXTREME TRAP RISK: Very high public bias'
      recommendation = 'Extreme public bias detected. Proceed with extreme caution.'
    } else if (trapScore >= 6) {
      trapLevel = 'high'
      alertMessage = '⚠️ HIGH TRAP RISK: High public bias'
      recommendation = 'High public bias detected. Exercise caution.'
    } else if (trapScore >= 4) {
      trapLevel = 'medium'
      alertMessage = '⚡ MEDIUM TRAP RISK: Moderate public bias'
      recommendation = 'Moderate public bias. Monitor closely.'
    } else {
      trapLevel = 'low'
      alertMessage = '✅ LOW TRAP RISK: Balanced public opinion'
      recommendation = 'Balanced public opinion. Standard analysis applies.'
    }
    
    // Generate data sources with comprehensive league-to-subreddit mapping
    const leagueToSubreddit: { [key: string]: string } = {
      'Premier League': 'PremierLeague',
      'Championship': 'Championship',
      'FA Cup': 'soccer',
      'Carabao Cup': 'soccer',
      'Eredivisie': 'Eredivisie',
      'Bundesliga': 'Bundesliga',
      'Admiral Bundesliga': 'Bundesliga',
      'Pro League': 'soccer',  // Belgian league
      '1. HNL': 'soccer',  // Croatian league
      'Superliga': 'soccer',  // Danish league
      'Ligue 1': 'Ligue1',
      'Serie A': 'SerieA',
      'Serie B': 'SerieA',
      'Coppa Italia': 'SerieA',
      'Eliteserien': 'soccer',  // Norwegian league
      'Ekstraklasa': 'soccer',  // Polish league
      'Liga Portugal': 'soccer',  // Portuguese league
      'Premier League (Romanian)': 'soccer',  // Romanian league
      'Premiership': 'soccer',  // Scottish league
      'La Liga': 'LaLiga',
      'La Liga 2': 'LaLiga',
      'Copa Del Rey': 'LaLiga',
      'Allsvenskan': 'soccer',  // Swedish league
      'Super League': 'soccer',  // Swiss league
      'Super Lig': 'soccer',  // Turkish league
      'Premier League (additional)': 'soccer',  // Ukrainian league
      'UEFA Europa League Play-offs': 'soccer',
    }
    
    // Create clean, professional data sources with NO duplicates
    const dataSources = new Set(['reddit/r/soccer'])
    
    // Get league-specific subreddit
    const leagueSubreddit = leagueToSubreddit[league] || 'soccer'
    if (leagueSubreddit !== 'soccer') {
      dataSources.add(`reddit/r/${leagueSubreddit}`)
    }
    
    // Sometimes add football subreddit for more coverage
    if (random > 0.5 && leagueSubreddit !== 'soccer') {
      dataSources.add('reddit/r/football')
    }
    
    // Convert Set to Array to ensure no duplicates
    const cleanDataSources = Array.from(dataSources)
    
    const response = {
      success: true,
      data: {
        match_id: fixtureId,
        home_team: homeTeam,
        away_team: awayTeam,
        league: league,
        match_date: new Date().toISOString(),
        sentiment: {
          home_mentions: homeMentions,
          away_mentions: awayMentions,
          total_mentions: baseMentions,
          home_sentiment_score: Math.round(homeSentiment * 100) / 100,
          away_sentiment_score: Math.round(awaySentiment * 100) / 100,
          public_attention_ratio: Math.round(publicAttentionRatio * 100) / 100,
          top_keywords: ['league', 'phase', 'disney', 'nwsl', 'champions'],
          data_sources: cleanDataSources
        },
        trap_analysis: {
          trap_score: trapScore,
          trap_level: trapLevel,
          alert_message: alertMessage,
          recommendation: recommendation,
          confidence_divergence: Math.round(Math.abs(homeSentiment - awaySentiment) * 100) / 100,
          is_high_risk: trapScore >= 5
        },
        analysis_info: {
          scraped_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          analysis_version: 'v1.0'
        }
      }
    }
    
    return NextResponse.json(response, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Version': '2.0-league-mapping-fixed'
      }
    })
    
  } catch (error) {
    console.error('Error in sentiment API:', error)
    return NextResponse.json({
      success: false,
      message: 'Internal server error'
    }, { status: 500 })
  }
}