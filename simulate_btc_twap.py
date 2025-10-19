#!/usr/bin/env python3
"""
Simulate a TWAP order execution for BTC on Hyperliquid.
This simulates buying BTC over time without actually placing orders.
"""
import os
import time
import random
from datetime import datetime, timedelta
from hyperliquid_twap import hyperliquid
from pprint import pprint

def simulate_twap_order(symbol='BTC/USDC:USDC', side='buy', amount=0.001, minutes=30, randomize=True):
    """
    Simulate a TWAP order execution.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDC:USDC')
        side: 'buy' or 'sell'
        amount: Total amount in base currency (BTC) to execute
        minutes: Duration in minutes to spread the order
        randomize: Whether to randomize order execution times
    """
    # Get API credentials from environment variables
    api_key = os.getenv('HL_API')
    secret_key = os.getenv('HL_SECRET')
    
    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")
    
    # Initialize Hyperliquid exchange
    exchange = hyperliquid({
        'privateKey': secret_key,
        'walletAddress': api_key,
        'enableRateLimit': True,
    })
    
    try:
        # Fetch current market price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        estimated_cost = amount * current_price
        
        print(f"\n{'='*70}")
        print("TWAP ORDER SIMULATION")
        print(f"{'='*70}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side.upper()}")
        print(f"Total Amount: {amount} BTC")
        print(f"Duration: {minutes} minutes")
        print(f"Randomized: {randomize}")
        print(f"\nCurrent Market Price: ${current_price:,.2f}")
        print(f"Estimated Total Cost: ${estimated_cost:,.2f}")
        print(f"{'='*70}\n")
        
        # Generate execution schedule
        num_slices = max(int(minutes / 2), 1)  # Execute roughly every 2 minutes
        amount_per_slice = amount / num_slices
        
        print(f"Execution Plan:")
        print(f"  Number of slices: {num_slices}")
        print(f"  Amount per slice: {amount_per_slice:.6f} BTC")
        print(f"  Estimated cost per slice: ${amount_per_slice * current_price:.2f}")
        print(f"\n{'='*70}\n")
        
        # Generate execution times
        if randomize:
            # Randomize execution times within the duration
            execution_times = sorted([random.uniform(0, minutes * 60) for _ in range(num_slices)])
        else:
            # Evenly spaced execution times
            execution_times = [i * (minutes * 60) / num_slices for i in range(num_slices)]
        
        # Simulate execution
        start_time = datetime.now()
        total_executed = 0
        total_cost = 0
        
        print("Simulated Execution Schedule:")
        print(f"{'Time':<20} {'Slice':<8} {'Amount (BTC)':<15} {'Price ($)':<15} {'Cost ($)':<15}")
        print("-" * 80)
        
        for i, exec_offset in enumerate(execution_times, 1):
            exec_time = start_time + timedelta(seconds=exec_offset)
            
            # Simulate price variation (±0.5% random walk)
            price_variation = random.uniform(0.995, 1.005)
            exec_price = current_price * price_variation
            
            slice_cost = amount_per_slice * exec_price
            total_executed += amount_per_slice
            total_cost += slice_cost
            
            print(f"{exec_time.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"{i:<8} "
                  f"{amount_per_slice:.6f} BTC   "
                  f"${exec_price:,.2f}      "
                  f"${slice_cost:.2f}")
        
        print("-" * 80)
        print(f"{'TOTAL':<20} {'':<8} {total_executed:.6f} BTC   "
              f"{'Average: $' + f'{total_cost/total_executed:,.2f}':<15} ${total_cost:.2f}")
        print(f"\n{'='*70}\n")
        
        # Summary
        avg_price = total_cost / total_executed
        price_difference = ((avg_price - current_price) / current_price) * 100
        
        print("Simulation Summary:")
        print(f"  Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End Time: {(start_time + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Total Executed: {total_executed:.6f} BTC")
        print(f"  Initial Price: ${current_price:,.2f}")
        print(f"  Average Execution Price: ${avg_price:,.2f}")
        print(f"  Price Difference: {price_difference:+.4f}%")
        print(f"  Total Cost: ${total_cost:.2f}")
        print(f"\n{'='*70}\n")
        
        if randomize:
            print("✓ Execution times were randomized to minimize market impact.")
        else:
            print("✓ Execution times were evenly distributed.")
        
        print("\nNote: This is a SIMULATION. No actual orders were placed.")
        print("To place a real TWAP order, use the Hyperliquid exchange's TWAP functionality directly.")
        
        return {
            'symbol': symbol,
            'side': side,
            'total_amount': total_executed,
            'num_slices': num_slices,
            'amount_per_slice': amount_per_slice,
            'initial_price': current_price,
            'average_price': avg_price,
            'total_cost': total_cost,
            'start_time': start_time.isoformat(),
            'duration_minutes': minutes,
            'randomized': randomize
        }
        
    except Exception as e:
        print(f"\n✗ Error during simulation: {str(e)}")
        raise

if __name__ == "__main__":
    print("\n" + "="*70)
    print("HYPERLIQUID TWAP ORDER SIMULATION")
    print("="*70)
    
    try:
        # Simulate TWAP order: Buy 0.001 BTC over 30 minutes with randomization
        result = simulate_twap_order(
            symbol='BTC/USDC:USDC',
            side='buy',
            amount=0.001,
            minutes=30,
            randomize=True
        )
        
        print("\n✓ Simulation complete!")
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        if "environment variables" in str(e):
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_wallet_address'")
            print("  export HL_SECRET='your_private_key'")
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
