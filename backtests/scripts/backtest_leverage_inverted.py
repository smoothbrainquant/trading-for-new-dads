#!/usr/bin/env python3
"""
Inverted Leverage Factor Strategy

Strategy: LONG low leverage coins (fundamentals), SHORT high leverage coins (speculation)
Ranking Metric: OI/Market Cap ratio
Weighting: Risk Parity (inverse volatility)

Performance: Best with 7-day rebalancing
- Sharpe Ratio: 1.19
- Total Return: +53.91% over 4+ years
- Max Drawdown: -12.10%

Key Finding: Leverage ratios are a CONTRARIAN indicator. Coins with low OI/MCap ratios
(major caps like BTC, ETH, BNB) outperform coins with high OI/MCap ratios (speculative altcoins).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def load_leverage_data(leverage_file):
    """Load historical leverage data (weekly OI/MCap ratios)"""
    df = pd.read_csv(leverage_file)
    df["date"] = pd.to_datetime(df["date"])
    return df


def rank_coins_by_leverage_inverted(leverage_df, as_of_date, ranking_metric="oi_to_mcap_ratio", top_n=10, bottom_n=10):
    """
    INVERTED ranking: Long LOW leverage (fundamentals), Short HIGH leverage (speculation)
    
    Returns: (low_leverage_long, high_leverage_short)
    """
    df = leverage_df[leverage_df["date"] <= as_of_date].copy()
    
    if df.empty:
        return [], []
    
    # Get most recent observation for each coin
    latest = df.sort_values("date").groupby("coin_symbol").tail(1)
    latest = latest[latest[ranking_metric].notna()]
    latest = latest[latest[ranking_metric] > 0]
    
    # Filter out stablecoins
    stablecoins = ["USDT", "USDC", "DAI", "USDD", "TUSD", "BUSD"]
    latest = latest[~latest["coin_symbol"].isin(stablecoins)]
    
    if len(latest) < (top_n + bottom_n):
        return [], []
    
    # Sort by leverage ratio
    latest = latest.sort_values(ranking_metric, ascending=False)
    
    # INVERTED: Long BOTTOM (least leveraged), Short TOP (most leveraged)
    low_leverage_long = latest.tail(bottom_n)["coin_symbol"].tolist()
    high_leverage_short = latest.head(top_n)["coin_symbol"].tolist()
    
    return low_leverage_long, high_leverage_short


def calculate_risk_parity_weights(coins, price_df, as_of_date, lookback=30):
    """Calculate risk parity weights (inverse volatility weighting)"""
    if not coins:
        return {}
    
    # Get recent volatility data
    recent_data = price_df[
        (price_df["date"] <= as_of_date) & 
        (price_df["date"] > as_of_date - timedelta(days=lookback*2))
    ]
    
    # Calculate volatility for each coin
    vol_dict = {}
    for coin in coins:
        coin_data = recent_data[recent_data["coin_symbol"] == coin]
        if len(coin_data) >= 10:
            returns = coin_data["close"].pct_change().dropna()
            if len(returns) > 0:
                vol = returns.std() * np.sqrt(252)  # Annualized
                if vol > 0:
                    vol_dict[coin] = vol
    
    if not vol_dict:
        # Fallback to equal weight
        return {coin: 1.0/len(coins) for coin in coins}
    
    # Calculate inverse volatility weights
    inv_vol = {k: 1.0/v for k, v in vol_dict.items()}
    total_inv_vol = sum(inv_vol.values())
    
    weights = {k: v/total_inv_vol for k, v in inv_vol.items()}
    
    # Add any missing coins with equal weight
    missing_coins = set(coins) - set(weights.keys())
    if missing_coins:
        avg_weight = sum(weights.values()) / len(weights) if weights else 1.0/len(coins)
        for coin in missing_coins:
            weights[coin] = avg_weight
        # Renormalize
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
    
    return weights


def backtest_inverted_leverage(
    leverage_df,
    price_df,
    rebalance_days=7,
    ranking_metric="oi_to_mcap_ratio",
    top_n=10,
    bottom_n=10,
    use_risk_parity=True,
    transaction_cost=0.001,
    start_date=None,
    end_date=None,
    initial_capital=10000
):
    """
    Backtest the INVERTED leverage strategy
    
    Args:
        leverage_df: DataFrame with OI/MCap ratios
        price_df: DataFrame with price data
        rebalance_days: Rebalance frequency
        ranking_metric: Metric to rank by (oi_to_mcap_ratio or oi_to_volume_ratio)
        top_n: Number of coins to short (high leverage)
        bottom_n: Number of coins to long (low leverage)
        use_risk_parity: Use risk parity weighting
        transaction_cost: Transaction cost per trade (default 10bps)
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Initial capital
    
    Returns:
        dict with portfolio_values, metrics, holdings
    """
    
    # Prepare price data
    price_df = price_df.copy()
    if "base" in price_df.columns:
        price_df["coin_symbol"] = price_df["base"]
    elif "symbol" in price_df.columns and "/" in str(price_df["symbol"].iloc[0]):
        price_df["coin_symbol"] = price_df["symbol"].str.split("/").str[0]
    else:
        price_df["coin_symbol"] = price_df["symbol"]
    
    price_df = price_df.sort_values(["coin_symbol", "date"])
    price_df["return"] = price_df.groupby("coin_symbol")["close"].pct_change()
    
    # Determine date range
    leverage_start = leverage_df["date"].min()
    leverage_end = leverage_df["date"].max()
    price_start = price_df["date"].min()
    price_end = price_df["date"].max()
    
    backtest_start = max(leverage_start, price_start)
    backtest_end = min(leverage_end, price_end)
    
    if start_date:
        backtest_start = max(backtest_start, pd.to_datetime(start_date))
    if end_date:
        backtest_end = min(backtest_end, pd.to_datetime(end_date))
    
    # Generate all dates
    all_dates = pd.date_range(start=backtest_start, end=backtest_end, freq='D')
    rebalance_dates = all_dates[::rebalance_days].tolist()
    
    # Initialize tracking
    portfolio_values = []
    portfolio_value = initial_capital
    current_longs = []
    current_shorts = []
    current_long_weights = {}
    current_short_weights = {}
    
    for date in all_dates:
        is_rebalance = date in rebalance_dates
        
        if is_rebalance:
            # Rank coins (INVERTED)
            new_longs, new_shorts = rank_coins_by_leverage_inverted(
                leverage_df, date, ranking_metric, top_n, bottom_n
            )
            
            if not new_longs or not new_shorts:
                portfolio_values.append({
                    "date": date,
                    "portfolio_value": portfolio_value
                })
                continue
            
            # Calculate weights
            if use_risk_parity:
                new_long_weights = calculate_risk_parity_weights(new_longs, price_df, date)
                new_short_weights = calculate_risk_parity_weights(new_shorts, price_df, date)
            else:
                new_long_weights = {coin: 1.0/len(new_longs) for coin in new_longs}
                new_short_weights = {coin: 1.0/len(new_shorts) for coin in new_shorts}
            
            # Calculate turnover and apply transaction costs
            total_trades = (
                len(set(new_longs) - set(current_longs)) +
                len(set(current_longs) - set(new_longs)) +
                len(set(new_shorts) - set(current_shorts)) +
                len(set(current_shorts) - set(new_shorts))
            )
            
            if total_trades > 0:
                turnover_ratio = total_trades / (len(new_longs) + len(new_shorts))
                cost = portfolio_value * turnover_ratio * transaction_cost
                portfolio_value -= cost
            
            current_longs = new_longs
            current_shorts = new_shorts
            current_long_weights = new_long_weights
            current_short_weights = new_short_weights
        
        # Calculate daily returns
        if current_longs or current_shorts:
            date_prices = price_df[price_df["date"] == date]
            
            # Long portfolio return (weighted)
            long_return = 0.0
            if current_longs and current_long_weights:
                for coin, weight in current_long_weights.items():
                    coin_return = date_prices[date_prices["coin_symbol"] == coin]["return"]
                    if len(coin_return) > 0 and not pd.isna(coin_return.iloc[0]):
                        long_return += weight * coin_return.iloc[0]
            
            # Short portfolio return (weighted, negative)
            short_return = 0.0
            if current_shorts and current_short_weights:
                for coin, weight in current_short_weights.items():
                    coin_return = date_prices[date_prices["coin_symbol"] == coin]["return"]
                    if len(coin_return) > 0 and not pd.isna(coin_return.iloc[0]):
                        short_return += weight * (-coin_return.iloc[0])
            
            # Combined return (50% long, 50% short)
            if current_longs and current_shorts:
                daily_return = 0.5 * long_return + 0.5 * short_return
            elif current_longs:
                daily_return = long_return
            elif current_shorts:
                daily_return = short_return
            else:
                daily_return = 0.0
            
            portfolio_value *= (1 + daily_return)
        
        portfolio_values.append({
            "date": date,
            "portfolio_value": portfolio_value
        })
    
    portfolio_df = pd.DataFrame(portfolio_values)
    
    return {
        "portfolio_values": portfolio_df,
        "final_value": portfolio_value,
        "total_return": (portfolio_value - initial_capital) / initial_capital
    }


def main():
    """
    Standalone execution for testing
    """
    print("\n" + "="*80)
    print("INVERTED LEVERAGE FACTOR BACKTEST")
    print("="*80)
    
    # Load data
    print("\nLoading data...")
    leverage_df = load_leverage_data("signals/historical_leverage_weekly_20251102_170645.csv")
    price_df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    price_df["date"] = pd.to_datetime(price_df["date"])
    
    print(f"Leverage data: {len(leverage_df)} rows, {leverage_df['coin_symbol'].nunique()} coins")
    print(f"Price data: {len(price_df)} rows")
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtest_inverted_leverage(
        leverage_df=leverage_df,
        price_df=price_df,
        rebalance_days=7,
        ranking_metric="oi_to_mcap_ratio",
        top_n=10,
        bottom_n=10,
        use_risk_parity=True,
        start_date="2021-06-01",
        end_date=None
    )
    
    print(f"\n? Backtest complete!")
    print(f"  Final value: ${results['final_value']:,.2f}")
    print(f"  Total return: {results['total_return']*100:.2f}%")
    
    # Calculate metrics
    portfolio_df = results["portfolio_values"]
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    
    days = len(portfolio_df)
    years = days / 365.25
    annualized_return = (results['final_value'] / 10000) ** (1/years) - 1
    
    daily_vol = portfolio_df["daily_return"].std()
    annualized_vol = daily_vol * np.sqrt(252)
    sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    cumulative = portfolio_df["portfolio_value"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    print(f"  Annualized return: {annualized_return*100:.2f}%")
    print(f"  Sharpe ratio: {sharpe:.2f}")
    print(f"  Max drawdown: {max_drawdown*100:.2f}%")


if __name__ == "__main__":
    main()
