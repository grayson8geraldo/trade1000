# Trading Strategy: EMA Momentum Scalping

## DISCLAIMER

This is a high-risk strategy using leverage. Past performance does not guarantee
future results. Only trade with money you can afford to lose.

---

## 1. Strategy Philosophy

**Core Principle:** Follow the higher-timeframe trend, enter on lower-timeframe
pullbacks to dynamic support/resistance, exit with strict risk management.

**Edge:** The strategy exploits the tendency of price to revert to mean (EMA)
during trending moves, entering at high-probability locations where institutional
and retail orders cluster (VWAP, EMA zones).

**Mathematical Path to $1,000:**
- Starting capital: $100
- Using 5x leverage
- Average risk per trade: 2% of capital ($2 initially)
- Average reward-to-risk: 2:1
- Win rate target: 55-60%
- Expected daily return: 3-5% of account
- Timeline: ~25-35 trading days

---

## 2. Market & Asset Selection

### Primary Asset: BTC/USDT Perpetual (ByBit)
- Trade during high-volume sessions: London (08:00-12:00 UTC), NY (13:00-17:00 UTC)
- Overlap session (13:00-16:00 UTC) has the highest volatility
- Avoid trading during Asia session unless clear breakout

### Secondary Asset: ETH/USDT Perpetual (ByBit)
- Trade when BTC is ranging/choppy and ETH shows cleaner structure
- ETH often has better intraday swings during altcoin momentum days

### When NOT to Trade
- During major news events (FOMC, CPI, NFP) — check economic calendar
- When daily ATR is < 50% of 20-day average (low volatility)
- When funding rate is extreme (> 0.05% or < -0.05%)
- After 2 consecutive losing trades — mandatory 2-hour break
- After hitting daily loss limit

---

## 3. Timeframes

| Timeframe | Purpose                        |
|-----------|--------------------------------|
| 1H        | Trend direction (EMA 50)       |
| 15M       | Momentum confirmation          |
| 5M        | Entry/exit execution           |
| 1M        | Fine-tuning entry (optional)   |

---

## 4. Indicators Setup (TradingView)

### Chart 1: 5M (Main Execution Chart)
- **EMA 9** (yellow) — fast signal line
- **EMA 21** (blue) — slow signal line
- **EMA 50** (white) — dynamic support/resistance
- **RSI 14** — momentum oscillator (separate panel)
- **VWAP** (purple) — institutional reference level
- **ATR 14** — volatility for stop calculation (separate panel or data window)
- **Volume** — standard volume bars with 20-period MA

### Chart 2: 1H (Trend Reference)
- **EMA 50** (white) — primary trend filter
- **EMA 200** (red) — major trend context
- **RSI 14** — higher-timeframe momentum

### Chart 3: 15M (Confirmation)
- **EMA 9, EMA 21** — momentum alignment
- **RSI 14** — momentum confirmation

---

## 5. Entry Rules

### LONG Setup (All conditions must be met)

#### Trend Filter (1H Chart)
- [ ] Price is ABOVE 1H EMA 50
- [ ] 1H EMA 50 is sloping upward (or flat — not declining)
- [ ] 1H RSI is above 45

#### Momentum Confirmation (15M Chart)
- [ ] 15M EMA 9 is above EMA 21
- [ ] 15M RSI is above 50

#### Entry Trigger (5M Chart)
- [ ] EMA 9 crosses ABOVE EMA 21 (after a pullback)
  — OR —
- [ ] Price pulls back to EMA 21 and bounces (candle closes above EMA 21)
  — OR —
- [ ] Price pulls back to VWAP from above and bounces

#### Confirmation
- [ ] RSI(14) on 5M is between 40 and 65 (not overbought)
- [ ] Current volume candle is above 20-period volume MA
- [ ] No major resistance within 1x ATR above entry

#### Entry Execution
- Enter at the close of the signal candle
- Or place limit order at EMA 21 / VWAP (if pullback is in progress)

---

### SHORT Setup (All conditions must be met)

#### Trend Filter (1H Chart)
- [ ] Price is BELOW 1H EMA 50
- [ ] 1H EMA 50 is sloping downward (or flat — not rising)
- [ ] 1H RSI is below 55

#### Momentum Confirmation (15M Chart)
- [ ] 15M EMA 9 is below EMA 21
- [ ] 15M RSI is below 50

#### Entry Trigger (5M Chart)
- [ ] EMA 9 crosses BELOW EMA 21 (after a bounce)
  — OR —
- [ ] Price bounces to EMA 21 and rejects (candle closes below EMA 21)
  — OR —
- [ ] Price bounces to VWAP from below and rejects

#### Confirmation
- [ ] RSI(14) on 5M is between 35 and 60 (not oversold)
- [ ] Current volume candle is above 20-period volume MA
- [ ] No major support within 1x ATR below entry

---

## 6. Exit Rules

### Stop Loss
- **Initial Stop:** 1.5 x ATR(14) on 5M from entry price
- **Alternative:** Below/above the most recent swing low/high (whichever is tighter)
- **Hard rule:** Never move stop loss further from entry (only toward profit)

### Take Profit (Tiered Exit)
| Portion | Target          | Action                              |
|---------|-----------------|-------------------------------------|
| 50%     | 1:1.5 RR        | Close 50%, move stop to breakeven   |
| 30%     | 1:2.5 RR        | Close 30%, trail stop by 1x ATR     |
| 20%     | 1:3.5 RR / EMA  | Close on EMA 9 cross against or hit |

