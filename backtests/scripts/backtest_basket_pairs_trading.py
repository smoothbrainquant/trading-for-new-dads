#!/usr/bin/env python3
"""
Backtest for Basket Pairs Trading Strategy

This script backtests cryptocurrency pairs trading strategies based on 
basket divergence signals. The core logic:

1. Load historical divergence signals (z-scores, percentile ranks)
2. Enter positions when signals trigger (LONG outperformers, SHORT underperformers)
3. Exit based on mean reversion, time-based exit, stop loss, or take profit
4. Track performance metrics: Sharpe, drawdown, win rate, turnover

Key Features:
- No lookahead bias: Signals on day t, returns from day t+1
- Multiple exit strategies: mean reversion, time-based, stop loss, take profit
- Position sizing: equal-weight or z-score weighted
- Portfolio constraints: max positions per category and total
- Market neutral option: balance long/short exposure
- Transaction costs modeling
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestConfig:
    """Configuration parameters for pairs trading backtest"""
    # Signal parameters
    signal_file: str = 'signals/basket_divergence_signals_full.csv'
    price_file: str = 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
    
    # Entry thresholds
    long_entry_threshold: float = -1.5  # z-score threshold for LONG entry
    short_entry_threshold: float = 1.5  # z-score threshold for SHORT entry
    
    # Exit rules
    holding_period: int = 10  # days to hold position (time-based exit)
    exit_z_threshold: float = 0.5  # Exit when |z-score| < threshold (mean reversion)
    stop_loss: float = 0.10  # Exit if loss > 10%
    take_profit: float = 0.15  # Exit if gain > 15%
    
    # Position sizing
    position_size_method: str = 'equal_weight'  # 'equal_weight' or 'z_score_weight'
    max_positions_per_category: int = 3
    max_total_positions: int = 20
    target_leverage: float = 1.0  # 1.0 = 100% long, 100% short (dollar neutral)
    
    # Transaction costs
    transaction_cost: float = 0.001  # 10 bps per trade
    slippage: float = 0.0005  # 5 bps slippage
    
    # Portfolio settings
    initial_capital: float = 100000.0
    market_neutral: bool = True  # Balance long/short exposure
    
    # Backtest period
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # Categories to trade (None = all categories)
    categories: Optional[List[str]] = None


class Position:
    """Represents a single trading position"""
    def __init__(self, symbol: str, category: str, signal: str, entry_date: pd.Timestamp,
                 entry_price: float, entry_z_score: float, position_size: float,
                 market_cap: float):
        self.symbol = symbol
        self.category = category
        self.signal = signal  # 'LONG' or 'SHORT'
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.entry_z_score = entry_z_score
        self.position_size = position_size  # Dollar value
        self.market_cap = market_cap
        
        self.exit_date: Optional[pd.Timestamp] = None
        self.exit_price: Optional[float] = None
        self.exit_z_score: Optional[float] = None
        self.exit_reason: Optional[str] = None
        self.pnl: Optional[float] = None
        self.return_pct: Optional[float] = None
        self.hold_days: int = 0
        
    def update_pnl(self, current_price: float, transaction_cost: float = 0.0):
        """Calculate current P&L for the position"""
        if self.signal == 'LONG':
            pnl = (current_price / self.entry_price - 1) * self.position_size
        else:  # SHORT
            pnl = (1 - current_price / self.entry_price) * self.position_size
        
        # Subtract transaction costs (entry + potential exit)
        pnl -= 2 * transaction_cost * self.position_size
        return pnl
    
    def close(self, exit_date: pd.Timestamp, exit_price: float, 
              exit_z_score: float, exit_reason: str, transaction_cost: float):
        """Close the position and record metrics"""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_z_score = exit_z_score
        self.exit_reason = exit_reason
        self.hold_days = (exit_date - self.entry_date).days
        
        # Calculate return
        if self.signal == 'LONG':
            self.return_pct = (exit_price / self.entry_price - 1)
        else:  # SHORT
            self.return_pct = (1 - exit_price / self.entry_price)
        
        # Calculate P&L including transaction costs
        self.pnl = self.return_pct * self.position_size - 2 * transaction_cost * self.position_size
    
    def to_dict(self) -> dict:
        """Convert position to dictionary for logging"""
        return {
            'symbol': self.symbol,
            'category': self.category,
            'signal': self.signal,
            'entry_date': self.entry_date,
            'exit_date': self.exit_date,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'entry_z_score': self.entry_z_score,
            'exit_z_score': self.exit_z_score,
            'position_size': self.position_size,
            'return_pct': self.return_pct,
            'pnl': self.pnl,
            'hold_days': self.hold_days,
            'exit_reason': self.exit_reason,
            'market_cap': self.market_cap
        }


class PortfolioTracker:
    """Tracks portfolio state and performance over time"""
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.open_positions: List[Position] = []
        self.closed_positions: List[Position] = []
        
        # Performance tracking
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []
        
    def get_open_exposure(self) -> Tuple[float, float]:
        """Get current long and short exposure"""
        long_exposure = sum(p.position_size for p in self.open_positions if p.signal == 'LONG')
        short_exposure = sum(p.position_size for p in self.open_positions if p.signal == 'SHORT')
        return long_exposure, short_exposure
    
    def get_category_exposure(self, category: str) -> int:
        """Get number of open positions in a category"""
        return sum(1 for p in self.open_positions if p.category == category)
    
    def can_add_position(self, category: str, max_per_category: int, max_total: int) -> bool:
        """Check if we can add another position"""
        if len(self.open_positions) >= max_total:
            return False
        if self.get_category_exposure(category) >= max_per_category:
            return False
        return True
    
    def update_equity(self, date: pd.Timestamp, price_data: pd.DataFrame):
        """Calculate current portfolio value"""
        # Calculate mark-to-market value of open positions
        mtm_value = 0.0
        for pos in self.open_positions:
            price_row = price_data[(price_data['base'] == pos.symbol) & 
                                   (price_data['date'] == date)]
            if not price_row.empty:
                current_price = price_row.iloc[0]['close']
                mtm_value += pos.update_pnl(current_price)
        
        total_equity = self.cash + mtm_value
        
        # Calculate daily return
        if len(self.equity_curve) > 0:
            prev_equity = self.equity_curve[-1]['equity']
            daily_return = (total_equity / prev_equity - 1) if prev_equity > 0 else 0.0
            self.daily_returns.append(daily_return)
        else:
            self.daily_returns.append(0.0)
        
        # Record equity
        long_exp, short_exp = self.get_open_exposure()
        self.equity_curve.append({
            'date': date,
            'equity': total_equity,
            'cash': self.cash,
            'mtm_value': mtm_value,
            'num_positions': len(self.open_positions),
            'long_exposure': long_exp,
            'short_exposure': short_exp,
            'daily_return': self.daily_returns[-1]
        })


def load_data(config: BacktestConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load signal and price data"""
    # Load signals
    signals_df = pd.read_csv(config.signal_file)
    signals_df['date'] = pd.to_datetime(signals_df['date'])
    
    # Load prices
    price_df = pd.read_csv(config.price_file)
    price_df['date'] = pd.to_datetime(price_df['date'])
    
    # Ensure base column exists
    if 'base' not in price_df.columns and 'symbol' in price_df.columns:
        price_df['base'] = price_df['symbol'].str.extract(r'^([^/]+)')[0]
    
    # Filter by date range
    if config.start_date:
        start = pd.to_datetime(config.start_date)
        signals_df = signals_df[signals_df['date'] >= start]
        price_df = price_df[price_df['date'] >= start]
    
    if config.end_date:
        end = pd.to_datetime(config.end_date)
        signals_df = signals_df[signals_df['date'] <= end]
        price_df = price_df[price_df['date'] <= end]
    
    # Filter by categories
    if config.categories:
        signals_df = signals_df[signals_df['category'].isin(config.categories)]
    
    return signals_df, price_df


