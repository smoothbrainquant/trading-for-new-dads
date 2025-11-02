"""
Generate Mean-Variance Optimization (MVO) Portfolio Weights

This script:
1. Loads daily returns from all backtested strategies
2. Calculates expected returns and covariance matrix
3. Optimizes portfolio weights to maximize Sharpe ratio
4. Applies constraints:
   - All weights >= 0 (no shorts)
   - Weights sum to 1.0
   - Optional caps on specific strategies
5. Outputs optimal weights and portfolio metrics
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import sys
import os
from datetime import datetime
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def load_daily_returns(filepath):
    """Load daily returns from backtest results."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    return df


def calculate_portfolio_metrics(returns_df, weights):
    """
    Calculate portfolio metrics given returns and weights.
    
    Args:
        returns_df: DataFrame with strategy returns
        weights: Dictionary or Series of strategy weights
        
    Returns:
        dict: Portfolio metrics (return, volatility, sharpe)
    """
    # Convert weights to Series if dict
    if isinstance(weights, dict):
        weights = pd.Series(weights)
    
    # Filter to strategies in returns_df
    strategies = [col for col in returns_df.columns if col != 'date']
    weights = weights[strategies]
    weights = weights / weights.sum()  # Normalize
    
    # Drop rows with any NaN
    returns = returns_df[strategies].dropna()
    
    # Calculate portfolio returns
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # Annualize (252 trading days)
    annual_return = portfolio_returns.mean() * 252
    annual_vol = portfolio_returns.std() * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # Max drawdown
    cum_returns = (1 + portfolio_returns).cumprod()
    running_max = cum_returns.expanding().max()
    drawdown = (cum_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
    }


