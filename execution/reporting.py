"""
Reporting Module for Trading Strategy Execution

This module handles all reporting and analytics exports, including:
- Portfolio weights export (pre/post reallocation)
- Trade allocation breakdown by signal
- Market data enrichment (price changes, market cap, funding rates)

Separated from main.py to improve maintainability and scalability.
"""

import os
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


def export_portfolio_weights_multisignal(
    target_positions: Dict[str, float],
    initial_contributions_original: Dict[str, Dict[str, float]],
    per_signal_contribs: Dict[str, Dict[str, float]],
    signal_names: List[str],
    notional_value: float,
    workspace_root: str,
) -> None:
    """
    Export portfolio weights for multi-signal blend mode.
    
    Shows weight changes from original allocation to final (after reallocation).
    
    Args:
        target_positions: Final target positions {symbol: notional}
        initial_contributions_original: Original contributions before reallocation
        per_signal_contribs: Final contributions after reallocation
        signal_names: List of signal names
        notional_value: Total portfolio notional value
        workspace_root: Path to workspace root directory
    """
    try:
        if not target_positions:
            print("No target positions to export.")
            return
        
        # Create simplified DataFrame showing strategy weight changes
        weight_rows = []
        
        # Get all symbols from either original or final contributions
        all_symbols = set(target_positions.keys())
        for strategy_contribs in initial_contributions_original.values():
            all_symbols.update(strategy_contribs.keys())
        
        for symbol in all_symbols:
            # Calculate ORIGINAL weights (before reallocation)
            original_weight_total = 0.0
            original_strategy_weights = {}
            for name in signal_names:
                orig_contrib = initial_contributions_original.get(name, {}).get(symbol, 0.0)
                orig_weight = (orig_contrib / notional_value) if notional_value > 0 else 0.0
                original_strategy_weights[name] = orig_weight
                original_weight_total += orig_weight
            
            # Calculate FINAL weights (after reallocation)
            final_weight_total = 0.0
            final_strategy_weights = {}
            for name in signal_names:
                final_contrib = per_signal_contribs.get(name, {}).get(symbol, 0.0)
                final_weight = (final_contrib / notional_value) if notional_value > 0 else 0.0
                final_strategy_weights[name] = final_weight
                final_weight_total += final_weight
            
            # Build row with simplified format
            row = {
                'symbol': symbol,
                'original_weight_pct': original_weight_total * 100,
                'final_weight_pct': final_weight_total * 100,
                'weight_change_pct': (final_weight_total - original_weight_total) * 100,
                'target_notional': target_positions.get(symbol, 0.0),
                'target_side': 'LONG' if target_positions.get(symbol, 0.0) > 0 else ('SHORT' if target_positions.get(symbol, 0.0) < 0 else 'FLAT'),
            }
            
            # Add per-strategy contributions (final weights as %)
            for name in signal_names:
                row[f'{name}_weight_pct'] = final_strategy_weights.get(name, 0.0) * 100
            
            weight_rows.append(row)
        
        df_weights = pd.DataFrame(weight_rows)
        
        # Sort by absolute final weight (descending)
        df_weights['abs_final_weight'] = df_weights['final_weight_pct'].abs()
        df_weights = df_weights.sort_values('abs_final_weight', ascending=False).drop('abs_final_weight', axis=1)
        
        # Save to file
        out_dir = os.path.join(workspace_root, 'backtests', 'results')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'portfolio_weights.csv')
        df_weights.to_csv(out_path, index=False)
        
        print(f"\n{'='*80}")
        print(f"PORTFOLIO WEIGHTS EXPORTED")
        print(f"{'='*80}")
        print(f"Saved portfolio weights to: {out_path}")
        print(f"Format: Shows weight change from original allocation to final (after reallocation)")
        print(f"Columns: symbol, original_weight_pct, final_weight_pct, weight_change_pct, target_notional, target_side")
        print(f"         + per-strategy final contributions: [{', '.join(signal_names)}]_weight_pct")
        print(f"Total symbols: {len(weight_rows)}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\nWarning: Could not export portfolio weights: {e}")


