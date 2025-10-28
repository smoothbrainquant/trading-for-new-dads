"""
Rebalance Scheduler Module

This module handles rebalancing schedule persistence for strategies that
rebalance less frequently than daily (e.g., weekly, monthly).

Key Concepts:
- Stores last rebalance date and next rebalance date
- Stores target portfolio weights from last rebalance
- On rebalance days: Calculate new signals and update weights
- On non-rebalance days: Use stored weights (positions drift naturally)

Usage:
    from execution.rebalance_scheduler import RebalanceScheduler
    
    scheduler = RebalanceScheduler(
        strategy_name='skew_factor',
        rebalance_days=7
    )
    
    # In your daily execution loop:
    if scheduler.should_rebalance():
        # Calculate new signals
        target_weights = calculate_skew_signals()
        scheduler.record_rebalance(target_weights)
    else:
        # Use weights from last rebalance
        target_weights = scheduler.get_current_weights()
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional


class RebalanceScheduler:
    """
    Manages rebalancing schedule and weight persistence for multi-day strategies.
    
    This class handles:
    1. Determining when to rebalance based on configurable frequency
    2. Persisting portfolio weights between rebalances
    3. Tracking rebalance history for audit/analysis
    """
    
    def __init__(
        self,
        strategy_name: str,
        rebalance_days: int = 7,
        state_dir: Optional[str] = None,
        force_rebalance: bool = False
    ):
        """
        Initialize rebalance scheduler.
        
        Args:
            strategy_name: Name of the strategy (e.g., 'skew_factor')
            rebalance_days: Number of days between rebalances (default: 7)
            state_dir: Directory to store state files (default: execution/.state/)
            force_rebalance: Force rebalance on first run regardless of schedule
        """
        self.strategy_name = strategy_name
        self.rebalance_days = rebalance_days
        self.force_rebalance = force_rebalance
        
        # Set up state directory
        if state_dir is None:
            # Default to execution/.state/ directory
            execution_dir = Path(__file__).parent
            state_dir = execution_dir / '.state'
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # State file path
        self.state_file = self.state_dir / f'{strategy_name}_rebalance_state.json'
        
        # Load existing state
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load rebalance state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                print(f"✓ Loaded rebalance state for {self.strategy_name}")
                print(f"  Last rebalance: {state.get('last_rebalance_date', 'Never')}")
                print(f"  Next rebalance: {state.get('next_rebalance_date', 'Unknown')}")
                print(f"  Positions: {len(state.get('current_weights', {}))}")
                return state
            except Exception as e:
                print(f"⚠️  Error loading state: {e}. Starting fresh.")
                return self._default_state()
        else:
            print(f"No existing rebalance state found for {self.strategy_name}")
            return self._default_state()
    
    def _default_state(self) -> Dict:
        """Create default state structure."""
        return {
            'strategy_name': self.strategy_name,
            'rebalance_days': self.rebalance_days,
            'last_rebalance_date': None,
            'next_rebalance_date': None,
            'current_weights': {},
            'rebalance_history': []
        }
    
    def _save_state(self):
        """Save rebalance state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            print(f"✓ Saved rebalance state to {self.state_file}")
        except Exception as e:
            print(f"⚠️  Error saving state: {e}")
    
    def should_rebalance(self, current_date: Optional[datetime] = None) -> bool:
        """
        Check if today is a rebalance day.
        
        Args:
            current_date: Date to check (default: today)
            
        Returns:
            bool: True if should rebalance today
        """
        if current_date is None:
            current_date = datetime.now()
        
        current_date_str = current_date.strftime('%Y-%m-%d')
        
        # Force rebalance if requested (first run)
        if self.force_rebalance and self.state['last_rebalance_date'] is None:
            print(f"\n{'='*80}")
            print(f"REBALANCE: YES (First run - initializing portfolio)")
            print(f"{'='*80}")
            return True
        
        # If no previous rebalance, it's time to rebalance
        if self.state['last_rebalance_date'] is None:
            print(f"\n{'='*80}")
            print(f"REBALANCE: YES (No previous rebalance recorded)")
            print(f"{'='*80}")
            return True
        
        # If next rebalance date is set, check against it
        next_rebalance = self.state.get('next_rebalance_date')
        if next_rebalance:
            if current_date_str >= next_rebalance:
                print(f"\n{'='*80}")
                print(f"REBALANCE: YES (Scheduled rebalance day)")
                print(f"  Last rebalance: {self.state['last_rebalance_date']}")
                print(f"  Today: {current_date_str}")
                print(f"  Days since last: {(current_date - datetime.strptime(self.state['last_rebalance_date'], '%Y-%m-%d')).days}")
                print(f"{'='*80}")
                return True
        
        # Not a rebalance day
        days_since = (current_date - datetime.strptime(self.state['last_rebalance_date'], '%Y-%m-%d')).days
        days_until = (datetime.strptime(next_rebalance, '%Y-%m-%d') - current_date).days if next_rebalance else 0
        print(f"\n{'='*80}")
        print(f"REBALANCE: NO (Holding current positions)")
        print(f"  Last rebalance: {self.state['last_rebalance_date']} ({days_since} days ago)")
        print(f"  Next rebalance: {next_rebalance} (in {days_until} days)")
        print(f"  Current positions: {len(self.state['current_weights'])}")
        print(f"{'='*80}")
        return False
    
    def record_rebalance(
        self,
        target_weights: Dict[str, float],
        current_date: Optional[datetime] = None
    ):
        """
        Record a rebalance event with new target weights.
        
        Args:
            target_weights: Dictionary of symbol -> weight (can be notional amounts)
            current_date: Date of rebalance (default: today)
        """
        if current_date is None:
            current_date = datetime.now()
        
        current_date_str = current_date.strftime('%Y-%m-%d')
        next_rebalance_date = (current_date + timedelta(days=self.rebalance_days)).strftime('%Y-%m-%d')
        
        # Update state
        self.state['last_rebalance_date'] = current_date_str
        self.state['next_rebalance_date'] = next_rebalance_date
        self.state['current_weights'] = target_weights
        
        # Add to history
        self.state['rebalance_history'].append({
            'date': current_date_str,
            'num_positions': len(target_weights),
            'positions': list(target_weights.keys())
        })
        
        # Keep only last 52 rebalances in history (1 year for weekly)
        if len(self.state['rebalance_history']) > 52:
            self.state['rebalance_history'] = self.state['rebalance_history'][-52:]
        
        # Save to disk
        self._save_state()
        
        print(f"\n✓ Rebalance recorded for {current_date_str}")
        print(f"  Next rebalance scheduled: {next_rebalance_date}")
        print(f"  New positions: {len(target_weights)}")
    
    def get_current_weights(self) -> Dict[str, float]:
        """
        Get current portfolio weights from last rebalance.
        
        Returns:
            Dict[str, float]: Current target weights
        """
        return self.state.get('current_weights', {})
    
    def get_days_since_rebalance(self, current_date: Optional[datetime] = None) -> Optional[int]:
        """Get number of days since last rebalance."""
        if self.state['last_rebalance_date'] is None:
            return None
        
        if current_date is None:
            current_date = datetime.now()
        
        last_rebalance = datetime.strptime(self.state['last_rebalance_date'], '%Y-%m-%d')
        return (current_date - last_rebalance).days
    
    def get_days_until_rebalance(self, current_date: Optional[datetime] = None) -> Optional[int]:
        """Get number of days until next rebalance."""
        if self.state['next_rebalance_date'] is None:
            return None
        
        if current_date is None:
            current_date = datetime.now()
        
        next_rebalance = datetime.strptime(self.state['next_rebalance_date'], '%Y-%m-%d')
        return (next_rebalance - current_date).days
    
    def force_rebalance_now(self):
        """Force a rebalance on next check (useful for manual intervention)."""
        self.state['next_rebalance_date'] = datetime.now().strftime('%Y-%m-%d')
        self._save_state()
        print(f"✓ Forced next rebalance to today")
    
    def get_rebalance_info(self) -> Dict:
        """Get current rebalance schedule information."""
        return {
            'strategy_name': self.strategy_name,
            'rebalance_days': self.rebalance_days,
            'last_rebalance': self.state.get('last_rebalance_date'),
            'next_rebalance': self.state.get('next_rebalance_date'),
            'days_since': self.get_days_since_rebalance(),
            'days_until': self.get_days_until_rebalance(),
            'num_positions': len(self.state.get('current_weights', {})),
            'total_rebalances': len(self.state.get('rebalance_history', []))
        }
    
    def print_status(self):
        """Print current rebalance status."""
        info = self.get_rebalance_info()
        print("\n" + "="*80)
        print(f"REBALANCE SCHEDULER STATUS: {info['strategy_name']}")
        print("="*80)
        print(f"  Rebalance frequency: Every {info['rebalance_days']} days")
        print(f"  Last rebalance: {info['last_rebalance'] or 'Never'}")
        print(f"  Next rebalance: {info['next_rebalance'] or 'Not scheduled'}")
        print(f"  Days since last: {info['days_since'] or 'N/A'}")
        print(f"  Days until next: {info['days_until'] or 'N/A'}")
        print(f"  Current positions: {info['num_positions']}")
        print(f"  Total rebalances: {info['total_rebalances']}")
        print("="*80)