def calculate_position_sizes(signals: pd.DataFrame, portfolio: PortfolioTracker, 
                             config: BacktestConfig) -> Dict[str, float]:
    """
    Calculate position sizes for new signals
    
    Returns dict of {symbol: position_size}
    """
    if signals.empty:
        return {}
    
    # Available capital for new positions
    long_exp, short_exp = portfolio.get_open_exposure()
    target_capital = config.initial_capital * config.target_leverage
    
    # Separate long and short signals
    long_signals = signals[signals['signal'] == 'LONG']
    short_signals = signals[signals['signal'] == 'SHORT']
    
    position_sizes = {}
    
    # Calculate sizes based on method
    if config.position_size_method == 'equal_weight':
        # Equal weight across all signals
        n_longs = len(long_signals)
        n_shorts = len(short_signals)
        
        if n_longs > 0:
            size_per_long = (target_capital - long_exp) / n_longs if n_longs > 0 else 0
            for symbol in long_signals['symbol']:
                position_sizes[symbol] = max(0, min(size_per_long, target_capital * 0.1))
        
        if n_shorts > 0:
            size_per_short = (target_capital - short_exp) / n_shorts if n_shorts > 0 else 0
            for symbol in short_signals['symbol']:
                position_sizes[symbol] = max(0, min(size_per_short, target_capital * 0.1))
    
    elif config.position_size_method == 'z_score_weight':
        # Weight by |z_score|
        if not long_signals.empty:
            long_signals = long_signals.copy()
            long_signals['abs_z'] = long_signals['z_score'].abs()
            total_z = long_signals['abs_z'].sum()
            if total_z > 0:
                for _, row in long_signals.iterrows():
                    weight = row['abs_z'] / total_z
                    position_sizes[row['symbol']] = min(weight * target_capital, target_capital * 0.15)
        
        if not short_signals.empty:
            short_signals = short_signals.copy()
            short_signals['abs_z'] = short_signals['z_score'].abs()
            total_z = short_signals['abs_z'].sum()
            if total_z > 0:
                for _, row in short_signals.iterrows():
                    weight = row['abs_z'] / total_z
                    position_sizes[row['symbol']] = min(weight * target_capital, target_capital * 0.15)
    
    return position_sizes