def mvo_optimization(returns_df, strategy_caps=None, min_weight=0.0, risk_free_rate=0.0):
    """
    Perform Mean-Variance Optimization to maximize Sharpe ratio.
    
    Args:
        returns_df: DataFrame with daily returns for each strategy
        strategy_caps: Dict of strategy names to max weights (e.g., {'Mean Reversion': 0.05})
        min_weight: Minimum weight per strategy (default 0.0)
        risk_free_rate: Risk-free rate for Sharpe calculation (default 0.0)
        
    Returns:
        dict: Optimal weights and portfolio metrics
    """
    # Get strategy names (exclude date column)
    strategies = [col for col in returns_df.columns if col != 'date']
    n_strategies = len(strategies)
    
    # Drop rows with any NaN values
    returns = returns_df[strategies].dropna()
    
    if len(returns) == 0:
        raise ValueError("No valid returns data after dropping NaN")
    
    # Calculate expected returns and covariance matrix (annualized)
    mean_returns = returns.mean() * 252  # Annualized
    cov_matrix = returns.cov() * 252  # Annualized
    
    # Objective function: Negative Sharpe ratio (we minimize)
    def neg_sharpe(weights):
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
        return -sharpe  # Negative because we minimize
    
    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
    ]
    
    # Bounds: min_weight <= weight <= cap (or 1.0 if no cap)
    bounds = []
    for strategy in strategies:
        max_weight = strategy_caps.get(strategy, 1.0) if strategy_caps else 1.0
        bounds.append((min_weight, max_weight))
    
    # Initial guess: equal weights
    x0 = np.array([1.0 / n_strategies] * n_strategies)
    
    # Optimize
    result = minimize(
        neg_sharpe,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    if not result.success:
        print(f"WARNING: Optimization did not converge: {result.message}")
    
    # Extract optimal weights
    optimal_weights = pd.Series(result.x, index=strategies)
    
    # Calculate portfolio metrics
    portfolio_return = np.dot(optimal_weights, mean_returns)
    portfolio_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
    sharpe = (portfolio_return - risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
    
    # Calculate max drawdown
    portfolio_returns = (returns * optimal_weights).sum(axis=1)
    cum_returns = (1 + portfolio_returns).cumprod()
    running_max = cum_returns.expanding().max()
    drawdown = (cum_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        'weights': optimal_weights,
        'annual_return': portfolio_return,
        'annual_volatility': portfolio_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'mean_returns': mean_returns,
        'cov_matrix': cov_matrix,
    }


def calculate_correlation_matrix(returns_df):
    """Calculate correlation matrix for strategies."""
    strategies = [col for col in returns_df.columns if col != 'date']
    returns = returns_df[strategies].dropna()
    return returns.corr()


def print_mvo_results(mvo_results, strategy_metrics=None):
    """Print formatted MVO optimization results."""
    print("\n" + "=" * 120)
    print("MEAN-VARIANCE OPTIMIZATION (MVO) RESULTS")
    print("=" * 120)
    
    weights = mvo_results['weights']
    
    print("\nOptimal Portfolio Weights:")
    print("-" * 120)
    
    # Sort by weight descending
    weights_sorted = weights.sort_values(ascending=False)
    
    for strategy, weight in weights_sorted.items():
        if strategy_metrics is not None and strategy in strategy_metrics.index:
            sharpe = strategy_metrics.loc[strategy, 'Sharpe Ratio']
            ann_return = strategy_metrics.loc[strategy, 'Avg Return']
            indicator = "?" if sharpe > 0 else "?"
            print(f"  {indicator} {strategy:<35} | Weight: {weight:>7.2%} | Sharpe: {sharpe:>7.3f} | Return: {ann_return:>7.2%}")
        else:
            print(f"  ? {strategy:<35} | Weight: {weight:>7.2%}")
    
    print("-" * 120)
    print(f"  {'TOTAL':<37} | Weight: {weights.sum():>7.2%}")
    
    print("\nExpected Portfolio Metrics:")
    print("-" * 120)
    print(f"  Expected Annual Return:    {mvo_results['annual_return']:>8.2%}")
    print(f"  Expected Volatility:       {mvo_results['annual_volatility']:>8.2%}")
    print(f"  Expected Sharpe Ratio:     {mvo_results['sharpe_ratio']:>8.3f}")
    print(f"  Expected Max Drawdown:     {mvo_results['max_drawdown']:>8.2%}")
    print("=" * 120)


def main():
    parser = argparse.ArgumentParser(
        description="Generate MVO portfolio weights from backtest results"
    )
    parser.add_argument(
        "--daily-returns",
        type=str,
        default="backtests/results/all_backtests_daily_returns.csv",
        help="Path to daily returns CSV file"
    )
    parser.add_argument(
        "--summary",
        type=str,
        default="backtests/results/all_backtests_summary.csv",
        help="Path to summary CSV file with strategy metrics"
    )
    parser.add_argument(
        "--output-weights",
        type=str,
        default="backtests/results/mvo_weights.csv",
        help="Output path for MVO weights CSV"
    )
    parser.add_argument(
        "--output-correlation",
        type=str,
        default="backtests/results/mvo_correlation.csv",
        help="Output path for correlation matrix CSV"
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Minimum weight per strategy (default: 0.0)"
    )
    parser.add_argument(
        "--cap-negative-sharpe",
        type=float,
        default=0.05,
        help="Cap weight for negative Sharpe strategies (default: 0.05)"
    )
    parser.add_argument(
        "--cap-regime-dependent",
        type=float,
        default=0.05,
        help="Cap weight for regime-dependent strategies (default: 0.05)"
    )
    parser.add_argument(
        "--cap-regime-switching",
        type=float,
        default=0.35,
        help="Cap weight for regime-switching strategies (default: 0.35)"
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print("MEAN-VARIANCE OPTIMIZATION (MVO)")
    print("=" * 120)
    print(f"\nConfiguration:")
    print(f"  Daily returns file: {args.daily_returns}")
    print(f"  Summary file: {args.summary}")
    print(f"  Output weights: {args.output_weights}")
    print(f"  Output correlation: {args.output_correlation}")
    print(f"  Min weight: {args.min_weight:.2%}")
    print(f"  Cap negative Sharpe: {args.cap_negative_sharpe:.2%}")
    print(f"  Cap regime-dependent: {args.cap_regime_dependent:.2%}")
    print(f"  Cap regime-switching: {args.cap_regime_switching:.2%}")
    
    # Load data
    print("\nLoading data...")
    returns_df = load_daily_returns(args.daily_returns)
    summary_df = pd.read_csv(args.summary)
    summary_df = summary_df.set_index('Strategy')
    
    print(f"  ? Loaded {len(returns_df)} days of returns")
    print(f"  ? Found {len([c for c in returns_df.columns if c != 'date'])} strategies")
    
    # Determine strategy caps based on performance
    print("\nApplying strategy caps...")
    strategy_caps = {}
    
    for strategy in returns_df.columns:
        if strategy == 'date':
            continue
            
        if strategy not in summary_df.index:
            print(f"  ? Warning: {strategy} not found in summary")
            continue
        
        sharpe = summary_df.loc[strategy, 'Sharpe Ratio']
        
        # Cap negative Sharpe strategies
        if sharpe < 0:
            strategy_caps[strategy] = args.cap_negative_sharpe
            print(f"  ? {strategy:<35} | Sharpe: {sharpe:>7.3f} | Cap: {args.cap_negative_sharpe:.1%} (Negative)")
        
        # Cap regime-dependent strategies (Kurtosis)
        elif 'Kurtosis' in strategy:
            strategy_caps[strategy] = args.cap_regime_dependent
            print(f"  ? {strategy:<35} | Sharpe: {sharpe:>7.3f} | Cap: {args.cap_regime_dependent:.1%} (Regime-dependent)")
        
        # Cap regime-switching strategies
        elif 'Regime-Switching' in strategy:
            strategy_caps[strategy] = args.cap_regime_switching
            print(f"  ? {strategy:<35} | Sharpe: {sharpe:>7.3f} | Cap: {args.cap_regime_switching:.1%} (Regime-switching)")
        
        else:
            print(f"  ? {strategy:<35} | Sharpe: {sharpe:>7.3f} | Cap: 100.0% (Uncapped)")
    
    # Perform MVO optimization
    print("\nPerforming Mean-Variance Optimization...")
    mvo_results = mvo_optimization(
        returns_df,
        strategy_caps=strategy_caps,
        min_weight=args.min_weight
    )
    
    # Print results
    print_mvo_results(mvo_results, summary_df)
    
    # Calculate correlation matrix
    print("\nCalculating strategy correlation matrix...")
    corr_matrix = calculate_correlation_matrix(returns_df)
    
    # Save results
    print("\nSaving results...")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output_weights), exist_ok=True)
    
    # Save weights
    weights_df = pd.DataFrame({
        'Strategy': mvo_results['weights'].index,
        'Weight': mvo_results['weights'].values,
        'Weight_Pct': mvo_results['weights'].values * 100,
    })
    
    # Add metrics from summary if available
    if summary_df is not None:
        weights_df = weights_df.merge(
            summary_df[['Sharpe Ratio', 'Avg Return', 'Max Drawdown']],
            left_on='Strategy',
            right_index=True,
            how='left'
        )
    
    weights_df = weights_df.sort_values('Weight', ascending=False)
    weights_df.to_csv(args.output_weights, index=False)
    print(f"  ? Saved weights to: {args.output_weights}")
    
    # Save correlation matrix
    corr_matrix.to_csv(args.output_correlation)
    print(f"  ? Saved correlation matrix to: {args.output_correlation}")
    
    # Print correlation insights
    print("\nKey Correlation Insights:")
    print("-" * 120)
    strategies = corr_matrix.columns.tolist()
    for i, strategy1 in enumerate(strategies):
        for strategy2 in strategies[i+1:]:
            corr = corr_matrix.loc[strategy1, strategy2]
            if abs(corr) > 0.5:  # Only show significant correlations
                indicator = "?" if abs(corr) > 0.7 else "?"
                print(f"  {indicator} {strategy1} ? {strategy2}: {corr:>7.3f}")
    
    print("\n" + "=" * 120)
    print("MVO OPTIMIZATION COMPLETE")
    print("=" * 120)
    
    return mvo_results


if __name__ == "__main__":
    main()
