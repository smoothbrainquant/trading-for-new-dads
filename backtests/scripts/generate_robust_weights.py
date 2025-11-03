"""
Generate Robust Portfolio Weights with Stabilization Techniques

This script implements multiple methods to address MVO instability:
1. L2 Regularization (penalize extreme weights)
2. Shrinkage Estimators (reduce estimation error)
3. Hierarchical Risk Parity (tree-based, no return estimates needed)
4. Equal Risk Contribution (Risk Parity)
5. Maximum Diversification (ignore returns)
"""

import pandas as pd
import numpy as np
import argparse
import os
from scipy.optimize import minimize
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform


def load_backtest_data(daily_returns_file, summary_file):
    """Load backtest daily returns and summary statistics."""
    daily_returns = pd.read_csv(daily_returns_file)
    daily_returns['date'] = pd.to_datetime(daily_returns['date'])
    summary = pd.read_csv(summary_file)
    return daily_returns, summary


def shrink_covariance(cov_matrix, method='ledoit_wolf'):
    """
    Apply shrinkage to covariance matrix to reduce estimation error.
    
    Ledoit-Wolf shrinkage: shrinks sample covariance towards constant correlation matrix
    """
    n = len(cov_matrix)
    
    # Extract variances and correlations
    variances = np.diag(cov_matrix)
    std_devs = np.sqrt(variances)
    
    # Handle zero variance
    std_devs = np.where(std_devs == 0, 1e-8, std_devs)
    
    corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
    corr_matrix = np.clip(corr_matrix, -1, 1)
    np.fill_diagonal(corr_matrix, 1.0)
    
    # Target: constant correlation matrix
    avg_corr = (corr_matrix.sum() - n) / (n * (n - 1))  # Exclude diagonal
    target_corr = np.eye(n) + avg_corr * (np.ones((n, n)) - np.eye(n))
    target_cov = np.outer(std_devs, std_devs) * target_corr
    
    # Shrinkage intensity (simple estimate)
    shrinkage_intensity = 0.3  # 30% towards target
    
    shrunk_cov = (1 - shrinkage_intensity) * cov_matrix + shrinkage_intensity * target_cov
    
    return shrunk_cov


def shrink_returns(returns, method='james_stein'):
    """
    Apply shrinkage to expected returns.
    
    James-Stein estimator: shrinks individual estimates towards grand mean
    """
    grand_mean = returns.mean()
    shrinkage_intensity = 0.5  # 50% towards grand mean
    
    shrunk_returns = (1 - shrinkage_intensity) * returns + shrinkage_intensity * grand_mean
    
    return shrunk_returns


def optimize_mvo_regularized(returns, cov_matrix, min_weight=0.05, lambda_reg=0.1, strategy_caps=None):
    """
    MVO with L2 regularization to penalize extreme weights.
    
    Objective: maximize Sharpe - lambda * sum(weights^2)
    This penalizes concentration and encourages diversification.
    """
    if strategy_caps is None:
        strategy_caps = {}
    
    def objective(weights):
        port_return = np.dot(weights, returns)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = port_return / port_vol if port_vol > 0 else 0
        
        # L2 regularization term
        l2_penalty = lambda_reg * np.sum(weights ** 2)
        
        return -sharpe + l2_penalty  # Minimize
    
    n = len(returns)
    x0 = np.array([1.0 / n] * n)
    
    bounds = [(min_weight, strategy_caps.get(i, 1.0)) for i in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}]
    
    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    return result.x if result.success else x0


