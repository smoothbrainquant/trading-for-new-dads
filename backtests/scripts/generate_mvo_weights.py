"""
Generate Strategy Weights Using Mean-Variance Optimization (MVO)

This script reads backtest daily returns and generates portfolio weights using
Mean-Variance Optimization to maximize the Sharpe ratio. It supports:
- Constrained optimization with strategy caps
- Minimum weight floors for diversification
- Identification of negative/regime-dependent strategies for capping
"""

import pandas as pd
import numpy as np
import argparse
import os
from scipy.optimize import minimize


def load_backtest_data(daily_returns_file, summary_file):
    """
    Load backtest daily returns and summary statistics.
    
    Args:
        daily_returns_file: Path to daily returns CSV
        summary_file: Path to summary CSV with strategy metrics
        
    Returns:
        tuple: (daily_returns_df, summary_df)
    """
    daily_returns = pd.read_csv(daily_returns_file)
    daily_returns['date'] = pd.to_datetime(daily_returns['date'])
    
    summary = pd.read_csv(summary_file)
    
    return daily_returns, summary


def calculate_portfolio_metrics(weights, returns, cov_matrix):
    """
    Calculate portfolio return, volatility, and Sharpe ratio.
    
    Args:
        weights: Array of portfolio weights
        returns: Array of expected returns for each strategy
        cov_matrix: Covariance matrix of returns
        
    Returns:
        tuple: (return, volatility, sharpe_ratio)
    """
    portfolio_return = np.dot(weights, returns)
    portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
    
    return portfolio_return, portfolio_vol, sharpe


def negative_sharpe(weights, returns, cov_matrix):
    """Objective function to minimize (negative Sharpe ratio)."""
    _, _, sharpe = calculate_portfolio_metrics(weights, returns, cov_matrix)
    return -sharpe


