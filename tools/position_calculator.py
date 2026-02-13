#!/usr/bin/env python3
"""
Position Size & Risk Calculator for EMA Momentum Scalping Strategy.
Run before every trade to calculate exact position size, stop loss, and take profit levels.

Usage:
    python position_calculator.py
    python position_calculator.py --account 150 --entry 67500 --sl 67200 --direction long
"""

import argparse
import sys


def calculate_position(
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    direction: str,
    risk_pct: float = 2.0,
    leverage: int = 5,
    tp1_rr: float = 1.5,
    tp2_rr: float = 2.5,
    tp3_rr: float = 3.5,
) -> dict:
    """Calculate position size and all trade parameters."""

    risk_amount = account_balance * (risk_pct / 100)

    if direction == "long":
        sl_distance = entry_price - stop_loss_price
    else:
        sl_distance = stop_loss_price - entry_price

    if sl_distance <= 0:
        print("ERROR: Stop loss is on the wrong side of entry price.")
        sys.exit(1)

    sl_distance_pct = (sl_distance / entry_price) * 100

    # Position size based on risk
    position_size_usd = risk_amount / (sl_distance / entry_price)
    max_position = account_balance * leverage
    position_size_usd = min(position_size_usd, max_position)

    # Recalculate actual risk if position was capped
    actual_risk = position_size_usd * (sl_distance / entry_price)
    actual_risk_pct = (actual_risk / account_balance) * 100

    margin_required = position_size_usd / leverage
    contracts = position_size_usd / entry_price

    # Take profit levels
    if direction == "long":
        tp1 = entry_price + sl_distance * tp1_rr
        tp2 = entry_price + sl_distance * tp2_rr
        tp3 = entry_price + sl_distance * tp3_rr
    else:
        tp1 = entry_price - sl_distance * tp1_rr
        tp2 = entry_price - sl_distance * tp2_rr
        tp3 = entry_price - sl_distance * tp3_rr

    # Profit calculations (tiered exit: 50% at TP1, 30% at TP2, 20% at TP3)
    profit_tp1 = position_size_usd * 0.50 * (sl_distance * tp1_rr / entry_price)
    profit_tp2 = position_size_usd * 0.30 * (sl_distance * tp2_rr / entry_price)
    profit_tp3 = position_size_usd * 0.20 * (sl_distance * tp3_rr / entry_price)
    total_profit_if_all_tp = profit_tp1 + profit_tp2 + profit_tp3
    total_profit_pct = (total_profit_if_all_tp / account_balance) * 100

    # Liquidation price (approximate)
    maint_margin_rate = 0.005  # 0.5% for ByBit perpetuals
    if direction == "long":
        liq_price = entry_price * (1 - (1 / leverage) + maint_margin_rate)
    else:
        liq_price = entry_price * (1 + (1 / leverage) - maint_margin_rate)

    return {
        "direction": direction.upper(),
        "account_balance": account_balance,
        "entry_price": entry_price,
        "stop_loss": stop_loss_price,
        "sl_distance": sl_distance,
        "sl_distance_pct": sl_distance_pct,
        "risk_amount": risk_amount,
        "actual_risk": actual_risk,
        "actual_risk_pct": actual_risk_pct,
        "position_size_usd": position_size_usd,
        "margin_required": margin_required,
        "contracts": contracts,
        "leverage": leverage,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "profit_tp1": profit_tp1,
        "profit_tp2": profit_tp2,
        "profit_tp3": profit_tp3,
        "total_profit": total_profit_if_all_tp,
        "total_profit_pct": total_profit_pct,
        "liquidation_price": liq_price,
        "risk_reward_avg": (tp1_rr * 0.5 + tp2_rr * 0.3 + tp3_rr * 0.2),
    }