def export_portfolio_weights_legacy(
    target_positions: Dict[str, float],
    per_signal_contribs: Dict[str, Dict[str, float]],
    signal_names: List[str],
    notional_value: float,
    workspace_root: str,
) -> None:
    """
    Export portfolio weights for legacy 50/50 mode.
    
    Args:
        target_positions: Final target positions {symbol: notional}
        per_signal_contribs: Per-signal contributions
        signal_names: List of signal names
        notional_value: Total portfolio notional value
        workspace_root: Path to workspace root directory
    """
    try:
        if not target_positions:
            print("No target positions to export.")
            return
        
        # Convert target positions (notional) to portfolio weights
        portfolio_weights = {}
        for symbol, notional in target_positions.items():
            weight = notional / notional_value if notional_value > 0 else 0.0
            portfolio_weights[symbol] = weight
        
        # Create DataFrame with weights and per-strategy contributions
        weight_rows = []
        for symbol in portfolio_weights.keys():
            row = {
                'symbol': symbol,
                'final_weight': portfolio_weights[symbol],
                'target_notional': target_positions[symbol],
                'target_side': 'LONG' if target_positions[symbol] > 0 else ('SHORT' if target_positions[symbol] < 0 else 'FLAT')
            }
            # Add per-strategy weight contributions
            for name in signal_names:
                contrib_val = per_signal_contribs.get(name, {}).get(symbol, 0.0)
                row[f'{name}_weight'] = (contrib_val / notional_value) if notional_value > 0 else 0.0
            weight_rows.append(row)
        
        df_weights = pd.DataFrame(weight_rows)
        
        # Sort by absolute weight (descending)
        df_weights['abs_weight'] = df_weights['final_weight'].abs()
        df_weights = df_weights.sort_values('abs_weight', ascending=False).drop('abs_weight', axis=1)
        
        # Save to file
        out_dir = os.path.join(workspace_root, 'backtests', 'results')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'portfolio_weights.csv')
        df_weights.to_csv(out_path, index=False)
        
        print(f"\n{'='*80}")
        print(f"PORTFOLIO WEIGHTS EXPORTED")
        print(f"{'='*80}")
        print(f"Saved portfolio weights to: {out_path}")
        print(f"Total symbols: {len(portfolio_weights)}")
        print(f"Total weight (abs): {sum(abs(w) for w in portfolio_weights.values()):.4f}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\nWarning: Could not export portfolio weights: {e}")


def _fetch_price_changes(
    traded_symbols: List[str],
    historical_data: Dict[str, pd.DataFrame],
) -> Dict[str, float]:
    """
    Calculate 1-day price changes for traded symbols.
    
    Args:
        traded_symbols: List of symbols being traded
        historical_data: Historical OHLCV data
        
    Returns:
        Dict mapping symbol to 1-day % change
    """
    pct_change_map: Dict[str, float] = {}
    for symbol in traded_symbols:
        try:
            df_sym = historical_data.get(symbol)
            if df_sym is not None and not df_sym.empty and 'close' in df_sym.columns:
                closes = df_sym['close'].dropna()
                if len(closes) >= 2:
                    prev, last = float(closes.iloc[-2]), float(closes.iloc[-1])
                    if prev != 0:
                        pct_change_map[symbol] = (last / prev - 1.0) * 100.0
                    else:
                        pct_change_map[symbol] = 0.0
                else:
                    pct_change_map[symbol] = 0.0
            else:
                pct_change_map[symbol] = 0.0
        except Exception:
            pct_change_map[symbol] = 0.0
    return pct_change_map