# Example usage and testing
if __name__ == "__main__":
    print("Testing RebalanceScheduler")
    print("="*80)
    
    # Create scheduler for weekly rebalancing
    scheduler = RebalanceScheduler(
        strategy_name='test_strategy',
        rebalance_days=7,
        force_rebalance=True
    )
    
    # Check status
    scheduler.print_status()
    
    # Simulate first run (should rebalance)
    if scheduler.should_rebalance():
        print("\n→ Calculating new signals...")
        test_weights = {
            'BTC-USD': 1000.0,
            'ETH-USD': 800.0,
            'SOL-USD': 500.0
        }
        scheduler.record_rebalance(test_weights)
    
    # Simulate next day (should NOT rebalance)
    print("\n\n--- NEXT DAY ---")
    next_day = datetime.now() + timedelta(days=1)
    if scheduler.should_rebalance(next_day):
        print("Would rebalance")
    else:
        print("Holding positions")
        weights = scheduler.get_current_weights()
        print(f"Current weights: {weights}")
    
    # Simulate 7 days later (should rebalance)
    print("\n\n--- 7 DAYS LATER ---")
    week_later = datetime.now() + timedelta(days=7)
    if scheduler.should_rebalance(week_later):
        print("\n→ Calculating new signals...")
        new_weights = {
            'BTC-USD': 1200.0,
            'ETH-USD': 900.0,
            'AVAX-USD': 600.0
        }
        scheduler.record_rebalance(new_weights, week_later)
    
    # Print final status
    scheduler.print_status()
