/* Local UI verification with synthetic API fixtures; never contacts production. */
const { chromium } = require(process.argv[2] || 'playwright')
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const origin = process.env.PORTFOLIO_TEST_ORIGIN || 'http://localhost:4111'
const now = Date.now()
const date = new Date(now + 8 * 3600000).toISOString()
const markets = [
  ['btts', 'Both teams to score', 'Ambele echipe marchează', 'both-teams-to-score'],
  ['asian_handicap', 'Asian handicap', 'Handicap asiatic', 'asian-handicap'],
  ['1x2', 'Match result', 'Rezultat final', 'match-result'],
]
const cards = Array.from({ length: 5 }, (_, i) => ({
  selection_id: `test-${i}`, receipt_url: `/results/selection/test-${i}`,
  fixture_id: 99000+i, home_team: ['Rapid București','Arsenal','Barcelona','Inter','Celtic'][i],
  away_team: ['Dinamo București','Everton','Valencia','Torino','Aberdeen'][i], league: 'Sample league',
  kickoff: date, market_type: markets[i%3][0], predicted_outcome: i%3===1 ? 'Home -0.25' : i%3===0 ? 'yes' : 'home',
  odds: 2, current_odds: 2.02, bookmaker_count: 7, published_at: new Date(now).toISOString(),
  odds_captured_at: new Date(now).toISOString(), current_price_at: new Date(now).toISOString(),
  status: 'PENDING', unit_profit: null, homepage: true,
  evidence: { model_probability: i%3===1 ? null : .61, market_probability: i%3===1 ? null : .48,
    conservative_probability: i%3===1 ? null : .46, model_ev: .12, conservative_ev: -.07,
    calibration_count: 12, probability_method: i%3===1 ? 'score_distribution_stress' : 'market_shrunk_calibration',
    evidence_label: 'research', context: {lineups:'unavailable', observed_at:new Date(now).toISOString(), form_available:false, absences_available:false, absence_count:null}},
}))
const board = {success:true, version:'market-portfolio-v5', status:'ready', generated_at:new Date(now).toISOString(),
  homepage:cards, markets:markets.map(([key,en,ro,slug]) => ({key,name:{en,ro},strategy_url:`/strategies/${slug}`,status:'ready',evaluated:10,selections:cards.filter(c=>c.market_type===key)})), unavailable_markets:{},
  scan:{fixtures_evaluated:150,candidates_evaluated:400,eligible_candidates:20,published_on_board:5,rejections:{model_edge_too_small:25}}}
const summary = {published:5,pending:5,settled:0,won:0,lost:0,half_won:0,half_lost:0,push:0,profit_units:0,roi_percent:null,average_odds:null}
const report = {overall:summary,by_market:markets.map(([key])=>({...summary,key,published:cards.filter(c=>c.market_type===key).length}))}
const results = {version:board.version,selections:cards,performance:report,homepage_performance:report}

;(async () => {
  const browser = await chromium.launch({headless:true})
  const output = path.join(__dirname, '..', 'docs', 'qa', 'portfolio-v5')
  fs.mkdirSync(output,{recursive:true})
  const errors=[]
  try {
    for (const [language,width,height] of [['en',1440,1100],['ro',390,844]]) {
      const context=await browser.newContext({viewport:{width,height}})
      await context.addInitScript(lang=>{
        localStorage.setItem('smartbet-lang',lang)
        localStorage.setItem('smartbet_legal_consent', JSON.stringify({accepted:true,version:'1.0',timestamp:new Date().toISOString()}))
      }, language)
      await context.route('**/*',route=>{
        const url=new URL(route.request().url())
        if(url.origin!==origin) return route.abort()
        if(url.pathname==='/api/selection-portfolio') return route.fulfill({json:url.searchParams.get('view')==='results'?results:board})
        if(url.pathname.startsWith('/api/')) return route.fulfill({json:{success:true,recommendations:[],featured_gems:[],data:[]}})
        return route.continue()
      })
      const page=await context.newPage()
      page.on('pageerror',e=>errors.push(e.message))
      for (const [url,count] of [['/',5],['/markets',2],['/strategies/asian-handicap',2],['/track-record',5]]) {
        await page.goto(origin+url,{waitUntil:'domcontentloaded'})
        const main=page.locator(url==='/' ? '#homepage-selections-heading' : 'main').first()
        await main.waitFor()
        await page.getByText(url==='/strategies/asian-handicap' ? 'Arsenal vs Everton' : 'Rapid București vs Dinamo București',{exact:false}).first().waitFor({timeout:15000})
        await page.waitForTimeout(200)
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth+1),false,`Horizontal overflow: ${language} ${url}`)
        if(url==='/') {
          assert.equal(await page.locator('section[aria-labelledby="homepage-selections-heading"] article').count(),count)
          await page.locator('section[aria-labelledby="homepage-selections-heading"]').screenshot({path:path.join(output,`homepage-${language}.png`)})
        } else {
          await page.screenshot({path:path.join(output,`${url.replaceAll('/','_')}-${language}.png`),fullPage:true})
        }
        console.log(`PASS ${language} ${width}px ${url}`)
      }
      await context.close()
    }
    assert.deepEqual(errors,[])
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
