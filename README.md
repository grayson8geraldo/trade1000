# Trade $100 -> $1,000 | Crypto Day Trading Strategy

## Overview

Intraday momentum scalping strategy for ByBit using TradingView charts.
Target: grow $100 to $1,000 over 3-5 weeks.

## Strategy: Multi-Timeframe EMA Momentum + RSI + VWAP

**Core idea:** Trade with the trend on the 1H timeframe, enter on 5M pullbacks
to dynamic support/resistance (EMA), confirmed by momentum (RSI) and
institutional levels (VWAP).

### Assets
- **Primary:** BTC/USDT Perpetual (ByBit)
- **Secondary:** ETH/USDT Perpetual (ByBit)

### Why These Assets
- Highest liquidity on ByBit = tight spreads
- 24/7 market = more trading opportunities
- Reliable technical patterns on 5M/15M timeframes
- Sufficient volatility for scalping

## Project Structure

```
trade1000/
├── README.md                    # This file
├── STRATEGY.md                  # Full strategy rules & playbook
├── indicators/
│   └── ema_momentum_strategy.pine  # TradingView Pine Script indicator
├── backtest/
│   ├── backtest.py              # Python backtesting engine
│   ├── requirements.txt         # Python dependencies
│   └── data/                    # Historical data (gitignored)
├── tools/
│   ├── position_calculator.py   # Position size & risk calculator
│   └── daily_checklist.md       # Pre-trading checklist
└── journal/
    └── trading_journal.md       # Trade journal template
```

## Quick Start

1. Read `STRATEGY.md` thoroughly
2. Add Pine Script indicator to TradingView
3. Paper trade for 3-5 days minimum
4. Use `tools/position_calculator.py` before every trade
5. Log every trade in `journal/trading_journal.md`

## Risk Warning

Trading with leverage carries significant risk. This strategy includes
strict risk management rules — follow them without exception. Never risk
money you cannot afford to lose.