def optimize_equal_risk_contribution(cov_matrix, min_weight=0.05, strategy_caps=None):
    """
    Equal Risk Contribution (Risk Parity).
    
    Each strategy contributes equally to portfolio risk.
    More stable than MVO as it doesn't depend on return estimates.
    """
    if strategy_caps is None:
        strategy_caps = {}
    
    def risk_contribution_objective(weights):
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_contrib = np.dot(cov_matrix, weights) / port_vol
        risk_contrib = weights * marginal_contrib
        
        # Target: equal risk contribution
        target = port_vol / len(weights)
        
        return np.sum((risk_contrib - target) ** 2)
    
    n = len(cov_matrix)
    x0 = np.array([1.0 / n] * n)
    
    bounds = [(min_weight, strategy_caps.get(i, 1.0)) for i in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}]
    
    result = minimize(
        risk_contribution_objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    return result.x if result.success else x0


def optimize_max_diversification(cov_matrix, min_weight=0.05, strategy_caps=None):
    """
    Maximum Diversification Portfolio.
    
    Maximizes diversification ratio = weighted avg vol / portfolio vol
    Ignores expected returns, focuses purely on diversification.
    """
    if strategy_caps is None:
        strategy_caps = {}
    
    volatilities = np.sqrt(np.diag(cov_matrix))
    
    def negative_div_ratio(weights):
        weighted_avg_vol = np.dot(weights, volatilities)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -weighted_avg_vol / port_vol if port_vol > 0 else 0
    
    n = len(cov_matrix)
    x0 = np.array([1.0 / n] * n)
    
    bounds = [(min_weight, strategy_caps.get(i, 1.0)) for i in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}]
    
    result = minimize(
        negative_div_ratio,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    return result.x if result.success else x0


def hierarchical_risk_parity(cov_matrix, strategy_names):
    """
    Hierarchical Risk Parity (HRP).
    
    Tree-based allocation that doesn't require return estimates.
    Very stable and robust to estimation error.
    
    Steps:
    1. Compute distance matrix from correlation
    2. Hierarchical clustering
    3. Recursive bisection allocation
    """
    # Convert covariance to correlation
    std_devs = np.sqrt(np.diag(cov_matrix))
    
    # Handle zero variance (strategies with no trades)
    std_devs = np.where(std_devs == 0, 1e-8, std_devs)
    
    corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
    
    # Ensure valid correlation matrix
    corr_matrix = np.clip(corr_matrix, -1, 1)
    np.fill_diagonal(corr_matrix, 1.0)
    
    # Distance matrix: sqrt(0.5 * (1 - correlation))
    dist_matrix = np.sqrt(np.clip(0.5 * (1 - corr_matrix), 0, None))
    
    # Ensure symmetry
    dist_matrix = (dist_matrix + dist_matrix.T) / 2
    np.fill_diagonal(dist_matrix, 0)
    
    # Hierarchical clustering
    condensed_dist = squareform(dist_matrix)
    linkage_matrix = linkage(condensed_dist, method='single')
    
    # Get cluster ordering
    n = len(strategy_names)
    order = _get_quasi_diag(linkage_matrix, n)
    
    # Recursive bisection
    weights = np.ones(n)
    _recursive_bisection(order, cov_matrix, weights)
    
    return weights


def _get_quasi_diag(linkage_matrix, n):
    """Get quasi-diagonal ordering from linkage matrix."""
    order = []
    
    def traverse(node_id):
        if node_id < n:
            order.append(node_id)
        else:
            left = int(linkage_matrix[node_id - n, 0])
            right = int(linkage_matrix[node_id - n, 1])
            traverse(left)
            traverse(right)
    
    traverse(2 * n - 2)
    return order


def _recursive_bisection(order, cov_matrix, weights):
    """Recursively bisect and allocate weights."""
    if len(order) == 1:
        return
    
    # Split into two groups
    mid = len(order) // 2
    left_indices = order[:mid]
    right_indices = order[mid:]
    
    # Calculate cluster variances
    left_cov = cov_matrix[np.ix_(left_indices, left_indices)]
    right_cov = cov_matrix[np.ix_(right_indices, right_indices)]
    
    # Inverse variance weighting
    left_var = np.sum(left_cov)
    right_var = np.sum(right_cov)
    
    total_var = left_var + right_var
    left_weight = 1.0 - left_var / total_var
    right_weight = 1.0 - right_var / total_var
    
    # Normalize
    weight_sum = left_weight + right_weight
    left_weight /= weight_sum
    right_weight /= weight_sum
    
    # Allocate
    for idx in left_indices:
        weights[idx] *= left_weight
    for idx in right_indices:
        weights[idx] *= right_weight
    
    # Recurse
    _recursive_bisection(left_indices, cov_matrix, weights)
    _recursive_bisection(right_indices, cov_matrix, weights)


def apply_min_weight_constraint(weights, min_weight=0.05):
    """Apply minimum weight floor and renormalize."""
    weights = np.maximum(weights, min_weight)
    weights = weights / np.sum(weights)
    return weights


def calculate_portfolio_metrics(weights, returns, cov_matrix):
    """Calculate portfolio metrics."""
    port_return = np.dot(weights, returns)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe = port_return / port_vol if port_vol > 0 else 0
    return port_return, port_vol, sharpe


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate robust portfolio weights with stabilization techniques",
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
        "--output-dir",
        type=str,
        default="backtests/results",
        help="Output directory for weight files",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.05,
        help="Minimum weight per strategy",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Number of days to use (None = use all data)",
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print("ROBUST PORTFOLIO WEIGHT GENERATION")
    print("=" * 120)
    
    # Load data
    daily_returns_df, summary_df = load_backtest_data(args.daily_returns_file, args.summary_file)
    
    # Filter by lookback period if specified
    if args.lookback_days:
        last_date = daily_returns_df['date'].max()
        start_date = last_date - pd.Timedelta(days=args.lookback_days)
        daily_returns_df = daily_returns_df[daily_returns_df['date'] >= start_date].copy()
        print(f"\nUsing last {args.lookback_days} days: {daily_returns_df['date'].min()} to {daily_returns_df['date'].max()}")
    else:
        print(f"\nUsing full period: {daily_returns_df['date'].min()} to {daily_returns_df['date'].max()}")
    
    print(f"Number of days: {len(daily_returns_df)}")
    
    # Get strategy columns
    strategy_cols = [col for col in daily_returns_df.columns if col != 'date']
    daily_returns_df[strategy_cols] = daily_returns_df[strategy_cols].fillna(0)
    
    # Calculate returns and covariance
    mean_returns = daily_returns_df[strategy_cols].mean() * 365
    cov_matrix = daily_returns_df[strategy_cols].cov() * 365
    
    # Identify strategies to cap
    strategies_to_cap = {}
    strategy_cap_indices = {}
    for i, strategy in enumerate(strategy_cols):
        if strategy in summary_df['Strategy'].values:
            sharpe = summary_df[summary_df['Strategy'] == strategy]['Sharpe Ratio'].iloc[0]
            if sharpe < 0 or strategy == 'Kurtosis Factor':
                strategies_to_cap[strategy] = 0.05
                strategy_cap_indices[i] = 0.05
    
    print(f"\nStrategies: {len(strategy_cols)}")
    print(f"Strategies capped at {args.min_weight*100}%: {len(strategies_to_cap)}")
    
    # Apply shrinkage
    print("\n" + "=" * 120)
    print("APPLYING SHRINKAGE ESTIMATORS")
    print("=" * 120)
    shrunk_returns = shrink_returns(mean_returns.values)
    shrunk_cov = shrink_covariance(cov_matrix.values)
    
    print("? Applied James-Stein shrinkage to returns")
    print("? Applied Ledoit-Wolf shrinkage to covariance matrix")
    
    # Generate weights using different methods
    print("\n" + "=" * 120)
    print("GENERATING WEIGHTS WITH MULTIPLE METHODS")
    print("=" * 120)
    
    methods = {}
    
    # 1. Regularized MVO with shrinkage
    print("\n1. Regularized MVO (L2 penalty + shrinkage)...")
    methods['Regularized MVO'] = optimize_mvo_regularized(
        shrunk_returns, shrunk_cov, args.min_weight, lambda_reg=0.5, strategy_caps=strategy_cap_indices
    )
    
    # 2. Equal Risk Contribution (Risk Parity)
    print("2. Equal Risk Contribution (Risk Parity)...")
    methods['Risk Parity'] = optimize_equal_risk_contribution(
        shrunk_cov, args.min_weight, strategy_caps=strategy_cap_indices
    )
    
    # 3. Maximum Diversification
    print("3. Maximum Diversification...")
    methods['Max Diversification'] = optimize_max_diversification(
        shrunk_cov, args.min_weight, strategy_caps=strategy_cap_indices
    )
    
    # 4. Hierarchical Risk Parity
    print("4. Hierarchical Risk Parity (HRP)...")
    hrp_weights = hierarchical_risk_parity(shrunk_cov, strategy_cols)
    hrp_weights = apply_min_weight_constraint(hrp_weights, args.min_weight)
    methods['HRP'] = hrp_weights
    
    # 5. Simple Average (ensemble)
    print("5. Ensemble Average...")
    ensemble_weights = np.mean([methods[k] for k in ['Regularized MVO', 'Risk Parity', 'Max Diversification']], axis=0)
    ensemble_weights = apply_min_weight_constraint(ensemble_weights, args.min_weight)
    methods['Ensemble'] = ensemble_weights
    
    # Display results
    print("\n" + "=" * 120)
    print("WEIGHT COMPARISON ACROSS METHODS")
    print("=" * 120)
    
    results_df = pd.DataFrame({
        'Strategy': strategy_cols
    })
    
    for method_name, weights in methods.items():
        results_df[method_name] = weights
    
    # Add expected returns and Sharpe
    results_df['Expected_Return'] = mean_returns.values
    strategy_to_sharpe = dict(zip(summary_df['Strategy'], summary_df['Sharpe Ratio']))
    results_df['Sharpe_Ratio'] = results_df['Strategy'].map(strategy_to_sharpe)
    
    # Calculate portfolio metrics for each method
    print("\nPortfolio Metrics by Method:")
    print("-" * 120)
    print(f"{'Method':<25} | {'Return':>8} | {'Vol':>8} | {'Sharpe':>8} | {'Max Weight':>10} | {'Min Weight':>10}")
    print("-" * 120)
    
    for method_name, weights in methods.items():
        port_return, port_vol, sharpe = calculate_portfolio_metrics(weights, shrunk_returns, shrunk_cov)
        max_weight = weights.max()
        min_weight = weights.min()
        print(f"{method_name:<25} | {port_return:>7.2%} | {port_vol:>7.2%} | {sharpe:>8.3f} | {max_weight:>9.2%} | {min_weight:>9.2%}")
    
    # Display weight table
    print("\n" + "=" * 120)
    print("DETAILED WEIGHT ALLOCATION")
    print("=" * 120)
    
    # Sort by Regularized MVO weights
    display_df = results_df.sort_values('Regularized MVO', ascending=False)
    
    print(f"\n{'Strategy':<25} | {'Sharpe':>6} | {'Reg MVO':>8} | {'Risk Par':>8} | {'Max Div':>8} | {'HRP':>8} | {'Ensemble':>8}")
    print("-" * 120)
    for _, row in display_df.iterrows():
        print(f"{row['Strategy']:<25} | {row['Sharpe_Ratio']:>6.3f} | "
              f"{row['Regularized MVO']:>7.2%} | {row['Risk Parity']:>7.2%} | "
              f"{row['Max Diversification']:>7.2%} | {row['HRP']:>7.2%} | {row['Ensemble']:>7.2%}")
    
    # Save results
    os.makedirs(args.output_dir, exist_ok=True)
    
    for method_name, weights in methods.items():
        filename = method_name.lower().replace(' ', '_')
        filepath = os.path.join(args.output_dir, f"{filename}_weights.csv")
        
        method_df = pd.DataFrame({
            'Strategy': strategy_cols,
            'Weight': weights,
            'Weight_Pct': weights * 100
        })
        method_df = method_df.sort_values('Weight', ascending=False)
        method_df.to_csv(filepath, index=False)
    
    # Save comparison table
    comparison_file = os.path.join(args.output_dir, "weight_comparison_all_methods.csv")
    results_df.to_csv(comparison_file, index=False)
    
    print("\n" + "=" * 120)
    print("FILES SAVED")
    print("=" * 120)
    print(f"? Weight comparison: {comparison_file}")
    for method_name in methods.keys():
        filename = method_name.lower().replace(' ', '_')
        print(f"? {method_name}: {args.output_dir}/{filename}_weights.csv")
    
    print("\n" + "=" * 120)
    print("RECOMMENDATION")
    print("=" * 120)
    print("""
The ENSEMBLE method is recommended for most stable performance:
- Averages Regularized MVO, Risk Parity, and Max Diversification
- Reduces sensitivity to estimation error
- Balances risk-adjusted returns with diversification

Regularized MVO provides highest Sharpe but may be less stable over time.
Risk Parity/HRP are most stable but ignore return expectations.
""")
    print("=" * 120)


if __name__ == "__main__":
    main()