def check_exit_conditions(position: Position, current_data: pd.Series, 
                          config: BacktestConfig) -> Tuple[bool, str]:
    """
    Check if position should be exited
    
    Returns (should_exit, exit_reason)
    """
    # Time-based exit
    if position.hold_days >= config.holding_period:
        return True, 'time_based'
    
    # Mean reversion exit (z-score back to neutral)
    if not pd.isna(current_data.get('z_score', np.nan)):
        z_score = current_data['z_score']
        if abs(z_score) < config.exit_z_threshold:
            return True, 'mean_revert'
    
    # Stop loss / Take profit
    if 'close' in current_data:
        current_price = current_data['close']
        if position.signal == 'LONG':
            ret = current_price / position.entry_price - 1
        else:  # SHORT
            ret = 1 - current_price / position.entry_price
        
        if ret < -config.stop_loss:
            return True, 'stop_loss'
        if ret > config.take_profit:
            return True, 'take_profit'
    
    return False, ''


def run_backtest(config: BacktestConfig) -> Tuple[PortfolioTracker, pd.DataFrame]:
    """
    Main backtest loop
    
    Returns:
        portfolio: PortfolioTracker with results
        trades_df: DataFrame of all trades
    """
    print(f"Loading data...")
    signals_df, price_df = load_data(config)
    
    print(f"Backtest period: {signals_df['date'].min()} to {signals_df['date'].max()}")
    print(f"Total signal observations: {len(signals_df)}")
    print(f"Active signals: {len(signals_df[signals_df['signal'].isin(['LONG', 'SHORT'])])}")
    print(f"Categories: {signals_df['category'].unique()}")
    
    # Initialize portfolio
    portfolio = PortfolioTracker(config.initial_capital)
    
    # Get unique trading dates
    trading_dates = sorted(signals_df['date'].unique())
    
    print(f"\nRunning backtest over {len(trading_dates)} trading days...")
    
    for i, date in enumerate(trading_dates):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(trading_dates)} days ({100*i/len(trading_dates):.1f}%)")
        
        # Get signals for this day
        day_signals = signals_df[signals_df['date'] == date]
        
        # Get price data for this day and next day (for returns)
        day_prices = price_df[price_df['date'] == date]
        if i < len(trading_dates) - 1:
            next_date = trading_dates[i + 1]
            next_prices = price_df[price_df['date'] == next_date]
        else:
            next_prices = day_prices
        
        # --- Check exit conditions for open positions ---
        positions_to_close = []
        for pos in portfolio.open_positions:
            pos.hold_days = (date - pos.entry_date).days
            
            # Get current signal/price data for this position
            pos_signal = day_signals[(day_signals['symbol'] == pos.symbol) & 
                                     (day_signals['category'] == pos.category)]
            pos_price = day_prices[day_prices['base'] == pos.symbol]
            
            if not pos_price.empty:
                current_price = pos_price.iloc[0]['close']
                
                # Combine signal and price data
                current_data = {}
                if not pos_signal.empty:
                    current_data = pos_signal.iloc[0].to_dict()
                current_data['close'] = current_price
                
                should_exit, exit_reason = check_exit_conditions(
                    pos, pd.Series(current_data), config
                )
                
                if should_exit:
                    # Use next day's price for exit (no lookahead)
                    next_price_row = next_prices[next_prices['base'] == pos.symbol]
                    if not next_price_row.empty:
                        exit_price = next_price_row.iloc[0]['close']
                        exit_z = current_data.get('z_score', np.nan)
                        
                        total_cost = (config.transaction_cost + config.slippage)
                        pos.close(next_date if i < len(trading_dates) - 1 else date, 
                                 exit_price, exit_z, exit_reason, total_cost)
                        
                        positions_to_close.append(pos)
                        
                        # Return cash
                        portfolio.cash += pos.position_size + pos.pnl
        
        # Close positions
        for pos in positions_to_close:
            portfolio.open_positions.remove(pos)
            portfolio.closed_positions.append(pos)
        
        # --- Enter new positions ---
        # Get active signals for today
        active_signals = day_signals[day_signals['signal'].isin(['LONG', 'SHORT'])]
        
        # Filter out symbols we already have positions in
        open_symbols = {(p.symbol, p.category) for p in portfolio.open_positions}
        new_signals = active_signals[
            ~active_signals.apply(lambda x: (x['symbol'], x['category']) in open_symbols, axis=1)
        ]
        
        if not new_signals.empty:
            # Calculate position sizes
            position_sizes = calculate_position_sizes(new_signals, portfolio, config)
            
            # Enter positions
            for _, signal in new_signals.iterrows():
                symbol = signal['symbol']
                category = signal['category']
                
                # Check if we can add this position
                if not portfolio.can_add_position(
                    category, 
                    config.max_positions_per_category,
                    config.max_total_positions
                ):
                    continue
                
                # Check if we have size allocated
                if symbol not in position_sizes or position_sizes[symbol] <= 0:
                    continue
                
                # Get entry price (use next day's open/close to avoid lookahead)
                next_price_row = next_prices[next_prices['base'] == symbol]
                if next_price_row.empty:
                    continue
                
                entry_price = next_price_row.iloc[0]['close']
                size = position_sizes[symbol]
                
                # Check if we have enough cash
                total_cost = size * (1 + config.transaction_cost + config.slippage)
                if portfolio.cash < total_cost:
                    continue
                
                # Create position
                pos = Position(
                    symbol=symbol,
                    category=category,
                    signal=signal['signal'],
                    entry_date=next_date if i < len(trading_dates) - 1 else date,
                    entry_price=entry_price,
                    entry_z_score=signal['z_score'],
                    position_size=size,
                    market_cap=signal.get('market_cap', np.nan)
                )
                
                portfolio.open_positions.append(pos)
                portfolio.cash -= total_cost
        
        # --- Update equity curve ---
        if not next_prices.empty:
            portfolio.update_equity(
                next_date if i < len(trading_dates) - 1 else date,
                next_prices
            )
    
    # Close any remaining open positions at the end
    if portfolio.open_positions:
        final_date = trading_dates[-1]
        final_prices = price_df[price_df['date'] == final_date]
        
        for pos in portfolio.open_positions:
            price_row = final_prices[final_prices['base'] == pos.symbol]
            if not price_row.empty:
                exit_price = price_row.iloc[0]['close']
                total_cost = (config.transaction_cost + config.slippage)
                pos.close(final_date, exit_price, np.nan, 'backtest_end', total_cost)
                portfolio.cash += pos.position_size + pos.pnl
                portfolio.closed_positions.append(pos)
        
        portfolio.open_positions = []
    
    # Convert trades to DataFrame
    trades_df = pd.DataFrame([pos.to_dict() for pos in portfolio.closed_positions])
    
    print(f"\nBacktest complete!")
    print(f"Total trades: {len(trades_df)}")
    
    return portfolio, trades_df


