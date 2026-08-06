import { BlogPost } from '../types'

export const valueBettingExplained: BlogPost = {
  slug: 'value-betting-explained',
  title: 'Understanding Value Betting: How Expected Value Works',
  description: 'A plain explanation of value betting and expected value, with worked hypothetical examples — plus an honest account of what BetGlitch has and has not shown about pricing.',
  author: 'BetGlitch Team',
  date: '2026-03-20',
  readTime: '10 min read',
  tags: ['Value Betting', 'Strategy', 'Expected Value'],
  content: `
<div class="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-5">
<p class="text-sm leading-relaxed text-amber-900">
<strong class="text-amber-900">Read this first.</strong> Every calculation in this article is a
<strong class="text-amber-900">hypothetical educational example</strong> using invented numbers, written to
explain the mathematics of expected value and stake sizing. None of it is BetGlitch output, and none of it
describes what BetGlitch does. In particular: BetGlitch does not publish calibrated probabilities, does not
publish a numeric expected value, does not calculate a Kelly stake for you, and has <em>not</em> demonstrated
that it can find mispriced markets. Whether our filtering has any pricing value is still being evaluated in
public. Treat the worked examples as arithmetic, not as a description of a product feature.
</p>
</div>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">What Is Value Betting and Why Does It Matter?</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Value betting is the practice of placing bets only when the odds offered by a bookmaker imply a lower probability of an outcome than your own assessed probability. In other words, you bet when you believe the bookmaker has priced an outcome incorrectly in your favor. This is the single most important concept in long-term betting profitability — without understanding value, sustained profit is essentially impossible regardless of how much football knowledge you have.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Most casual bettors focus on picking winners. But picking winners is not enough. If you back a team at odds of 1.50 and they win 60% of the time, you are losing money in the long run. The odds imply a 66.7% probability, but the team only wins 60% of the time. That is negative value. Conversely, if you find a team priced at 3.00 (implied probability 33.3%) that actually wins 40% of the time, you have a significant edge — even though that team loses more often than it wins.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Expected Value (EV) Explained</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Expected Value is the mathematical foundation of value betting. It tells you how much you can expect to gain or lose per unit staked over the long run. The formula is straightforward:
</p>
<p class="text-gray-700 leading-relaxed mb-4">
<strong class="text-gray-900">EV = (Probability of Winning x Profit if Win) - (Probability of Losing x Stake)</strong>
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Or equivalently, for decimal odds:
</p>
<p class="text-gray-700 leading-relaxed mb-4">
<strong class="text-gray-900">EV = (Your Probability x Decimal Odds) - 1</strong>
</p>
<p class="text-gray-700 leading-relaxed mb-6">
If EV is positive, the bet has value. If EV is negative, the bookmaker has the edge. For example, suppose you estimate a home team has a 55% chance of winning, and the bookmaker offers odds of 2.00 (implied probability 50%). The EV calculation is:
</p>
<p class="text-gray-700 leading-relaxed mb-4">
<strong class="text-gray-900">EV = (0.55 x 2.00) - 1 = 1.10 - 1 = +0.10</strong>
</p>
<p class="text-gray-700 leading-relaxed mb-6">
This means for every $1 you stake, you expect to profit $0.10 in the long run. A 10% edge is excellent in the betting world. Over hundreds of bets, this compounds into substantial returns.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Why Bookmaker Odds Are Not Always Efficient</h2>
<p class="text-gray-700 leading-relaxed mb-6">
A common misconception is that bookmaker odds perfectly reflect the true probability of outcomes. In reality, several factors create pricing inefficiencies that informed bettors can exploit:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">The Overround:</strong> Bookmakers build a profit margin (typically 3-10%) into their odds. This means the implied probabilities of all outcomes in a market sum to more than 100%. The overround does not affect all outcomes equally — it is often distributed unevenly, creating pockets of value on specific selections.</li>
<li><strong class="text-gray-900">Public Bias:</strong> Bookmakers adjust their lines based on where money is flowing. Popular teams attract disproportionate betting volume, which can push their odds down below fair value — simultaneously inflating the odds on less popular opponents. This popularity bias is one of the most consistent sources of value in football betting.</li>
<li><strong class="text-gray-900">Slow Line Movement:</strong> When new information emerges — injuries, lineup changes, weather conditions — bookmakers do not always adjust instantly. There is often a window where the odds have not yet caught up to reality. Models that process information quickly can identify these windows.</li>
<li><strong class="text-gray-900">League-Specific Blind Spots:</strong> Bookmakers devote more resources to pricing high-profile leagues like the Premier League. Smaller leagues often have softer lines because less analytical effort is applied to them, creating more frequent value opportunities.</li>
</ul>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Where BetGlitch Actually Stands</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Everything above is textbook. Here is the honest position of this product against it.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
BetGlitch uses probability data from a single specialist football data provider across the European competitions it covers. The provider's model produces probability estimates; we filter and rank them against recorded prices and surface the highest-ranked outcome per market. That ranking is expressed as a <strong class="text-gray-900">signal score out of 100</strong>.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
The signal score is <strong class="text-gray-900">not</strong> a calibrated probability, and this is the whole reason we publish no expected value. Every EV formula above needs a probability as its input. Feed it a ranking instead and the output has the shape of an expected value without the meaning of one — so we do not display one, and we do not derive a Kelly stake from it either. Our own calibration study found the score barely separable from a constant on the markets we checked, which is exactly the situation in which a confident-looking percentage does the most damage.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
So BetGlitch does not tell you a price is mispriced. What it does is narrower and checkable: it records which outcome it ranked highest, at exactly which price, from which bookmaker, with full provenance, and — for picks it publishes — freezes all of that before kickoff so the result can be checked afterwards. Whether that has any pricing value is an open question our public record exists to answer.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">The Kelly Criterion: Sizing Your Stakes</h2>
<p class="text-gray-700 leading-relaxed mb-6">
<em>Hypothetical educational example.</em> Kelly needs a genuine probability as its input. BetGlitch does not have one to give you — the signal score is a ranking — so BetGlitch does not calculate a Kelly stake and this section is arithmetic only, not a product feature.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Finding value is only half the equation. The other half is staking — how much should you bet on each value opportunity? The Kelly Criterion provides a mathematically optimal answer <em>given a correct probability</em>. The formula is:
</p>
<p class="text-gray-700 leading-relaxed mb-4">
<strong class="text-gray-900">Kelly % = (bp - q) / b</strong>
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Where <em>b</em> is the decimal odds minus 1, <em>p</em> is your probability of winning, and <em>q</em> is the probability of losing (1 - p). The result tells you what fraction of your bankroll to stake. For example, using our earlier scenario (55% probability, odds of 2.00):
</p>
<p class="text-gray-700 leading-relaxed mb-4">
<strong class="text-gray-900">Kelly % = (1.00 x 0.55 - 0.45) / 1.00 = 0.10, or 10% of bankroll</strong>
</p>
<p class="text-gray-700 leading-relaxed mb-6">
In practice, most experienced bettors use a fractional Kelly approach — staking one-quarter to one-half of the full Kelly amount. This reduces variance significantly while still capturing most of the long-term edge. Full Kelly can lead to large drawdowns that are psychologically difficult to endure, even when the math is in your favor.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">A Practical Walkthrough</h2>
<p class="text-gray-700 leading-relaxed mb-6">
<em>Hypothetical educational example.</em> The fixture, the probabilities and the prices below are invented to make the arithmetic concrete. They are not BetGlitch output, and BetGlitch does not display any of the figures derived from them.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Suppose a bettor has assessed an upcoming Serie A match between Napoli and Atalanta and arrived at the following probabilities:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Napoli Win:</strong> 48%</li>
<li><strong class="text-gray-900">Draw:</strong> 27%</li>
<li><strong class="text-gray-900">Atalanta Win:</strong> 25%</li>
</ul>
<p class="text-gray-700 leading-relaxed mb-6">
Now check the bookmaker odds. The best available odds for a draw are 3.90, which implies a probability of 25.6%. The assessment above says 27%. The EV calculation: (0.27 x 3.90) - 1 = 1.053 - 1 = <strong class="text-gray-900">+0.053, or +5.3% EV</strong>. This is a value bet. The Kelly Criterion suggests a stake of approximately (2.90 x 0.27 - 0.73) / 2.90 = 1.8% of bankroll. Using quarter-Kelly, you would stake around 0.45% of your bankroll.
</p>
<p class="text-gray-700 leading-relaxed mb-6">
Will this specific bet win? Maybe, maybe not. And note the load-bearing assumption: the whole calculation only holds if that 27% is genuinely correct. Positive expected value computed from a wrong probability is not value — it is a wrong number wearing the right notation. Getting the probability right is the hard part, and it is precisely the part BetGlitch has not demonstrated.
</p>

<h2 class="text-2xl font-semibold text-gray-900 mb-4">Risk Management and Realistic Expectations</h2>
<p class="text-gray-700 leading-relaxed mb-6">
Value betting is not a get-rich-quick scheme. It is a disciplined, long-term strategy that requires patience, proper bankroll management, and emotional control. Here are key principles to keep in mind:
</p>
<ul class="list-disc list-inside space-y-2 mb-6 text-gray-700">
<li><strong class="text-gray-900">Losing streaks are inevitable.</strong> Even with a genuine 5% edge, you will experience extended losing runs. A bankroll management system like fractional Kelly ensures you survive these drawdowns.</li>
<li><strong class="text-gray-900">Sample size matters.</strong> You cannot judge a value betting strategy on 20 bets. You need hundreds, ideally thousands, of bets before the edge reliably manifests in your results.</li>
<li><strong class="text-gray-900">Never bet more than you can afford to lose.</strong> A positive expected value does not reduce the risk of any individual bet, and variance is real. Only use money you have explicitly set aside for this purpose.</li>
<li><strong class="text-gray-900">Track everything.</strong> Record every bet, the odds, your assessed probability, and the outcome. This data is essential for evaluating whether your edge is real and persisting over time.</li>
<li><strong class="text-gray-900">Stay disciplined.</strong> Do not chase losses by increasing stakes. Do not skip value bets because the selection "feels" wrong. Trust the process and the math.</li>
</ul>
<p class="text-gray-700 leading-relaxed mb-6">
BetGlitch does not provide an edge, and does not claim one. What it provides is a record: which outcome it ranked highest, at exactly which price and bookmaker, frozen before kickoff when it publishes, and settled in public afterwards — wins and losses alike. Every decision to bet, and every stake, is yours. BetGlitch is a free public beta, is not a bookmaker, does not accept bets, and no output guarantees profit. You can lose all the money you wager.
</p>
`,
}
