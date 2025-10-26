from typing import Dict, List
import pandas as pd

from execution.select_insts import select_instruments_near_200d_high
from signals.calc_breakout_signals import get_current_signals
from signals.calc_vola import calculate_rolling_30d_volatility as calc_vola_func
from signals.calc_weights import calculate_weights


def calculate_days_from_200d_high(data: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    from signals.calc_days_from_high import get_current_days_since_high

    combined_data = []
    for symbol, symbol_df in data.items():
        df_copy = symbol_df.copy()
        if 'symbol' not in df_copy.columns:
            df_copy['symbol'] = symbol
        combined_data.append(df_copy)

    if not combined_data:
        return {}

    df = pd.concat(combined_data, ignore_index=True)
    result_df = get_current_days_since_high(df)

    result: Dict[str, int] = {}
    for _, row in result_df.iterrows():
        result[row['symbol']] = int(row['days_since_200d_high'])

    return result


def select_instruments_by_days_from_high(data_source, threshold: int) -> pd.DataFrame:
    return select_instruments_near_200d_high(data_source, max_days=threshold)


def calculate_rolling_30d_volatility(data: Dict[str, pd.DataFrame], selected_symbols: List[str]) -> Dict[str, float]:
    combined_data = []
    for symbol in selected_symbols:
        if symbol in data:
            symbol_df = data[symbol].copy()
            if 'symbol' not in symbol_df.columns:
                symbol_df['symbol'] = symbol
            combined_data.append(symbol_df)

    if not combined_data:
        return {}

    df = pd.concat(combined_data, ignore_index=True)
    volatility_df = calc_vola_func(df)

    result: Dict[str, float] = {}
    for symbol in selected_symbols:
        symbol_data = volatility_df[volatility_df['symbol'] == symbol]
        if symbol_data.empty:
            continue
        latest = symbol_data['volatility_30d'].dropna()
        if not latest.empty:
            result[symbol] = float(latest.iloc[-1])
        else:
            # Fallback: estimate simple volatility over available history if <30 days
            closes = symbol_data['close'].dropna()
            if len(closes) >= 2:
                ret = closes.pct_change().dropna()
                if len(ret) >= 5:  # require at least 5 returns for a rough estimate
                    result[symbol] = float(ret.std() * (365 ** 0.5))

    return result


def calc_weights(volatilities: Dict[str, float]) -> Dict[str, float]:
    return calculate_weights(volatilities)


def get_base_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        return symbol
    return symbol.split('/')[0]


def calculate_breakout_signals_from_data(data: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    combined_data = []
    for symbol, symbol_df in data.items():
        df_copy = symbol_df.copy()
        if 'symbol' not in df_copy.columns:
            df_copy['symbol'] = symbol
        combined_data.append(df_copy)

    if not combined_data:
        return {}

    df = pd.concat(combined_data, ignore_index=True)
    signals_df = get_current_signals(df)

    target_positions: Dict[str, int] = {}
    for _, row in signals_df.iterrows():
        symbol = row['symbol']
        position = row['position']
        if position == 'LONG':
            target_positions[symbol] = 1
        elif position == 'SHORT':
            target_positions[symbol] = -1
        else:
            target_positions[symbol] = 0

    return target_positions