### Trailing Stop (After TP1 Hit)
- Trail stop at 1.5x ATR below price (long) or above price (short)
- Move to breakeven once TP1 is reached — this is non-negotiable

### Emergency Exit
- Close immediately if 1H EMA 50 is breached against your position
- Close immediately if a major news event is announced

---

## 7. Risk Management Rules

### Per-Trade Risk
| Account Balance | Max Risk Per Trade | Leverage |
|----------------|-------------------|----------|
| $100 - $200    | 2% ($2-$4)        | 5x       |
| $200 - $500    | 2.5% ($5-$12.50)  | 5x       |
| $500 - $1,000  | 2% ($10-$20)      | 3-5x     |

### Daily Limits
- **Max trades per day:** 4
- **Max daily loss:** 5% of account balance
- **Max consecutive losses before break:** 2 (then 2-hour break)
- **Max daily profit target:** 8% (stop trading when reached — avoid overtrading)

### Weekly Limits
- **Max weekly drawdown:** 12% of account
- **If weekly drawdown hit:** Stop trading for 24 hours, review all trades

### Leverage Rules
- **Default:** 5x leverage
- **Reduce to 3x:** After 2 losing days in a row
- **Back to 5x:** After 2 winning days
- **Never exceed 10x** — the account cannot survive the drawdown

### Position Sizing Formula
```
Position Size = (Account Balance × Risk%) / (Stop Loss % without leverage)
Actual Position = Position Size × Leverage

Example:
  Account = $150
  Risk = 2% = $3
  Stop Loss = 0.3% price move
  Position Size = $3 / 0.003 = $1,000
  With 5x leverage: Margin required = $1,000 / 5 = $200
  → Exceeds account! Reduce position.
  Adjusted: use $150 margin × 5x = $750 position
  Actual risk = $750 × 0.3% = $2.25 (1.5% risk) ✓
```

---

## 8. Scaling Plan

### Phase 1: Capital Preservation ($100 → $200)
- **Mindset:** Survival. Prove the strategy works.
- Risk: 2% per trade max
- Leverage: 5x
- Target: 2-3% daily growth
- Duration: ~7-10 trading days
- **Key rule:** If account drops to $80, stop and review for 48 hours

### Phase 2: Controlled Growth ($200 → $500)
- **Mindset:** Build confidence. Increase consistency.
- Risk: 2-2.5% per trade
- Leverage: 5x
- Target: 3-5% daily growth
- Duration: ~8-12 trading days
- **Key rule:** Withdraw $50 to separate wallet (risk-free base)

### Phase 3: Push to Target ($500 → $1,000)
- **Mindset:** Discipline. Don't get greedy.
- Risk: 2% per trade (reduce from Phase 2)
- Leverage: 3-5x
- Target: 2-4% daily growth
- Duration: ~7-10 trading days
- **Key rule:** Once at $750, mentally treat it as your new floor

---

## 9. Trade Execution Checklist

Before every trade, answer YES to all:

1. ☐ Does 1H trend align with my trade direction?
2. ☐ Does 15M momentum confirm?
3. ☐ Is the 5M entry trigger present?
4. ☐ Is volume above average?
5. ☐ Is my stop loss placed at a logical level?
6. ☐ Is my reward-to-risk at least 1.5:1?
7. ☐ Am I within my daily trade limit?
8. ☐ Am I within my daily loss limit?
9. ☐ Have I calculated my position size?
10. ☐ Am I emotionally calm and focused?

**If any answer is NO — do not take the trade.**

---

## 10. Common Patterns to Watch For

### High-Probability Setups
1. **VWAP Bounce + EMA Alignment:** Price pulls back to VWAP which coincides with
   EMA 21 on 5M, all timeframes aligned → highest conviction setup
2. **EMA 9/21 Cross after Squeeze:** After 5M Bollinger Bands squeeze, EMAs cross
   with volume spike → breakout momentum trade
3. **Higher-Low on 5M + 1H Trend:** Price makes a higher low on 5M chart while
   1H is clearly trending → continuation trade

### Traps to Avoid
1. **Chasing extended moves:** If price is > 2 ATR from EMA 21, don't enter
2. **Trading against 1H trend:** Even if 5M setup looks perfect, DON'T do it
3. **Revenge trading:** After a loss, the next trade must meet ALL criteria
4. **Overtrading:** 4 trades max. Quality > quantity.
5. **Moving stop loss:** Once placed, only move toward profit, never away

---

## 11. Session Routine

### Pre-Market (30 min before session)
1. Check economic calendar for news events
2. Mark 1H key levels (support/resistance, EMA 50 position)
3. Note VWAP from daily open
4. Check funding rates on ByBit
5. Determine bias: Long / Short / No Trade

### During Session
1. Wait for setup — don't force trades
2. Execute with checklist
3. Manage open positions per exit rules
4. Log trades immediately after closing

### Post-Session (15 min)
1. Update trading journal
2. Calculate daily P&L
3. Review each trade: what worked, what didn't
4. Note lessons for tomorrow
5. Close TradingView — walk away

---

## 12. Psychological Rules

1. **The market will be there tomorrow.** Missing a trade costs nothing.
   Taking a bad trade costs everything.
2. **Follow the system.** Every deviation weakens discipline.
3. **Accept losses.** They are a cost of business, not failure.
4. **No hope trading.** If the thesis is invalidated, exit immediately.
5. **Journal everything.** You can't improve what you don't measure.
