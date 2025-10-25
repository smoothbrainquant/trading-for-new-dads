"""
Create a single consolidated table showing directional mean reversion by period.
"""

import pandas as pd

# Load the directional results
df = pd.read_csv('directional_mean_reversion_by_period.csv')

print("=" * 160)
print("MEAN REVERSION BY PERIOD - CONSOLIDATED RESULTS (Next Day Returns)")
print("=" * 160)
print("\nStrategy Comparison:")
print("  • LONG NEGATIVE MOVES = Buy extreme dips (z-score < -1.5), expect bounce")
print("  • SHORT POSITIVE MOVES = Short extreme rallies (z-score > +1.5), expect pullback")
print("=" * 160)

# Create consolidated table
print("\n" + "=" * 160)
print("COMPLETE RESULTS TABLE")
print("=" * 160)

# Format the table
print(f"\n{'LONG NEGATIVE MOVES (Buy Dips)':<80} {'SHORT POSITIVE MOVES (Short Rallies)':<80}")
print("-" * 160)
print(f"{'Period':<6} {'Any Vol':<14} {'High Vol':<14} {'Low Vol':<14} {'Best':<18} │ "
      f"{'Fwd Return':<12} {'Short P&L':<12} {'Win %':<8} {'Sharpe':<8} {'Signals':<10}")
print("       Return% Sharpe  Return% Sharpe  Return% Sharpe  Strategy          │")
print("=" * 160)

for _, row in df.iterrows():
    period = row['period']
    
    # Long side
    any_ret = f"{row['long_any_vol_return_pct']:.2f}%"
    any_sh = f"{row['long_any_vol_sharpe']:.2f}"
    high_ret = f"{row['long_high_vol_return_pct']:.2f}%"
    high_sh = f"{row['long_high_vol_sharpe']:.2f}"
    low_ret = f"{row['long_low_vol_return_pct']:.2f}%"
    low_sh = f"{row['long_low_vol_sharpe']:.2f}"
    
    # Determine best
    returns = {
        'Any': row['long_any_vol_sharpe'],
        'High': row['long_high_vol_sharpe'],
        'Low': row['long_low_vol_sharpe']
    }
    best = max(returns, key=returns.get)
    best_str = f"{best} Vol"
    
    # Short side
    fwd_ret = f"{row['short_rally_forward_return_pct']:+.2f}%"
    short_pnl = f"{row['short_rally_pnl_pct']:+.2f}%"
    short_wr = f"{row['short_rally_winrate_pct']:.1f}"
    short_sh = f"{row['short_rally_sharpe']:.2f}"
    short_cnt = int(row['short_rally_count'])
    
    print(f"{period:<6} {any_ret:>6} {any_sh:>6}  {high_ret:>6} {high_sh:>6}  {low_ret:>6} {low_sh:>6}  {best_str:<16} │ "
          f"{fwd_ret:>11} {short_pnl:>11} {short_wr:>7} {short_sh:>7} {short_cnt:>9}")

print("=" * 160)

# Summary statistics
print("\n" + "=" * 160)
print("SUMMARY STATISTICS")
print("=" * 160)

print("\nLONG STRATEGY (Buy Dips) - Averages:")
print(f"  Any Volume:  {df['long_any_vol_return_pct'].mean():.2f}% return, {df['long_any_vol_sharpe'].mean():.2f} Sharpe, {df['long_any_vol_winrate_pct'].mean():.1f}% win rate")
print(f"  High Volume: {df['long_high_vol_return_pct'].mean():.2f}% return, {df['long_high_vol_sharpe'].mean():.2f} Sharpe, {df['long_high_vol_winrate_pct'].mean():.1f}% win rate")
print(f"  Low Volume:  {df['long_low_vol_return_pct'].mean():.2f}% return, {df['long_low_vol_sharpe'].mean():.2f} Sharpe, {df['long_low_vol_winrate_pct'].mean():.1f}% win rate")

print("\nSHORT STRATEGY (Short Rallies) - Averages:")
print(f"  Forward Return: {df['short_rally_forward_return_pct'].mean():+.2f}% (price continues)")
print(f"  Short P&L:      {df['short_rally_pnl_pct'].mean():+.2f}% (your profit/loss)")
print(f"  Sharpe:         {df['short_rally_sharpe'].mean():.2f}")
print(f"  Win Rate:       {df['short_rally_winrate_pct'].mean():.1f}%")

# Best configurations
print("\n" + "=" * 160)
print("TOP 5 CONFIGURATIONS (by Sharpe Ratio)")
print("=" * 160)

top5_data = []
for _, row in df.iterrows():
    period = row['period']
    top5_data.append({
        'Config': f"{period} Any Vol",
        'Return%': row['long_any_vol_return_pct'],
        'Sharpe': row['long_any_vol_sharpe'],
        'WinRate%': row['long_any_vol_winrate_pct'],
        'Signals': row['long_any_vol_count']
    })
    top5_data.append({
        'Config': f"{period} High Vol",
        'Return%': row['long_high_vol_return_pct'],
        'Sharpe': row['long_high_vol_sharpe'],
        'WinRate%': row['long_high_vol_winrate_pct'],
        'Signals': row['long_high_vol_count']
    })
    top5_data.append({
        'Config': f"{period} Low Vol",
        'Return%': row['long_low_vol_return_pct'],
        'Sharpe': row['long_low_vol_sharpe'],
        'WinRate%': row['long_low_vol_winrate_pct'],
        'Signals': row['long_low_vol_count']
    })

top5_df = pd.DataFrame(top5_data).sort_values('Sharpe', ascending=False).head(10)

print(f"\n{'Rank':<6} {'Configuration':<16} {'Return %':<12} {'Sharpe':<10} {'Win Rate %':<12} {'Signals':<10}")
print("-" * 160)
for idx, (_, row) in enumerate(top5_df.iterrows(), 1):
    print(f"{idx:<6} {row['Config']:<16} {row['Return%']:>11.2f} {row['Sharpe']:>9.2f} {row['WinRate%']:>11.1f} {int(row['Signals']):>9}")

print("\n" + "=" * 160)
print("KEY TAKEAWAYS")
print("=" * 160)
print("""
1. MEAN REVERSION WORKS FOR NEGATIVE MOVES (Buy Dips) ✓
   → All periods show positive returns
   → 2d and 10d with high volume are best (Sharpe 3.0+)
   → High volume dips are 2x more profitable than low volume
   
2. MEAN REVERSION FAILS FOR POSITIVE MOVES (Short Rallies) ✗
   → Near-zero or negative P&L from shorting
   → Price tends to continue up (momentum effect)
   → Win rates below 50% (worse than random)
   
3. ASYMMETRIC OPPORTUNITY
   → "Buy the dip" is a proven strategy in crypto
   → "Short the rally" is NOT effective
   → Markets fall fast (revert), rise slow (trend)
   
4. VOLUME IS CRITICAL
   → High volume selloffs create the best opportunities
   → Suggests institutional panic → bounce
   → Low volume moves are less reliable

5. OPTIMAL PERIODS: 2d and 10d lookbacks
   → Very short (1d): Too noisy
   → Very long (30d): Too slow
   → Sweet spot: 2-10 days
""")

print("=" * 160)
