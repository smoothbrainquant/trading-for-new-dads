"""
Portfolio Weight Calculation Module

This module implements risk parity weight calculation based on inverse volatility.
Risk parity aims to equalize the risk contribution of each asset in the portfolio.
"""


def calculate_weights(volatilities):
    """
    Calculate portfolio weights based on risk parity using inverse volatility.

    Risk parity is a portfolio allocation strategy that aims to equalize
    the risk contribution of each asset in the portfolio. This implementation
    assigns weights inversely proportional to asset volatility.

    Methodology:
    1. Calculate inverse volatility for each asset (1 / volatility)
    2. Sum all inverse volatilities
    3. Normalize by dividing each inverse volatility by the sum

    This ensures that:
    - Lower volatility assets receive higher weights
    - Higher volatility assets receive lower weights
    - All assets contribute equally to portfolio risk
    - Weights sum to 1.0 (100% of portfolio)

    Mathematical formula:
        weight_i = (1 / vol_i) / sum(1 / vol_j for all j)

    Where:
        vol_i = rolling volatility of asset i
        weight_i = resulting portfolio weight for asset i

    Args:
        volatilities (dict): Dictionary mapping symbols to their rolling volatility values.
                           Volatility should be expressed as standard deviation of returns.
                           Example: {'BTC/USD': 0.045, 'ETH/USD': 0.062}

    Returns:
        dict: Dictionary mapping symbols to their risk parity weights (summing to 1.0).
              Returns empty dict if volatilities is empty or contains invalid values.
              Example: {'BTC/USD': 0.58, 'ETH/USD': 0.42}

    Notes:
        - Assets with zero or negative volatility are excluded from calculation
        - If all assets have zero/invalid volatility, returns empty dict
        - Weights are normalized to sum to exactly 1.0
    """
    if not volatilities:
        return {}

    # Filter out invalid volatilities (zero, negative, or None)
    valid_volatilities = {
        symbol: vol for symbol, vol in volatilities.items() if vol is not None and vol > 0
    }

    if not valid_volatilities:
        return {}

    # Calculate inverse volatility for each asset
    inverse_volatilities = {symbol: 1.0 / vol for symbol, vol in valid_volatilities.items()}

    # Calculate sum of all inverse volatilities
    total_inverse_vol = sum(inverse_volatilities.values())

    # Calculate normalized weights (sum to 1.0)
    weights = {
        symbol: inv_vol / total_inverse_vol for symbol, inv_vol in inverse_volatilities.items()
    }

    return weights
