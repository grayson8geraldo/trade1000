#!/usr/bin/env python3
"""
Backtesting engine for EMA Momentum Scalping Strategy.

Downloads BTC/USDT 5-minute data from ByBit public API and runs the strategy
against historical data.

Usage:
    pip install -r requirements.txt
    python backtest.py
    python backtest.py --symbol ETHUSDT --days 30
    python backtest.py --symbol BTCUSDT --days 60 --leverage 5
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from tabulate import tabulate


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_bybit_klines(symbol: str = "BTCUSDT", interval: str = "5",
                       days: int = 30) -> pd.DataFrame:
    """Fetch historical kline data from ByBit public API."""

    url = "https://api.bybit.com/v5/market/kline"
    all_data = []
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    limit = 1000  # max per request

    print(f"Fetching {symbol} {interval}m data for {days} days...")

    current_end = end_time
    while current_end > start_time:
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "end": current_end,
            "limit": limit,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            if data.get("retCode") != 0:
                print(f"  API error: {data.get('retMsg')}")
                break

            rows = data.get("result", {}).get("list", [])
            if not rows:
                break

            all_data.extend(rows)
            # ByBit returns data newest first, so last item is oldest
            oldest_ts = int(rows[-1][0])
            current_end = oldest_ts - 1

            print(f"  Fetched {len(all_data)} candles...")
            time.sleep(0.2)  # rate limit

        except requests.RequestException as e:
            print(f"  Request failed: {e}")
            time.sleep(1)
            continue

    if not all_data:
        print("ERROR: No data fetched.")
        return pd.DataFrame()

    # Convert to DataFrame
    # ByBit format: [timestamp, open, high, low, close, volume, turnover]
    df = pd.DataFrame(all_data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"
    ])

    df["timestamp"] = pd.to_numeric(df["timestamp"])
    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp").reset_index(drop=True)

    print(f"  Total candles: {len(df)}")
    print(f"  Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")

    return df


# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all strategy indicators to the dataframe."""

    # EMAs (5M)
    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # RSI (5M)
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR (5M)
    tr = pd.DataFrame({
        "hl": df["high"] - df["low"],
        "hc": (df["high"] - df["close"].shift(1)).abs(),
        "lc": (df["low"] - df["close"].shift(1)).abs(),
    }).max(axis=1)
    df["atr"] = tr.ewm(span=14, adjust=False).mean()

    # Volume MA
    df["vol_ma"] = df["volume"].rolling(window=20).mean()
    df["vol_spike"] = df["volume"] > df["vol_ma"]

    # VWAP (daily reset) — simplified: rolling VWAP
    df["vwap"] = (df["volume"] * (df["high"] + df["low"] + df["close"]) / 3).cumsum() / df["volume"].cumsum()

    # Higher timeframe: 1H indicators (resample)
    df_1h = df.set_index("datetime").resample("1h").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).dropna()
    df_1h["ema50_1h"] = df_1h["close"].ewm(span=50, adjust=False).mean()

    delta_1h = df_1h["close"].diff()
    gain_1h = delta_1h.clip(lower=0)
    loss_1h = (-delta_1h).clip(lower=0)
    avg_gain_1h = gain_1h.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss_1h = loss_1h.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs_1h = avg_gain_1h / avg_loss_1h
    df_1h["rsi_1h"] = 100 - (100 / (1 + rs_1h))

    # Merge 1H data back
    df_1h_merge = df_1h[["ema50_1h", "rsi_1h"]].reset_index()
    df_1h_merge.columns = ["datetime_1h", "ema50_1h", "rsi_1h"]
    df["datetime_floor_1h"] = df["datetime"].dt.floor("h")
    df = df.merge(df_1h_merge, left_on="datetime_floor_1h",
                  right_on="datetime_1h", how="left")
    df["ema50_1h"] = df["ema50_1h"].ffill()
    df["rsi_1h"] = df["rsi_1h"].ffill()

    # 15M indicators (resample)
    df_15m = df.set_index("datetime").resample("15min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).dropna()
    df_15m["ema9_15m"] = df_15m["close"].ewm(span=9, adjust=False).mean()
    df_15m["ema21_15m"] = df_15m["close"].ewm(span=21, adjust=False).mean()

    delta_15m = df_15m["close"].diff()
    gain_15m = delta_15m.clip(lower=0)
    loss_15m = (-delta_15m).clip(lower=0)
    avg_gain_15m = gain_15m.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss_15m = loss_15m.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs_15m = avg_gain_15m / avg_loss_15m
    df_15m["rsi_15m"] = 100 - (100 / (1 + rs_15m))

    df_15m_merge = df_15m[["ema9_15m", "ema21_15m", "rsi_15m"]].reset_index()
    df_15m_merge.columns = ["datetime_15m", "ema9_15m", "ema21_15m", "rsi_15m"]
    df["datetime_floor_15m"] = df["datetime"].dt.floor("15min")
    df = df.merge(df_15m_merge, left_on="datetime_floor_15m",
                  right_on="datetime_15m", how="left")
    df["ema9_15m"] = df["ema9_15m"].ffill()
    df["ema21_15m"] = df["ema21_15m"].ffill()
    df["rsi_15m"] = df["rsi_15m"].ffill()

    # EMA crosses
    df["ema_bull_cross"] = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1))
    df["ema_bear_cross"] = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1))

    # Pullback signals
    df["pullback_long"] = (df["low"] <= df["ema21"] * 1.001) & (df["close"] > df["ema21"]) & (df["close"] > df["open"])
    df["pullback_short"] = (df["high"] >= df["ema21"] * 0.999) & (df["close"] < df["ema21"]) & (df["close"] < df["open"])

    # Cleanup
    df = df.drop(columns=["datetime_floor_1h", "datetime_1h",
                           "datetime_floor_15m", "datetime_15m"], errors="ignore")

    return df


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate long and short signals based on strategy rules."""

    # 1H Trend filter
    htf_bullish = (df["close"] > df["ema50_1h"]) & (df["rsi_1h"] > 45)
    htf_bearish = (df["close"] < df["ema50_1h"]) & (df["rsi_1h"] < 55)

    # 15M Momentum
    m15_bull = (df["ema9_15m"] > df["ema21_15m"]) & (df["rsi_15m"] > 50)
    m15_bear = (df["ema9_15m"] < df["ema21_15m"]) & (df["rsi_15m"] < 50)

    # 5M Triggers
    long_trigger = df["ema_bull_cross"] | df["pullback_long"]
    short_trigger = df["ema_bear_cross"] | df["pullback_short"]

    # RSI filter
    long_rsi = (df["rsi"] > 40) & (df["rsi"] < 65)
    short_rsi = (df["rsi"] > 35) & (df["rsi"] < 60)

    # Volume
    vol_ok = df["vol_spike"]

    # Combined signals
    df["long_signal"] = htf_bullish & m15_bull & long_trigger & long_rsi & vol_ok
    df["short_signal"] = htf_bearish & m15_bear & short_trigger & short_rsi & vol_ok

    return df


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

def run_backtest(
    df: pd.DataFrame,
    initial_balance: float = 100.0,
    risk_pct: float = 2.0,
    leverage: int = 5,
    sl_atr_mult: float = 1.5,
    tp1_rr: float = 1.5,
    tp2_rr: float = 2.5,
    tp3_rr: float = 3.5,
    max_daily_trades: int = 4,
    max_daily_loss_pct: float = 5.0,
) -> dict:
    """Run the backtest simulation."""

    balance = initial_balance
    peak_balance = initial_balance
    trades = []
    in_position = False
    position = {}
    daily_trades = 0
    daily_loss = 0.0
    current_day = None

    for i in range(len(df)):
        row = df.iloc[i]
        dt = row["datetime"]
        day = dt.date()

        # Reset daily counters
        if day != current_day:
            current_day = day
            daily_trades = 0
            daily_loss = 0.0

        # Check daily limits
        daily_loss_limit = balance * (max_daily_loss_pct / 100)
        if daily_trades >= max_daily_trades or daily_loss >= daily_loss_limit:
            continue

        # Manage existing position
        if in_position:
            pos = position
            entry = pos["entry"]
            sl = pos["sl"]
            tp1 = pos["tp1"]
            tp2 = pos["tp2"]
            tp3 = pos["tp3"]

            if pos["direction"] == "long":
                # Check stop loss
                if row["low"] <= sl:
                    pnl = -pos["risk_amount"]
                    balance += pnl
                    daily_loss += abs(pnl)
                    pos["exit"] = sl
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "stop_loss"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                # Check TP3 (best case — simplification: check if high reaches TP levels)
                if row["high"] >= tp3:
                    # Tiered profit
                    sl_dist = entry - sl
                    pnl = (pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry) +
                           pos["position_size"] * 0.3 * (sl_dist * tp2_rr / entry) +
                           pos["position_size"] * 0.2 * (sl_dist * tp3_rr / entry))
                    balance += pnl
                    pos["exit"] = tp3
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp3_full"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                if row["high"] >= tp2:
                    sl_dist = entry - sl
                    pnl = (pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry) +
                           pos["position_size"] * 0.3 * (sl_dist * tp2_rr / entry))
                    # Remaining 20% at breakeven
                    balance += pnl
                    pos["exit"] = tp2
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp2_partial"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                if row["high"] >= tp1:
                    sl_dist = entry - sl
                    pnl = pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry)
                    # Remaining at breakeven (simplified)
                    balance += pnl
                    pos["exit"] = tp1
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp1_partial"
                    trades.append(pos.copy())
                    in_position = False
                    continue

            else:  # short
                if row["high"] >= sl:
                    pnl = -pos["risk_amount"]
                    balance += pnl
                    daily_loss += abs(pnl)
                    pos["exit"] = sl
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "stop_loss"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                if row["low"] <= tp3:
                    sl_dist = sl - entry
                    pnl = (pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry) +
                           pos["position_size"] * 0.3 * (sl_dist * tp2_rr / entry) +
                           pos["position_size"] * 0.2 * (sl_dist * tp3_rr / entry))
                    balance += pnl
                    pos["exit"] = tp3
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp3_full"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                if row["low"] <= tp2:
                    sl_dist = sl - entry
                    pnl = (pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry) +
                           pos["position_size"] * 0.3 * (sl_dist * tp2_rr / entry))
                    balance += pnl
                    pos["exit"] = tp2
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp2_partial"
                    trades.append(pos.copy())
                    in_position = False
                    continue

                if row["low"] <= tp1:
                    sl_dist = sl - entry
                    pnl = pos["position_size"] * 0.5 * (sl_dist * tp1_rr / entry)
                    balance += pnl
                    pos["exit"] = tp1
                    pos["exit_time"] = dt
                    pos["pnl"] = pnl
                    pos["exit_reason"] = "tp1_partial"
                    trades.append(pos.copy())
                    in_position = False
                    continue

            continue  # still in position, no exit triggered

        # Check for new entry signals
        if not in_position:
            atr = row["atr"]
            if pd.isna(atr) or atr <= 0:
                continue

            direction = None
            if row.get("long_signal", False):
                direction = "long"
            elif row.get("short_signal", False):
                direction = "short"

            if direction is None:
                continue

            entry_price = row["close"]
            risk_amount = balance * (risk_pct / 100)

            if direction == "long":
                sl_price = entry_price - atr * sl_atr_mult
                sl_dist = entry_price - sl_price
                tp1_price = entry_price + sl_dist * tp1_rr
                tp2_price = entry_price + sl_dist * tp2_rr
                tp3_price = entry_price + sl_dist * tp3_rr
            else:
                sl_price = entry_price + atr * sl_atr_mult
                sl_dist = sl_price - entry_price
                tp1_price = entry_price - sl_dist * tp1_rr
                tp2_price = entry_price - sl_dist * tp2_rr
                tp3_price = entry_price - sl_dist * tp3_rr

            sl_pct = sl_dist / entry_price
            position_size = min(risk_amount / sl_pct, balance * leverage)

            position = {
                "direction": direction,
                "entry": entry_price,
                "entry_time": dt,
                "sl": sl_price,
                "tp1": tp1_price,
                "tp2": tp2_price,
                "tp3": tp3_price,
                "risk_amount": risk_amount,
                "position_size": position_size,
                "atr": atr,
                "balance_at_entry": balance,
            }
            in_position = True
            daily_trades += 1

        # Track peak balance for drawdown
        peak_balance = max(peak_balance, balance)

    # Close any open position at last price
    if in_position:
        last = df.iloc[-1]
        if position["direction"] == "long":
            pnl = position["position_size"] * (last["close"] - position["entry"]) / position["entry"]
        else:
            pnl = position["position_size"] * (position["entry"] - last["close"]) / position["entry"]
        balance += pnl
        position["exit"] = last["close"]
        position["exit_time"] = last["datetime"]
        position["pnl"] = pnl
        position["exit_reason"] = "end_of_data"
        trades.append(position.copy())

    return {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "trades": trades,
        "peak_balance": peak_balance,
    }


# ============================================================================
# REPORTING
# ============================================================================

def generate_report(result: dict, df: pd.DataFrame):
    """Print a detailed backtest report."""

    trades = result["trades"]
    initial = result["initial_balance"]
    final = result["final_balance"]
    peak = result["peak_balance"]

    print("\n" + "=" * 70)
    print("  BACKTEST REPORT — EMA Momentum Scalping Strategy")
    print("=" * 70)

    if not trades:
        print("\n  No trades generated. Check signal criteria or data period.")
        return

    # Basic stats
    total_trades = len(trades)
    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0

    total_pnl = final - initial
    total_pnl_pct = (total_pnl / initial) * 100

    avg_win = np.mean([t["pnl"] for t in winners]) if winners else 0
    avg_loss = np.mean([abs(t["pnl"]) for t in losers]) if losers else 0
    profit_factor = (sum(t["pnl"] for t in winners) / sum(abs(t["pnl"]) for t in losers)
                     if losers and sum(abs(t["pnl"]) for t in losers) > 0 else float("inf"))

    max_dd = (peak - min(t.get("balance_at_entry", initial) + t["pnl"] for t in trades)) / peak * 100

    # Exit reason breakdown
    exit_reasons = {}
    for t in trades:
        reason = t.get("exit_reason", "unknown")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    # Duration
    date_range = df["datetime"].iloc[-1] - df["datetime"].iloc[0]

    print(f"\n  Data Period:         {df['datetime'].iloc[0].strftime('%Y-%m-%d')} to {df['datetime'].iloc[-1].strftime('%Y-%m-%d')} ({date_range.days} days)")
    print(f"  Total Candles:       {len(df):,}")

    print(f"\n  Initial Balance:     ${initial:.2f}")
    print(f"  Final Balance:       ${final:.2f}")
    print(f"  Net P&L:             ${total_pnl:+.2f} ({total_pnl_pct:+.1f}%)")
    print(f"  Peak Balance:        ${peak:.2f}")
    print(f"  Max Drawdown:        {max_dd:.1f}%")

    print(f"\n  Total Trades:        {total_trades}")
    print(f"  Winners:             {len(winners)} ({win_rate:.1f}%)")
    print(f"  Losers:              {len(losers)} ({100-win_rate:.1f}%)")
    print(f"  Avg Win:             ${avg_win:.2f}")
    print(f"  Avg Loss:            ${avg_loss:.2f}")
    print(f"  Profit Factor:       {profit_factor:.2f}")

    if total_trades > 0:
        best = max(trades, key=lambda t: t["pnl"])
        worst = min(trades, key=lambda t: t["pnl"])
        print(f"\n  Best Trade:          ${best['pnl']:+.2f} ({best['direction']} at {best['entry_time']})")
        print(f"  Worst Trade:         ${worst['pnl']:+.2f} ({worst['direction']} at {worst['entry_time']})")

    print(f"\n  Exit Reasons:")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason:<20} {count:>4} ({count/total_trades*100:.1f}%)")

    # Equity curve summary
    print(f"\n  {'─' * 66}")
    print(f"  Equity Curve (every ~10 trades):")
    print(f"  {'─' * 66}")

    running_balance = initial
    step = max(1, total_trades // 10)
    curve_data = []
    for idx, t in enumerate(trades):
        running_balance += t["pnl"]
        if idx % step == 0 or idx == total_trades - 1:
            curve_data.append([
                idx + 1,
                t.get("entry_time", "").strftime("%Y-%m-%d %H:%M") if hasattr(t.get("entry_time", ""), "strftime") else "",
                t["direction"].upper(),
                f"${t['pnl']:+.2f}",
                f"${running_balance:.2f}",
            ])

    print(tabulate(curve_data, headers=["#", "Date", "Dir", "P&L", "Balance"],
                   tablefmt="simple", stralign="right"))

    # Long vs Short breakdown
    longs = [t for t in trades if t["direction"] == "long"]
    shorts = [t for t in trades if t["direction"] == "short"]

    print(f"\n  {'─' * 66}")
    print(f"  Direction Breakdown:")
    print(f"  {'─' * 66}")

    for label, subset in [("LONG", longs), ("SHORT", shorts)]:
        if not subset:
            continue
        w = len([t for t in subset if t["pnl"] > 0])
        total = len(subset)
        pnl = sum(t["pnl"] for t in subset)
        print(f"  {label:6} — Trades: {total:3}, Win Rate: {w/total*100:.1f}%, Net P&L: ${pnl:+.2f}")

    print("\n" + "=" * 70)

    # Projection
    if total_pnl_pct > 0 and date_range.days > 0:
        daily_return = (final / initial) ** (1 / date_range.days) - 1
        days_to_1000 = np.log(1000 / initial) / np.log(1 + daily_return) if daily_return > 0 else float("inf")
        print(f"\n  PROJECTION (if consistent):")
        print(f"  Avg Daily Return:    {daily_return*100:.2f}%")
        print(f"  Days to $1,000:      {days_to_1000:.0f} trading days")
        print(f"  (This is a projection, not a guarantee)")
    print("")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="EMA Momentum Strategy Backtester")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair (default: BTCUSDT)")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data (default: 30)")
    parser.add_argument("--balance", type=float, default=100.0, help="Initial balance (default: 100)")
    parser.add_argument("--risk", type=float, default=2.0, help="Risk per trade in %% (default: 2.0)")
    parser.add_argument("--leverage", type=int, default=5, help="Leverage (default: 5)")
    parser.add_argument("--save-trades", action="store_true", help="Save trades to JSON file")

    args = parser.parse_args()

    # Fetch data
    df = fetch_bybit_klines(symbol=args.symbol, interval="5", days=args.days)
    if df.empty:
        print("No data available. Check symbol or network connection.")
        return

    # Add indicators
    print("Calculating indicators...")
    df = add_indicators(df)

    # Generate signals
    print("Generating signals...")
    df = generate_signals(df)

    long_count = df["long_signal"].sum()
    short_count = df["short_signal"].sum()
    print(f"  Long signals: {long_count}, Short signals: {short_count}")

    # Run backtest
    print("Running backtest...")
    result = run_backtest(
        df,
        initial_balance=args.balance,
        risk_pct=args.risk,
        leverage=args.leverage,
    )

    # Generate report
    generate_report(result, df)

    # Save trades if requested
    if args.save_trades and result["trades"]:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        output_file = data_dir / f"trades_{args.symbol}_{args.days}d.json"

        serializable_trades = []
        for t in result["trades"]:
            st = {}
            for k, v in t.items():
                if hasattr(v, "isoformat"):
                    st[k] = v.isoformat()
                elif isinstance(v, (np.floating, np.integer)):
                    st[k] = float(v)
                else:
                    st[k] = v
            serializable_trades.append(st)

        with open(output_file, "w") as f:
            json.dump(serializable_trades, f, indent=2)
        print(f"Trades saved to {output_file}")


if __name__ == "__main__":
    main()
