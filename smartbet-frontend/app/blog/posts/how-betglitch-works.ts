import { BlogPost } from '../types'

export const howBetglitchWorks: BlogPost = {
  slug: 'how-betglitch-works',
  title: 'How BetGlitch Works: From Fixture Data to Published Results',
  description: 'How BetGlitch takes probability data from a specialist football data provider, ranks it with its own filters, and freezes selected picks before kickoff so every settled result can be checked.',
  author: 'BetGlitch Team',
  date: '2026-03-15',
  readTime: '8 min read',
  tags: ['Signals', 'Transparency', 'How It Works'],
  content: `
<h2 class="text-2xl font-semibold text-gray-900 mb-4">Introduction: Smarter Predictions Through Data</h2>
<p class="text-gray-700 leading-relaxed mb-6">
The sports prediction landscape is crowded with tipsters who rely on gut feelings, outdated heuristics, and selective memory. BetGlitch takes a different approach. We take probability data from a specialist football data provider, apply our own ranking filters, and freeze selected picks before kickoff — wins and losses alike — across European competitions. We do not claim a predictive edge of our own; whether our filtering adds value is something we are still measuring in public.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
One distinction runs through everything below, so it is worth stating first. A <strong class="text-gray-900">live fixture analysis</strong> can change before kickoff. A <strong class="text-gray-900">published Gem</strong> is a selection locked before kickoff, and it cannot be edited later. Most fixture analyses never become Gems. Only settled Gems from the current strategy count in the current results; earlier strategies remain in a separate archive.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Our mission is simple: make football decisions easier to inspect. BetGlitch compares provider probability data, verified market prices and available fixture context, applies a fixed Gem filter, and locks every qualifying selection before kickoff so its result can be checked afterwards. This article explains exactly how that works.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Where the probabilities come from</h2>
<p class="text-gray-700 leading-relaxed mb-6">
At the core of BetGlitch is a specialist football data provider's probability model. We do not build, train or own a predictive model, and we do not claim to. There is no second model and no averaging of opinions: one provider supplies a probability vector per market — match result, over/under 2.5, both teams to score, double chance — and we work from those numbers.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
We rank those probabilities against recorded market prices. For each fixture and market we record:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Signal score:</strong> A relative ranking score, not a calibrated probability. It orders candidates; it does not state a chance of winning.</li>
<li><strong class="text-gray-900">Probability gap:</strong> How far the leading outcome sits above the next one. A narrow gap means the market is close to a coin flip.</li>
<li><strong class="text-gray-900">Recorded price:</strong> The exact odds, bookmaker, market and capture time behind every published Gem.</li>
</ul>
<p class="text-gray-700 leading-relaxed mb-6">
We are deliberately careful about what this does and does not prove. A ranking score is not a calibrated probability, and we have not yet demonstrated that our filtering beats the market price. That is precisely why the public record exists: to test it in the open rather than assert it.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Filtering: Being Selective</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Raw provider probabilities alone are not enough, so BetGlitch narrows them before anything is surfaced. These filters are selection rules, not validated predictors — they decide what we look at, and we have not shown that they improve results:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Signal-score floor:</strong> Candidates below a minimum score are not surfaced. The threshold is a selection rule we tune, not a validated accuracy boundary.</li>
<li><strong class="text-gray-900">Price gating:</strong> A candidate is only considered when we hold a verified market price for the exact market being ranked, with complete provenance. Without one, value cannot be assessed at all.</li>
<li><strong class="text-gray-900">Odds range:</strong> We concentrate on moderate odds. This bounds variance; it is not evidence that we price long shots correctly.</li>
<li><strong class="text-gray-900">Competition-specific handling:</strong> Some competitions are excluded or handled more conservatively. These lists are maintained by hand and revised as the sample grows.</li>
<li><strong class="text-gray-900">Probability gap:</strong> How far the leading outcome sits above the next one. A narrow gap means the market is close to a coin flip.</li>
</ul>
<p class="text-gray-700 leading-relaxed mb-6">
We used to publish an accuracy figure against the probability-gap filter. We have withdrawn it. It was measured on a sample that included predictions priced from the wrong market, so it was not a valid measurement of anything, and we would rather show no number than a number we cannot stand behind.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">The signal score</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Every candidate that passes the filters carries a signal score from 0 to 100. It ranks our relative preference among the available outcomes in one market. It is <strong class="text-gray-900">not</strong> a calibrated probability: a score of 66 does not mean the outcome happens 66% of the time, and a score of 70 is not "safer" than one of 60 in any way we have validated. We publish no tiers, no bet/no-bet decision, no fair odds and no numeric expected value, because each of those would assert a calibration standard we do not have.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Data Pipeline: From Source to Prediction</h2>
<p class="text-gray-700 leading-relaxed mb-6">
BetGlitch sources its probability and fixture data from a specialist third-party provider. Our pipeline operates in several stages:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Data ingestion:</strong> Fixture data, team information and recorded odds are pulled continuously for every covered competition.</li>
<li><strong class="text-gray-900">Probability ingestion:</strong> Provider probabilities are collected for each fixture and market type, with every outcome retained rather than only the favoured side.</li>
<li><strong class="text-gray-900">Filtering and ranking:</strong> The filters above narrow the candidates, and the survivors are ranked to produce a signal score.</li>
<li><strong class="text-gray-900">Publication:</strong> Up to three qualifying Gems are frozen before kickoff with their signal score, recorded price, bookmaker, provenance and immutable timestamps. A published Gem is never edited or withdrawn.</li>
<li><strong class="text-gray-900">Settlement:</strong> After full-time a published Gem is graded against the fields frozen at publication. Results are inserted, never overwritten.</li>
</ul>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Coverage</h2>
<p class="text-gray-700 leading-relaxed mb-6">
BetGlitch indexes European competitions spanning the top divisions of major footballing nations, selected second tiers, domestic cups and the UEFA club tournaments — the Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Liga Portugal, Süper Lig and more. Not every indexed competition produces signals: the UEFA tournaments are searchable but are not currently swept, so a fixture can be visible without ever being ranked. The current figures are shown on the <a href="/about" class="text-blue-600 hover:underline font-medium">about page</a>, which reads them from the same source the product does.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">What Makes BetGlitch Different</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Several qualities set BetGlitch apart from traditional tipsters and other prediction platforms:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Ranking, not tipping:</strong> We rank provider probabilities against recorded prices and only surface a candidate when it clears our filters.</li>
<li><strong class="text-gray-900">Immutability:</strong> A published Gem freezes its selection, signal score, price, bookmaker and provenance. It cannot be edited, re-priced, re-graded or withdrawn.</li>
<li><strong class="text-gray-900">Consistency:</strong> The same rules run on every fixture. There are no favourite teams and no retrospective reinterpretation of a result.</li>
<li><strong class="text-gray-900">Breadth:</strong> Sweeping every covered competition across four markets at once is beyond the capacity of an individual tipster.</li>
<li><strong class="text-gray-900">Published losses:</strong> Losing claims stay up at the same prominence as winning ones. Odds are never rewritten.</li>
</ul>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">What Actually Counts</h2>
<p class="text-gray-700 leading-relaxed mb-6">
It would be easy to claim that we publish everything we produce. It would also be false, and the difference matters more than the slogan. BetGlitch generates far more live signals than it publishes; only the ones we freeze become claims. So the honest version is narrower:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li>Live signals can change until kickoff, and count towards nothing.</li>
<li>Every published Gem is immutable and stays permanently visible, win or lose.</li>
<li>Only settled Gems produced by the current strategy count in the current results.</li>
<li>Pending claims count towards nothing until the match finishes.</li>
<li>Void and cancelled claims stay visible but are excluded from the relevant totals.</li>
</ul>
<p class="text-gray-700 leading-relaxed mb-6">
This makes our record smaller than the number of signals we produce, and that is deliberate. Settlement is graded against the fields frozen at publication, results are inserted rather than overwritten, and nothing is deleted. Visit the <a href="/track-record" class="text-blue-600 hover:underline font-medium">track record page</a> to check any of it yourself.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
BetGlitch is a free public beta, is not a bookmaker, and does not accept bets. Nothing here is advice, no output guarantees profit, and you can lose all the money you wager.
</p>
`,
}