def calculate_performance_metrics(portfolio: PortfolioTracker) -> pd.Series:
    """Calculate comprehensive performance metrics"""
    equity_df = pd.DataFrame(portfolio.equity_curve)
    
    if equity_df.empty or len(equity_df) < 2:
        return pd.Series({
            'total_return': 0.0,
            'annualized_return': 0.0,
            'annualized_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0,
        })
    
    # Basic returns
    initial_equity = equity_df.iloc[0]['equity']
    final_equity = equity_df.iloc[-1]['equity']
    total_return = (final_equity / initial_equity - 1)
    
    # Annualized metrics
    n_days = len(equity_df)
    years = n_days / 252
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility
    daily_returns = np.array(portfolio.daily_returns)
    annualized_vol = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 1 else 0
    
    # Sharpe ratio (assume 0% risk-free rate)
    sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Sortino ratio (downside volatility)
    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0
    sortino = annualized_return / downside_vol if downside_vol > 0 else 0
    
    # Maximum drawdown
    equity_series = equity_df['equity'].values
    running_max = np.maximum.accumulate(equity_series)
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = abs(drawdown.min())
    
    # Calmar ratio
    calmar = annualized_return / max_drawdown if max_drawdown > 0 else 0
    
    # Win rate (from closed trades)
    if portfolio.closed_positions:
        wins = sum(1 for p in portfolio.closed_positions if p.pnl > 0)
        win_rate = wins / len(portfolio.closed_positions)
        
        winning_trades = [p.return_pct for p in portfolio.closed_positions if p.pnl > 0]
        losing_trades = [p.return_pct for p in portfolio.closed_positions if p.pnl <= 0]
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        gross_profit = sum(p.pnl for p in portfolio.closed_positions if p.pnl > 0)
        gross_loss = abs(sum(p.pnl for p in portfolio.closed_positions if p.pnl <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
    
    # Average holding period
    avg_hold = np.mean([p.hold_days for p in portfolio.closed_positions]) if portfolio.closed_positions else 0
    
    return pd.Series({
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'num_trades': len(portfolio.closed_positions),
        'avg_hold_days': avg_hold,
        'final_equity': final_equity,
    })


def plot_equity_curve(portfolio: PortfolioTracker, output_path: str):
    """Plot equity curve and save to file"""
    equity_df = pd.DataFrame(portfolio.equity_curve)
    
    if equity_df.empty:
        print("No equity data to plot")
        return
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Equity curve
    axes[0].plot(equity_df['date'], equity_df['equity'], linewidth=2, label='Portfolio Value')
    axes[0].axhline(y=portfolio.initial_capital, color='gray', linestyle='--', label='Initial Capital')
    axes[0].set_xlabel('Date')
    axes[0].set_ylabel('Portfolio Value ($)')
    axes[0].set_title('Pairs Trading Strategy - Equity Curve')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Drawdown
    equity_series = equity_df['equity'].values
    running_max = np.maximum.accumulate(equity_series)
    drawdown = (equity_series - running_max) / running_max * 100
    
    axes[1].fill_between(equity_df['date'], drawdown, 0, alpha=0.3, color='red')
    axes[1].plot(equity_df['date'], drawdown, linewidth=1, color='darkred')
    axes[1].set_xlabel('Date')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].set_title('Drawdown')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Equity curve saved to {output_path}")
    plt.close()


def plot_category_performance(trades_df: pd.DataFrame, output_path: str):
    """Plot performance by category"""
    if trades_df.empty:
        print("No trades to plot")
        return
    
    # Group by category
    category_perf = trades_df.groupby('category').agg({
        'pnl': 'sum',
        'return_pct': 'mean',
        'symbol': 'count'
    }).rename(columns={'symbol': 'num_trades'})
    
    category_perf['win_rate'] = trades_df.groupby('category').apply(
        lambda x: (x['pnl'] > 0).sum() / len(x)
    )
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Total P&L by category
    category_perf['pnl'].sort_values().plot(kind='barh', ax=axes[0, 0])
    axes[0, 0].set_xlabel('Total P&L ($)')
    axes[0, 0].set_title('P&L by Category')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Average return by category
    (category_perf['return_pct'] * 100).sort_values().plot(kind='barh', ax=axes[0, 1])
    axes[0, 1].set_xlabel('Avg Return (%)')
    axes[0, 1].set_title('Average Return by Category')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Number of trades
    category_perf['num_trades'].sort_values().plot(kind='barh', ax=axes[1, 0])
    axes[1, 0].set_xlabel('Number of Trades')
    axes[1, 0].set_title('Trade Count by Category')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Win rate
    (category_perf['win_rate'] * 100).sort_values().plot(kind='barh', ax=axes[1, 1])
    axes[1, 1].set_xlabel('Win Rate (%)')
    axes[1, 1].set_title('Win Rate by Category')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Category performance saved to {output_path}")
    plt.close()


def save_results(portfolio: PortfolioTracker, trades_df: pd.DataFrame, 
                 metrics: pd.Series, config: BacktestConfig, output_dir: str):
    """Save all backtest results to files"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save equity curve
    equity_df = pd.DataFrame(portfolio.equity_curve)
    equity_df.to_csv(output_path / 'pairs_trading_equity_curve.csv', index=False)
    
    # Save trades log
    if not trades_df.empty:
        trades_df.to_csv(output_path / 'pairs_trading_trades_log.csv', index=False)
        
        # Save category breakdown
        category_breakdown = trades_df.groupby('category').agg({
            'pnl': ['sum', 'mean', 'std'],
            'return_pct': ['mean', 'std'],
            'hold_days': 'mean',
            'symbol': 'count'
        }).round(4)
        category_breakdown.to_csv(output_path / 'pairs_trading_category_breakdown.csv')
    
    # Save performance summary
    summary_df = pd.DataFrame({
        'metric': metrics.index,
        'value': metrics.values
    })
    summary_df.to_csv(output_path / 'pairs_trading_performance_summary.csv', index=False)
    
    # Save config
    config_df = pd.DataFrame([asdict(config)])
    config_df.to_csv(output_path / 'pairs_trading_config.csv', index=False)
    
    print(f"\nResults saved to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description='Backtest basket pairs trading strategy'
    )
    parser.add_argument('--signal-file', type=str, 
                       default='signals/basket_divergence_signals_full.csv',
                       help='Path to signals CSV file')
    parser.add_argument('--price-file', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to price data CSV file')
    parser.add_argument('--holding-period', type=int, default=10,
                       help='Days to hold positions (default: 10)')
    parser.add_argument('--stop-loss', type=float, default=0.10,
                       help='Stop loss threshold (default: 0.10 = 10%%)')
    parser.add_argument('--take-profit', type=float, default=0.15,
                       help='Take profit threshold (default: 0.15 = 15%%)')
    parser.add_argument('--position-size', type=str, default='equal_weight',
                       choices=['equal_weight', 'z_score_weight'],
                       help='Position sizing method')
    parser.add_argument('--max-positions', type=int, default=20,
                       help='Maximum total positions')
    parser.add_argument('--categories', type=str, nargs='+',
                       help='Categories to trade (default: all)')
    parser.add_argument('--start-date', type=str,
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str,
                       default='backtests/results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Create config
    config = BacktestConfig(
        signal_file=args.signal_file,
        price_file=args.price_file,
        holding_period=args.holding_period,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        position_size_method=args.position_size,
        max_total_positions=args.max_positions,
        categories=args.categories,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    
    print("="*80)
    print("BASKET PAIRS TRADING BACKTEST")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Signal file: {config.signal_file}")
    print(f"  Holding period: {config.holding_period} days")
    print(f"  Stop loss: {config.stop_loss*100:.1f}%")
    print(f"  Take profit: {config.take_profit*100:.1f}%")
    print(f"  Position sizing: {config.position_size_method}")
    print(f"  Max positions: {config.max_total_positions}")
    print(f"  Categories: {config.categories if config.categories else 'All'}")
    
    # Run backtest
    portfolio, trades_df = run_backtest(config)
    
    # Calculate metrics
    metrics = calculate_performance_metrics(portfolio)
    
    # Print results
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    print(f"\nOverall Performance:")
    print(f"  Total Return:        {metrics['total_return']*100:>8.2f}%")
    print(f"  Annualized Return:   {metrics['annualized_return']*100:>8.2f}%")
    print(f"  Annualized Vol:      {metrics['annualized_volatility']*100:>8.2f}%")
    print(f"  Sharpe Ratio:        {metrics['sharpe_ratio']:>8.2f}")
    print(f"  Sortino Ratio:       {metrics['sortino_ratio']:>8.2f}")
    print(f"  Max Drawdown:        {metrics['max_drawdown']*100:>8.2f}%")
    print(f"  Calmar Ratio:        {metrics['calmar_ratio']:>8.2f}")
    print(f"\nTrade Statistics:")
    print(f"  Number of Trades:    {metrics['num_trades']:>8.0f}")
    print(f"  Win Rate:            {metrics['win_rate']*100:>8.2f}%")
    print(f"  Avg Win:             {metrics['avg_win']*100:>8.2f}%")
    print(f"  Avg Loss:            {metrics['avg_loss']*100:>8.2f}%")
    print(f"  Profit Factor:       {metrics['profit_factor']:>8.2f}")
    print(f"  Avg Hold Period:     {metrics['avg_hold_days']:>8.1f} days")
    print(f"\nFinal Equity:          ${metrics['final_equity']:>,.2f}")
    
    # Save results
    save_results(portfolio, trades_df, metrics, config, args.output_dir)
    
    # Generate plots
    plot_equity_curve(portfolio, f"{args.output_dir}/pairs_trading_equity_curve.png")
    if not trades_df.empty:
        plot_category_performance(trades_df, f"{args.output_dir}/pairs_trading_category_heatmap.png")
    
    print("\n" + "="*80)
    print("Backtest complete! Check output directory for detailed results.")
    print("="*80)


if __name__ == '__main__':
    main()
