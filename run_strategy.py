"""
Strategy Execution Script
Pull daily data on universe >$100k volume/day, calculate days from 200d high,
and calculate weights for instruments <50d from 200d high.
"""

import pandas as pd
from ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
from ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from calc_days_from_high import calculate_days_since_200d_high
from select_insts import select_instruments_near_200d_high
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


def main():
    print("=" * 80)
    print("STRATEGY EXECUTION: >$100k Volume, <50d from 200d High")
    print("=" * 80)
    
    # Step 1: Get markets by volume
    print("\n[Step 1] Fetching markets by volume...")
    markets_df = ccxt_get_markets_by_volume()
    
    if markets_df is None or markets_df.empty:
        print("Error: Failed to fetch markets")
        return
    
    # Filter for markets with >$100k daily volume
    min_volume = 100_000
    filtered_markets = markets_df[markets_df['notional_volume_24h'] > min_volume].copy()
    
    print(f"\nTotal markets: {len(markets_df)}")
    print(f"Markets with >$100k daily volume: {len(filtered_markets)}")
    
    # Get symbols
    symbols = filtered_markets['symbol'].tolist()
    print(f"\nTop 10 markets by volume:")
    for idx, row in filtered_markets.head(10).iterrows():
        print(f"  {row['symbol']}: ${row['notional_volume_24h']:,.0f}")
    
    # Step 2: Get 200 days of daily data
    print(f"\n[Step 2] Fetching 200 days of daily data for {len(symbols)} symbols...")
    print("This may take a few minutes...")
    
    daily_data = ccxt_fetch_hyperliquid_daily_data(symbols=symbols, days=200)
    
    if daily_data is None or daily_data.empty:
        print("Error: Failed to fetch daily data")
        return
    
    print(f"Fetched {len(daily_data)} total data points")
    print(f"Date range: {daily_data['date'].min()} to {daily_data['date'].max()}")
    
    # Save raw data
    data_output_file = "universe_200d_daily_data.csv"
    daily_data.to_csv(data_output_file, index=False)
    print(f"Raw data saved to: {data_output_file}")
    
    # Step 3: Calculate days from 200d high
    print(f"\n[Step 3] Calculating days since 200d high for all instruments...")
    
    days_from_high_df = calculate_days_since_200d_high(daily_data)
    
    # Save full results
    days_output_file = "days_since_200d_high_all_instruments.csv"
    days_from_high_df.to_csv(days_output_file, index=False)
    print(f"Days from high results saved to: {days_output_file}")
    
    # Get current status for each symbol
    latest_status = days_from_high_df.sort_values('date').groupby('symbol').tail(1).reset_index(drop=True)
    print(f"\nCurrent status for all {len(latest_status)} instruments:")
    print(latest_status.sort_values('days_since_200d_high').to_string(index=False, max_rows=20))
    
    # Step 4: Select instruments <50 days from 200d high
    print(f"\n[Step 4] Selecting instruments <50 days from 200d high...")
    
    selected_instruments = select_instruments_near_200d_high(daily_data, max_days=50)
    
    print(f"\nFound {len(selected_instruments)} instruments within 50 days of 200d high:")
    print(selected_instruments.to_string(index=False))
    
    # Save selected instruments
    selected_output_file = "selected_instruments_lt50d_from_200d_high.csv"
    selected_instruments.to_csv(selected_output_file, index=False)
    print(f"\nSelected instruments saved to: {selected_output_file}")
    
    if selected_instruments.empty:
        print("\nNo instruments found within 50 days of 200d high. Exiting.")
        return
    
    # Step 5: Calculate rolling 30d volatility for selected instruments
    print(f"\n[Step 5] Calculating rolling 30d volatility for {len(selected_instruments)} selected instruments...")
    
    selected_symbols = selected_instruments['symbol'].tolist()
    selected_data = daily_data[daily_data['symbol'].isin(selected_symbols)].copy()
    
    volatility_df = calculate_rolling_30d_volatility(selected_data)
    
    # Get latest volatility for each symbol
    latest_volatility = volatility_df.sort_values('date').groupby('symbol').tail(1).reset_index(drop=True)
    latest_volatility = latest_volatility[latest_volatility['volatility_30d'].notna()].copy()
    
    print(f"\nLatest 30d volatility for selected instruments:")
    print(latest_volatility[['symbol', 'volatility_30d']].to_string(index=False))
    
    # Save volatility results
    vola_output_file = "selected_instruments_30d_volatility.csv"
    volatility_df.to_csv(vola_output_file, index=False)
    print(f"\nVolatility results saved to: {vola_output_file}")
    
    # Step 6: Calculate weights using risk parity
    print(f"\n[Step 6] Calculating portfolio weights using risk parity (inverse volatility)...")
    
    # Convert to dictionary for weight calculation
    volatilities = dict(zip(latest_volatility['symbol'], latest_volatility['volatility_30d']))
    
    weights = calculate_weights(volatilities)
    
    if not weights:
        print("\nError: Failed to calculate weights")
        return
    
    # Create weights DataFrame
    weights_df = pd.DataFrame([
        {'symbol': symbol, 'weight': weight}
        for symbol, weight in weights.items()
    ])
    weights_df = weights_df.sort_values('weight', ascending=False).reset_index(drop=True)
    
    print(f"\nPortfolio Weights (Risk Parity - Inverse Volatility):")
    print(weights_df.to_string(index=False))
    print(f"\nTotal weight: {weights_df['weight'].sum():.4f}")
    
    # Save weights
    weights_output_file = "portfolio_weights_lt50d_from_200d_high.csv"
    weights_df.to_csv(weights_output_file, index=False)
    print(f"\nWeights saved to: {weights_output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("EXECUTION COMPLETE - SUMMARY")
    print("=" * 80)
    print(f"1. Universe: {len(symbols)} instruments with >$100k daily volume")
    print(f"2. Data: 200 days of daily OHLCV data")
    print(f"3. Selected: {len(selected_instruments)} instruments <50d from 200d high")
    print(f"4. Portfolio: {len(weights)} instruments with calculated weights")
    print(f"\nOutput files:")
    print(f"  - {data_output_file}")
    print(f"  - {days_output_file}")
    print(f"  - {selected_output_file}")
    print(f"  - {vola_output_file}")
    print(f"  - {weights_output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