def optimize_portfolio_mvo(daily_returns_df, summary_df, strategy_caps=None, min_weight=0.0):
    """
    Optimize portfolio weights using Mean-Variance Optimization.
    
    Args:
        daily_returns_df: DataFrame with daily returns for each strategy
        summary_df: DataFrame with strategy summary metrics
        strategy_caps: Dict of strategy names to maximum weights
        min_weight: Minimum weight per strategy (default 0%)
        
    Returns:
        pd.DataFrame: DataFrame with optimized weights
    """
    if strategy_caps is None:
        strategy_caps = {}
    
    # Get strategy columns (exclude date)
    strategy_cols = [col for col in daily_returns_df.columns if col != 'date']
    
    # Calculate expected returns (annualized mean)
    mean_returns = daily_returns_df[strategy_cols].mean() * 365
    
    # Calculate covariance matrix (annualized)
    cov_matrix = daily_returns_df[strategy_cols].cov() * 365
    
    # Number of strategies
    n_strategies = len(strategy_cols)
    
    # Initial guess (equal weights)
    x0 = np.array([1.0 / n_strategies] * n_strategies)
    
    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}  # Weights sum to 1
    ]
    
    # Bounds for each strategy
    bounds = []
    for i, strategy in enumerate(strategy_cols):
        upper_bound = strategy_caps.get(strategy, 1.0)
        bounds.append((min_weight, upper_bound))
    
    # Optimize
    result = minimize(
        negative_sharpe,
        x0,
        args=(mean_returns.values, cov_matrix.values),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    if not result.success:
        print(f"WARNING: Optimization did not converge: {result.message}")
    
    # Extract optimal weights
    optimal_weights = result.x
    
    # Create results DataFrame
    weights_df = pd.DataFrame({
        'Strategy': strategy_cols,
        'Weight': optimal_weights,
        'Expected_Return': mean_returns.values,
        'Weight_Pct': optimal_weights * 100
    })
    
    # Add Sharpe ratios from summary
    strategy_to_sharpe = dict(zip(summary_df['Strategy'], summary_df['Sharpe Ratio']))
    weights_df['Sharpe_Ratio'] = weights_df['Strategy'].map(strategy_to_sharpe)
    
    # Sort by weight descending
    weights_df = weights_df.sort_values('Weight', ascending=False)
    
    # Calculate portfolio metrics
    portfolio_return, portfolio_vol, portfolio_sharpe = calculate_portfolio_metrics(
        optimal_weights, mean_returns.values, cov_matrix.values
    )
    
    return weights_df, portfolio_return, portfolio_vol, portfolio_sharpe, cov_matrix


def print_mvo_weights(weights_df, portfolio_return, portfolio_vol, portfolio_sharpe, 
                      summary_df, strategy_caps=None, min_weight=0.0):
    """Print formatted MVO weights table."""
    print("\n" + "=" * 120)
    print("MEAN-VARIANCE OPTIMIZATION (MVO) PORTFOLIO WEIGHTS")
    print("=" * 120)
    
    if strategy_caps is None:
        strategy_caps = {}
    
    weight_sum = weights_df['Weight'].sum()
    
    print(f"\nOptimization Method: Mean-Variance Optimization (maximize Sharpe ratio)")
    if min_weight > 0:
        print(f"Minimum weight floor: {min_weight*100:.1f}%")
    if strategy_caps:
        print(f"Strategy caps applied:")
        for strategy, cap in strategy_caps.items():
            print(f"  - {strategy}: {cap*100:.0f}%")
    print(f"Strategies included: {len(weights_df)}")
    print(f"Total weight: {weight_sum:.6f} (should be 1.0)")
    
    # Identify capped and negative Sharpe strategies
    capped_strategies = []
    negative_sharpe_strategies = []
    
    for _, row in weights_df.iterrows():
        if row['Strategy'] in strategy_caps:
            capped_strategies.append(row['Strategy'])
        if row['Sharpe_Ratio'] < 0:
            negative_sharpe_strategies.append(row['Strategy'])
    
    if capped_strategies:
        print(f"\nCapped strategies ({len(capped_strategies)}):")
        for strategy in capped_strategies:
            cap = strategy_caps[strategy]
            print(f"  - {strategy}: capped at {cap*100:.0f}%")
    
    if negative_sharpe_strategies:
        print(f"\nNegative Sharpe strategies ({len(negative_sharpe_strategies)}):")
        for strategy in negative_sharpe_strategies:
            sharpe = weights_df[weights_df['Strategy'] == strategy]['Sharpe_Ratio'].iloc[0]
            print(f"  - {strategy}: Sharpe = {sharpe:.3f}")
    
    print("\nOptimal Portfolio Allocation:")
    print("-" * 120)
    for _, row in weights_df.iterrows():
        sharpe_indicator = "?" if row['Sharpe_Ratio'] > 0 else "?"
        capped = " [CAPPED]" if row['Strategy'] in strategy_caps else ""
        print(
            f"  {sharpe_indicator} {row['Strategy']:<25} | Sharpe: {row['Sharpe_Ratio']:>8.3f} | "
            f"Weight: {row['Weight']:>8.4f} ({row['Weight_Pct']:>6.2f}%){capped}"
        )
    
    print("\n" + "-" * 120)
    print(f"  {'TOTAL':<27} | {'':>8} | Weight: {weight_sum:>8.4f} ({weight_sum*100:>6.2f}%)")
    
    print("\nOptimized Portfolio Metrics:")
    print("-" * 120)
    print(f"  Expected Annual Return:     {portfolio_return:>8.2%}")
    print(f"  Expected Annual Volatility: {portfolio_vol:>8.2%}")
    print(f"  Expected Sharpe Ratio:      {portfolio_sharpe:>8.3f}")
    
    # Calculate expected max drawdown (weighted average)
    merged = summary_df.merge(weights_df[['Strategy', 'Weight']], on='Strategy', how='inner')
    expected_max_dd = (merged['Max Drawdown'] * merged['Weight']).sum()
    print(f"  Expected Max Drawdown:      {expected_max_dd:>8.2%}")
    print("=" * 120)


def identify_strategies_to_cap(summary_df, regime_dependent_strategies=None):
    """
    Identify strategies that should be capped at 5%.
    
    Criteria:
    - Negative Sharpe ratio (non-performing)
    - Regime-dependent strategies
    
    Args:
        summary_df: DataFrame with strategy metrics
        regime_dependent_strategies: List of regime-dependent strategy names
        
    Returns:
        dict: Strategy names to cap percentage
    """
    if regime_dependent_strategies is None:
        regime_dependent_strategies = []
    
    strategies_to_cap = {}
    
    print("\n" + "=" * 120)
    print("IDENTIFYING STRATEGIES TO CAP")
    print("=" * 120)
    
    # Negative Sharpe strategies
    negative_sharpe = summary_df[summary_df['Sharpe Ratio'] < 0]
    print(f"\nNegative/Non-Performing Strategies (Sharpe < 0): {len(negative_sharpe)}")
    for _, row in negative_sharpe.iterrows():
        strategy = row['Strategy']
        sharpe = row['Sharpe Ratio']
        print(f"  ? {strategy:<25} | Sharpe: {sharpe:>8.3f} | CAP AT 5%")
        strategies_to_cap[strategy] = 0.05
    
    # Regime-dependent strategies
    if regime_dependent_strategies:
        print(f"\nRegime-Dependent Strategies: {len(regime_dependent_strategies)}")
        for strategy in regime_dependent_strategies:
            if strategy in summary_df['Strategy'].values:
                sharpe = summary_df[summary_df['Strategy'] == strategy]['Sharpe Ratio'].iloc[0]
                print(f"  ? {strategy:<25} | Sharpe: {sharpe:>8.3f} | CAP AT 5% (regime-dependent)")
                strategies_to_cap[strategy] = 0.05
    
    print("\n" + "=" * 120)
    
    return strategies_to_cap


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate portfolio weights using Mean-Variance Optimization (MVO)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--daily-returns-file",
        type=str,
        default="backtests/results/all_backtests_daily_returns.csv",
        help="Path to daily returns CSV file",
    )
    parser.add_argument(
        "--summary-file",
        type=str,
        default="backtests/results/all_backtests_summary.csv",
        help="Path to summary CSV file",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="backtests/results/mvo_weights.csv",
        help="Output file for MVO weights CSV",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Minimum weight per strategy (0.0 = no floor)",
    )
    parser.add_argument(
        "--cap-negative",
        action="store_true",
        default=True,
        help="Cap negative Sharpe strategies at 5%",
    )
    parser.add_argument(
        "--regime-dependent",
        type=str,
        nargs="*",
        default=["Kurtosis Factor"],
        help="List of regime-dependent strategies to cap at 5%",
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print("GENERATING MVO PORTFOLIO WEIGHTS")
    print("=" * 120)
    print(f"\nInput files:")
    print(f"  Daily returns: {args.daily_returns_file}")
    print(f"  Summary:       {args.summary_file}")
    print(f"\nOutput file: {args.output_file}")
    print(f"Minimum weight: {args.min_weight*100:.1f}%")
    print(f"Cap negative Sharpe: {args.cap_negative}")
    print(f"Regime-dependent strategies: {', '.join(args.regime_dependent)}")
    
    # Load data
    daily_returns_df, summary_df = load_backtest_data(args.daily_returns_file, args.summary_file)
    
    print(f"\nLoaded {len(summary_df)} strategies")
    print(f"Date range: {daily_returns_df['date'].min()} to {daily_returns_df['date'].max()}")
    print(f"Number of days: {len(daily_returns_df)}")
    
    # Identify strategies to cap
    strategies_to_cap = identify_strategies_to_cap(summary_df, args.regime_dependent)
    
    # Perform MVO
    print("\n" + "=" * 120)
    print("RUNNING MEAN-VARIANCE OPTIMIZATION")
    print("=" * 120)
    print("\nOptimizing portfolio weights to maximize Sharpe ratio...")
    
    weights_df, portfolio_return, portfolio_vol, portfolio_sharpe, cov_matrix = optimize_portfolio_mvo(
        daily_returns_df,
        summary_df,
        strategy_caps=strategies_to_cap,
        min_weight=args.min_weight
    )
    
    # Print results
    print_mvo_weights(
        weights_df,
        portfolio_return,
        portfolio_vol,
        portfolio_sharpe,
        summary_df,
        strategy_caps=strategies_to_cap,
        min_weight=args.min_weight
    )
    
    # Save weights to file
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    weights_df.to_csv(args.output_file, index=False)
    print(f"\n? MVO weights saved to: {args.output_file}")
    
    # Print correlation matrix
    print("\n" + "=" * 120)
    print("STRATEGY CORRELATION MATRIX")
    print("=" * 120)
    strategy_cols = [col for col in daily_returns_df.columns if col != 'date']
    corr_matrix = daily_returns_df[strategy_cols].corr()
    print(corr_matrix.round(3))
    
    # Save correlation matrix
    corr_file = args.output_file.replace("_weights.csv", "_correlation.csv")
    corr_matrix.to_csv(corr_file)
    print(f"\n? Correlation matrix saved to: {corr_file}")
    
    print("\n" + "=" * 120)
    print("MVO OPTIMIZATION COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
