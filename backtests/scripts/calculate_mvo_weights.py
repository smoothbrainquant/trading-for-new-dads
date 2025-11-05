"""
Calculate Mean-Variance Optimization (MVO) Weights

This script calculates optimal portfolio weights using Mean-Variance Optimization
for all working factor strategies (excluding Size and Days from High).

Strategies included:
- Volatility Factor
- Beta Factor
- Carry Factor
- Kurtosis Factor
- Breakout Signal
- Mean Reversion
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import sys
import os

def calculate_mvo_weights(returns_df, risk_aversion=1.0, allow_shorts=False, max_weight=0.40):
    """
    Calculate Mean-Variance Optimization weights.
    
    Args:
        returns_df: DataFrame with daily returns for each strategy (columns are strategies)
        risk_aversion: Risk aversion parameter (higher = more conservative)
        allow_shorts: Whether to allow negative weights
        max_weight: Maximum weight per strategy
    
    Returns:
        dict with optimal weights
    """
    # Remove date column if present
    if 'date' in returns_df.columns:
        returns_df = returns_df.drop(columns=['date'])
    
    # Calculate expected returns (annualized)
    mean_returns = returns_df.mean() * 252
    
    # Calculate covariance matrix (annualized)
    cov_matrix = returns_df.cov() * 252
    
    n_assets = len(returns_df.columns)
    
    # Objective function: minimize -return + risk_aversion * variance
    def objective(weights):
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        # We want to maximize return and minimize variance
        # Minimize: -return + (risk_aversion/2) * variance
        return -portfolio_return + (risk_aversion / 2) * portfolio_variance
    
    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # Weights sum to 1
    ]
    
    # Bounds
    if allow_shorts:
        bounds = [(-max_weight, max_weight) for _ in range(n_assets)]
    else:
        bounds = [(0, max_weight) for _ in range(n_assets)]
    
    # Initial guess (equal weights)
    x0 = np.array([1.0 / n_assets] * n_assets)
    
    # Optimize
    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'ftol': 1e-9, 'maxiter': 1000}
    )
    
    if not result.success:
        print(f"Warning: Optimization did not converge: {result.message}")
    
    # Create weights dictionary
    weights = dict(zip(returns_df.columns, result.x))
    
    # Calculate portfolio metrics
    optimal_weights = result.x
    portfolio_return = np.dot(optimal_weights, mean_returns)
    portfolio_variance = np.dot(optimal_weights, np.dot(cov_matrix, optimal_weights))
    portfolio_std = np.sqrt(portfolio_variance)
    sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
    
    return {
        'weights': weights,
        'expected_return': portfolio_return,
        'expected_volatility': portfolio_std,
        'expected_sharpe': sharpe_ratio,
        'optimization_value': result.fun
    }


def calculate_equal_risk_contribution(returns_df, max_weight=0.40):
    """
    Calculate Equal Risk Contribution (ERC) / Risk Parity weights.
    Each strategy contributes equally to portfolio risk.
    """
    # Remove date column if present
    if 'date' in returns_df.columns:
        returns_df = returns_df.drop(columns=['date'])
    
    # Calculate covariance matrix (annualized)
    cov_matrix = returns_df.cov() * 252
    
    n_assets = len(returns_df.columns)
    
    # Objective: minimize sum of squared differences in risk contribution
    def objective(weights):
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        marginal_contrib = np.dot(cov_matrix, weights)
        risk_contrib = weights * marginal_contrib
        
        # Each strategy should contribute 1/n of total risk
        target_contrib = portfolio_variance / n_assets
        return np.sum((risk_contrib - target_contrib) ** 2)
    
    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    ]
    
    # Bounds (long only)
    bounds = [(0.01, max_weight) for _ in range(n_assets)]
    
    # Initial guess (equal weights)
    x0 = np.array([1.0 / n_assets] * n_assets)
    
    # Optimize
    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'ftol': 1e-9, 'maxiter': 1000}
    )
    
    # Create weights dictionary
    weights = dict(zip(returns_df.columns, result.x))
    
    # Calculate metrics
    mean_returns = returns_df.mean() * 252
    optimal_weights = result.x
    portfolio_return = np.dot(optimal_weights, mean_returns)
    portfolio_variance = np.dot(optimal_weights, np.dot(cov_matrix, optimal_weights))
    portfolio_std = np.sqrt(portfolio_variance)
    sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
    
    return {
        'weights': weights,
        'expected_return': portfolio_return,
        'expected_volatility': portfolio_std,
        'expected_sharpe': sharpe_ratio
    }


def main():
    """Main execution."""
    print("="*120)
    print("MEAN-VARIANCE OPTIMIZATION - PORTFOLIO WEIGHT CALCULATION")
    print("="*120)
    
    # Load daily returns from the comprehensive backtest
    returns_file = "backtests/results/risk_parity_portfolio_size_comparison.csv"
    
    # Check if we have the daily returns file
    daily_returns_file = "backtests/results/all_backtests_daily_returns.csv"
    if os.path.exists(daily_returns_file):
        print(f"\nLoading daily returns from: {daily_returns_file}")
        daily_returns = pd.read_csv(daily_returns_file)
        daily_returns['date'] = pd.to_datetime(daily_returns['date'])
    else:
        print(f"\n❌ Daily returns file not found: {daily_returns_file}")
        print("Please run the full backtest comparison first.")
        return
    
    print(f"✓ Loaded {len(daily_returns)} days of returns")
    print(f"✓ Strategies: {[c for c in daily_returns.columns if c != 'date']}")
    
    # Filter out Size and Days from High (failed strategies)
    exclude_strategies = ['Size Factor', 'Days from High', 'Days from high', 'size', 'days']
    
    strategy_columns = [c for c in daily_returns.columns if c != 'date' and 
                       not any(ex.lower() in c.lower() for ex in exclude_strategies)]
    
    if len(strategy_columns) == 0:
        print("\n❌ No valid strategies found in daily returns")
        return
    
    print(f"\n✓ Using {len(strategy_columns)} strategies (excluding Size and Days from High):")
    for i, strat in enumerate(strategy_columns, 1):
        print(f"  {i}. {strat}")
    
    # Prepare returns DataFrame
    returns_df = daily_returns[['date'] + strategy_columns].copy()
    returns_df = returns_df.dropna()  # Remove any rows with NaN
    
    print(f"\n✓ Clean data: {len(returns_df)} days")
    
    # Calculate correlation matrix
    corr_matrix = returns_df[strategy_columns].corr()
    print("\n" + "="*120)
    print("CORRELATION MATRIX")
    print("="*120)
    print(corr_matrix.round(3))
    
    # Calculate summary statistics
    print("\n" + "="*120)
    print("STRATEGY SUMMARY STATISTICS (Annualized)")
    print("="*120)
    
    summary_stats = []
    for col in strategy_columns:
        returns = returns_df[col].dropna()
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        
        summary_stats.append({
            'Strategy': col,
            'Return': f"{annual_return:.2%}",
            'Volatility': f"{annual_vol:.2%}",
            'Sharpe': f"{sharpe:.3f}"
        })
    
    summary_df = pd.DataFrame(summary_stats)
    print(summary_df.to_string(index=False))
    
    # Calculate different weight schemes
    print("\n" + "="*120)
    print("OPTIMIZATION METHODS")
    print("="*120)
    
    results = {}
    
    # 1. Mean-Variance Optimization (Conservative, λ=2)
    print("\n1. Mean-Variance Optimization (Conservative, Risk Aversion = 2)")
    mvo_conservative = calculate_mvo_weights(
        returns_df[strategy_columns],
        risk_aversion=2.0,
        allow_shorts=False,
        max_weight=0.40
    )
    results['MVO Conservative'] = mvo_conservative
    
    # 2. Mean-Variance Optimization (Moderate, λ=1)
    print("2. Mean-Variance Optimization (Moderate, Risk Aversion = 1)")
    mvo_moderate = calculate_mvo_weights(
        returns_df[strategy_columns],
        risk_aversion=1.0,
        allow_shorts=False,
        max_weight=0.40
    )
    results['MVO Moderate'] = mvo_moderate
    
    # 3. Mean-Variance Optimization (Aggressive, λ=0.5)
    print("3. Mean-Variance Optimization (Aggressive, Risk Aversion = 0.5)")
    mvo_aggressive = calculate_mvo_weights(
        returns_df[strategy_columns],
        risk_aversion=0.5,
        allow_shorts=False,
        max_weight=0.40
    )
    results['MVO Aggressive'] = mvo_aggressive
    
    # 4. Equal Risk Contribution
    print("4. Equal Risk Contribution (Risk Parity)")
    erc = calculate_equal_risk_contribution(returns_df[strategy_columns], max_weight=0.40)
    results['Risk Parity'] = erc
    
    # 5. Equal Weight (baseline)
    print("5. Equal Weight (Baseline)")
    n = len(strategy_columns)
    equal_weights = {col: 1.0/n for col in strategy_columns}
    mean_returns = returns_df[strategy_columns].mean() * 252
    cov_matrix = returns_df[strategy_columns].cov() * 252
    equal_w_array = np.array([1.0/n] * n)
    port_return = np.dot(equal_w_array, mean_returns)
    port_var = np.dot(equal_w_array, np.dot(cov_matrix, equal_w_array))
    port_std = np.sqrt(port_var)
    
    results['Equal Weight'] = {
        'weights': equal_weights,
        'expected_return': port_return,
        'expected_volatility': port_std,
        'expected_sharpe': port_return / port_std if port_std > 0 else 0
    }
    
    # Print results
    print("\n\n" + "="*120)
    print("PORTFOLIO WEIGHT COMPARISON")
    print("="*120)
    
    # Create comparison table
    comparison_data = []
    for method_name, result in results.items():
        row = {'Method': method_name}
        for strat in strategy_columns:
            weight = result['weights'].get(strat, 0)
            row[strat] = f"{weight*100:.1f}%"
        row['Return'] = f"{result['expected_return']:.2%}"
        row['Vol'] = f"{result['expected_volatility']:.2%}"
        row['Sharpe'] = f"{result['expected_sharpe']:.3f}"
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Print weights
    print("\nPortfolio Weights:")
    weight_cols = ['Method'] + strategy_columns
    print(comparison_df[weight_cols].to_string(index=False))
    
    # Print performance metrics
    print("\n\nExpected Performance Metrics:")
    metrics_cols = ['Method', 'Return', 'Vol', 'Sharpe']
    print(comparison_df[metrics_cols].to_string(index=False))
    
    # Recommendations
    print("\n\n" + "="*120)
    print("RECOMMENDATIONS")
    print("="*120)
    
    # Find best Sharpe
    best_sharpe_method = max(results.items(), key=lambda x: x[1]['expected_sharpe'])
    
    print(f"\n🏆 BEST SHARPE RATIO: {best_sharpe_method[0]}")
    print(f"   Expected Return: {best_sharpe_method[1]['expected_return']:.2%}")
    print(f"   Expected Volatility: {best_sharpe_method[1]['expected_volatility']:.2%}")
    print(f"   Expected Sharpe: {best_sharpe_method[1]['expected_sharpe']:.3f}")
    
    print(f"\n   Allocation:")
    for strat, weight in sorted(best_sharpe_method[1]['weights'].items(), 
                                key=lambda x: x[1], reverse=True):
        if weight > 0.01:  # Only show weights > 1%
            print(f"      {weight*100:5.1f}%  {strat}")
    
    # Save results
    output_file = "backtests/results/mvo_portfolio_weights.csv"
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to: {output_file}")
    
    print("\n" + "="*120)
    print("MVO OPTIMIZATION COMPLETE")
    print("="*120)


if __name__ == "__main__":
    main()