def _fetch_market_caps(traded_symbols: List[str]) -> Dict[str, float]:
    """
    Fetch market caps for traded symbols from CoinMarketCap.
    
    Args:
        traded_symbols: List of symbols being traded
        
    Returns:
        Dict mapping symbol to market cap
    """
    marketcap_by_trading_symbol: Dict[str, float] = {}
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
        df_mc = fetch_coinmarketcap_data(limit=300)
        if df_mc is not None and not df_mc.empty:
            df_mc_map = map_symbols_to_trading_pairs(df_mc, trading_suffix='/USDC:USDC')
            # Use latest mapping; convert to dict trading_symbol->market_cap
            marketcap_by_trading_symbol = dict(
                zip(df_mc_map['trading_symbol'].astype(str), df_mc_map['market_cap'].astype(float))
            )
    except Exception:
        # If fetching fails, leave marketcap map empty
        pass
    return marketcap_by_trading_symbol


def _fetch_funding_rates(
    traded_symbols: List[str],
    exchange_id: str = 'hyperliquid',
) -> Dict[str, float]:
    """
    Fetch aggregated funding rates for traded symbols from Coinalyze.
    
    Args:
        traded_symbols: List of symbols being traded
        exchange_id: Exchange ID for fallback (default: hyperliquid)
        
    Returns:
        Dict mapping base symbol to funding rate %
    """
    funding_by_base: Dict[str, float] = {}
    try:
        from execution.get_carry import fetch_coinalyze_aggregated_funding_rates
        
        print(f"\n  Fetching aggregated funding rates from Coinalyze for {len(traded_symbols)} symbols...")
        print(f"  Format: [SYMBOL]USDT_PERP.A for aggregated data across all exchanges")
        print(f"  Note: Rate limited to 40 calls/min (1.5s between calls)")
        
        df_fr = fetch_coinalyze_aggregated_funding_rates(universe_symbols=traded_symbols)
        if df_fr is not None and not df_fr.empty:
            df_tmp = df_fr.copy()
            # Already has 'base' column from aggregated function
            funding_by_base = df_tmp.groupby('base')['funding_rate_pct'].mean().to_dict()
            print(f"  Got funding rates for {len(funding_by_base)} symbols")
    except Exception as e:
        # Fallback: Try exchange-specific Coinalyze for the target exchange
        try:
            from execution.get_carry import fetch_coinalyze_funding_rates_for_universe
            
            # Map exchange_id to Coinalyze code
            exchange_code_map = {'hyperliquid': 'H', 'bybit': 'D', 'okx': 'K'}
            exchange_code = exchange_code_map.get(exchange_id.lower(), 'H')
            print(f"  Aggregated fetch failed, trying {exchange_id} (code: {exchange_code})...")
            
            df_fr = fetch_coinalyze_funding_rates_for_universe(
                traded_symbols, 
                exchange_code=exchange_code
            )
            if df_fr is not None and not df_fr.empty:
                df_tmp = df_fr.copy()
                if 'base' not in df_tmp.columns:
                    df_tmp['base'] = df_tmp['coinalyze_symbol'].astype(str).str.extract(r'^([A-Z0-9]+)')[0]
                funding_by_base = df_tmp.groupby('base')['funding_rate_pct'].mean().to_dict()
        except Exception as e2:
            print(f"  ⚠️  Could not fetch funding rates: {e2}")
    
    return funding_by_base


