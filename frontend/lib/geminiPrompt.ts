export const VALID_TAGS = [
  'gap-and-hold',
  'gap-and-fade',
  'breakout-clean',
  'breakout-whipsaw',
  'multi-day-runner',
  'sector-sympathy',
  'news-fresh',
  'news-stale',
  'halt-triggered',
  'failed-follow-through',
] as const

export type PatternTag = (typeof VALID_TAGS)[number]

// ---------------------------------------------------------------------------
// Standardised Gemini chart analysis prompt
// ---------------------------------------------------------------------------

export const GEMINI_CHART_PROMPT = `Analyze this stock chart screenshot and return a structured analysis in the following format:

**Ticker**: [ticker]
**Date**: [date]
**Timeframe**: [timeframe]

**Structure**:
- Trend direction and key levels (support/resistance)
- Candle quality at key levels (clean, whipsaw, indecisive)
- Any notable chart patterns (flag, base, ascending triangle, etc.)

**Volume Behavior**:
- Volume on the move vs. average
- Climactic volume? Drying up at base?

**Entry Zone**:
- Ideal entry price or zone
- Stop loss level and rationale

**Verdict**:
- Setup quality: [Clean / Marginal / Avoid]
- Continuation potential: [High / Medium / Low]
- Key risk: [1 sentence]`

export async function copyGeminiPrompt(): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(GEMINI_CHART_PROMPT)
    return true
  } catch {
    return false
  }
}