def print_result(r: dict):
    """Print formatted trade plan."""
    print("\n" + "=" * 60)
    print(f"  TRADE PLAN — {r['direction']}")
    print("=" * 60)

    print(f"\n  Account Balance:    ${r['account_balance']:.2f}")
    print(f"  Leverage:           {r['leverage']}x")

    print(f"\n  Entry Price:        ${r['entry_price']:,.2f}")
    print(f"  Stop Loss:          ${r['stop_loss']:,.2f}  ({r['sl_distance_pct']:.3f}%)")
    print(f"  SL Distance:        ${r['sl_distance']:,.2f}")

    print(f"\n  Risk Amount:        ${r['actual_risk']:.2f}  ({r['actual_risk_pct']:.1f}% of account)")
    print(f"  Position Size:      ${r['position_size_usd']:,.2f}")
    print(f"  Margin Required:    ${r['margin_required']:,.2f}")
    print(f"  Contracts:          {r['contracts']:.6f}")

    print(f"\n  {'─' * 56}")
    print(f"  Take Profit Levels (Tiered Exit):")
    print(f"  {'─' * 56}")
    print(f"  TP1 (50% exit):     ${r['tp1']:,.2f}  →  +${r['profit_tp1']:.2f}")
    print(f"  TP2 (30% exit):     ${r['tp2']:,.2f}  →  +${r['profit_tp2']:.2f}")
    print(f"  TP3 (20% exit):     ${r['tp3']:,.2f}  →  +${r['profit_tp3']:.2f}")
    print(f"  {'─' * 56}")
    print(f"  Total if all TP:    +${r['total_profit']:.2f}  ({r['total_profit_pct']:.1f}% of account)")
    print(f"  Avg Risk:Reward:    1:{r['risk_reward_avg']:.1f}")

    print(f"\n  Liquidation Price:  ${r['liquidation_price']:,.2f}")

    # Safety checks
    print(f"\n  {'─' * 56}")
    print(f"  SAFETY CHECKS:")
    print(f"  {'─' * 56}")

    warnings = []
    if r["actual_risk_pct"] > 3.0:
        warnings.append(f"  ⚠ Risk is {r['actual_risk_pct']:.1f}% — above 3% limit!")
    if r["margin_required"] > r["account_balance"] * 0.9:
        warnings.append(f"  ⚠ Margin uses {r['margin_required']/r['account_balance']*100:.0f}% of account!")
    if r["sl_distance_pct"] > 2.0:
        warnings.append(f"  ⚠ Stop loss distance {r['sl_distance_pct']:.2f}% is wide — consider tighter SL")

    sl_to_liq = abs(r["stop_loss"] - r["liquidation_price"])
    if r["direction"] == "LONG" and r["stop_loss"] < r["liquidation_price"]:
        warnings.append(f"  ⚠ DANGER: Stop loss is BELOW liquidation price!")
    elif r["direction"] == "SHORT" and r["stop_loss"] > r["liquidation_price"]:
        warnings.append(f"  ⚠ DANGER: Stop loss is ABOVE liquidation price!")

    if warnings:
        for w in warnings:
            print(w)
    else:
        print("  ✓ All checks passed.")

    print("\n" + "=" * 60)


def interactive_mode():
    """Interactive mode for quick calculations."""
    print("\n" + "=" * 60)
    print("  EMA MOMENTUM SCALPER — Position Calculator")
    print("=" * 60)

    try:
        account = float(input("\n  Account Balance ($): "))
        entry = float(input("  Entry Price ($): "))
        sl = float(input("  Stop Loss Price ($): "))
        direction = input("  Direction (long/short): ").strip().lower()

        if direction not in ("long", "short"):
            print("  ERROR: Direction must be 'long' or 'short'")
            sys.exit(1)

        # Determine leverage based on account size
        if account < 200:
            default_lev = 5
        elif account < 500:
            default_lev = 5
        else:
            default_lev = 5

        lev_input = input(f"  Leverage (default {default_lev}x): ").strip()
        lev = int(lev_input) if lev_input else default_lev

        risk_input = input("  Risk % (default 2.0%): ").strip()
        risk = float(risk_input) if risk_input else 2.0

        result = calculate_position(
            account_balance=account,
            entry_price=entry,
            stop_loss_price=sl,
            direction=direction,
            risk_pct=risk,
            leverage=lev,
        )
        print_result(result)

    except ValueError:
        print("  ERROR: Invalid number entered.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Cancelled.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Position Size Calculator")
    parser.add_argument("--account", type=float, help="Account balance in USD")
    parser.add_argument("--entry", type=float, help="Entry price")
    parser.add_argument("--sl", type=float, help="Stop loss price")
    parser.add_argument("--direction", choices=["long", "short"], help="Trade direction")
    parser.add_argument("--leverage", type=int, default=5, help="Leverage (default: 5)")
    parser.add_argument("--risk", type=float, default=2.0, help="Risk percentage (default: 2.0)")

    args = parser.parse_args()

    if all([args.account, args.entry, args.sl, args.direction]):
        result = calculate_position(
            account_balance=args.account,
            entry_price=args.entry,
            stop_loss_price=args.sl,
            direction=args.direction,
            risk_pct=args.risk,
            leverage=args.leverage,
        )
        print_result(result)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