def generate_trade_allocation_breakdown(
    trades: Dict[str, float],
    target_positions: Dict[str, float],
    per_signal_contribs: Dict[str, Dict[str, float]],
    signal_names: List[str],
    notional_value: float,
    historical_data: Dict[str, pd.DataFrame],
    workspace_root: str,
    exchange_id: str = 'hyperliquid',
) -> None:
    """
    Generate and export trade allocation breakdown by signal.
    
    Shows how each signal contributes to each trade, enriched with market data.
    
    Args:
        trades: Trades to execute {symbol: trade_amount}
        target_positions: Final target positions {symbol: notional}
        per_signal_contribs: Per-signal contributions
        signal_names: List of signal names
        notional_value: Total portfolio notional value
        historical_data: Historical OHLCV data
        workspace_root: Path to workspace root directory
        exchange_id: Exchange ID for funding rate lookup
    """
    try:
        traded_symbols = list(trades.keys()) if trades else []
        if not traded_symbols:
            print("\nNo trades → no allocation breakdown table.")
            return
        
        print("\n" + "-"*80)
        print("TRADE ALLOCATION BREAKDOWN BY SIGNAL (% of symbol-level contribution)")
        print("-"*80)

        # Fetch enrichment data
        pct_change_map = _fetch_price_changes(traded_symbols, historical_data)
        marketcap_by_trading_symbol = _fetch_market_caps(traded_symbols)
        funding_by_base = _fetch_funding_rates(traded_symbols, exchange_id)

        # Build rows
        rows = []
        for symbol in traded_symbols:
            target = target_positions.get(symbol, 0.0)
            action = 'BUY' if trades[symbol] > 0 else 'SELL'
            target_side = 'LONG' if target > 0 else ('SHORT' if target < 0 else 'FLAT')
            
            # Calculate sum of absolute contributions
            abs_sum = 0.0
            for name in signal_names:
                abs_sum += abs(per_signal_contribs.get(name, {}).get(symbol, 0.0))
            
            # Get enrichments
            market_cap_val = marketcap_by_trading_symbol.get(symbol)
            
            # Map funding by base symbol
            try:
                from execution.strategies.utils import get_base_symbol
                base_symbol = get_base_symbol(symbol)
            except Exception:
                base_symbol = symbol.split('/')[0] if isinstance(symbol, str) else symbol
            funding_pct_val = funding_by_base.get(base_symbol)

            row = {
                'symbol': symbol,
                'action': action,
                'trade_notional': abs(trades[symbol]),
                'target_side': target_side,
                'target_notional': abs(target),
                'pct_change_1d': pct_change_map.get(symbol, 0.0),
                'market_cap': market_cap_val if market_cap_val is not None else float('nan'),
                'funding_rate_pct': funding_pct_val if funding_pct_val is not None else float('nan'),
            }
            
            # Add per-strategy weight columns (contribution as fraction of total portfolio notional)
            # and final blended portfolio weight for this symbol
            final_weight = (target / notional_value) if notional_value > 0 else 0.0
            row['final_blended_weight'] = final_weight
            
            for name in signal_names:
                contrib_val = per_signal_contribs.get(name, {}).get(symbol, 0.0)
                pct = (abs(contrib_val) / abs_sum * 100.0) if abs_sum > 0 else 0.0
                row[f'{name}_pct'] = pct
                # Strategy-specific portfolio weight contribution (signed), relative to total notional
                row[f'{name}_weight'] = (contrib_val / notional_value) if notional_value > 0 else 0.0
            
            rows.append(row)

        df = pd.DataFrame(rows)
        
        # Order columns
        pct_cols = [f'{n}_pct' for n in signal_names]
        weight_cols = [f'{n}_weight' for n in signal_names]
        base_cols = [
            'symbol', 'action', 'trade_notional', 'target_side', 'target_notional', 'final_blended_weight',
            'pct_change_1d', 'market_cap', 'funding_rate_pct'
        ]
        df = df[base_cols + weight_cols + pct_cols]

        # Pretty print
        with pd.option_context('display.max_columns', None, 'display.width', 140, 'display.float_format', '{:,.3f}'.format):
            print(df.to_string(index=False))

        # Save to CSV
        try:
            out_dir = os.path.join(workspace_root, 'backtests', 'results')
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, 'trade_allocation_breakdown.csv')
            df.to_csv(out_path, index=False)
            print(f"\nSaved allocation breakdown to: {out_path}")
        except Exception as e:
            print(f"Could not save allocation breakdown CSV: {e}")
            
    except Exception as e:
        print(f"\nAllocation breakdown generation error: {e}")
