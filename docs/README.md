# Documentation Index

This directory contains all project documentation organized by category and topic.

## ?? Directory Structure

### [factors/](./factors/)
Factor-specific documentation organized by factor type:

- **[adf/](./factors/adf/)** - Augmented Dickey-Fuller (ADF) Factor
  - Specifications, backtest results, regime switching analysis
  - Implementation summaries and coin-level analysis
  
- **[beta/](./factors/beta/)** - Beta Factor
  - Market beta factor specs and backtest results
  - Rebalance period analysis
  
- **[breakout/](./factors/breakout/)** - Breakout Signal Strategy
  - Breakout signal strategy documentation
  
- **[iqr-spread/](./factors/iqr-spread/)** - IQR Spread Factor
  - Interquartile range spread factor specs and results
  
- **[kurtosis/](./factors/kurtosis/)** - Kurtosis Factor
  - Kurtosis-based factor documentation
  
- **[mean-reversion/](./factors/mean-reversion/)** - Mean Reversion Strategies
  - Directional mean reversion analysis
  - Period analysis and implementation updates
  
- **[pairs-trading/](./factors/pairs-trading/)** - Pairs Trading
  - Phase 1-4 completion documentation
  - Pairs trading specifications
  
- **[reversal/](./factors/reversal/)** - Reversal Factor
  - Holding period analysis
  
- **[size/](./factors/size/)** - Size Factor
  - Size factor specs and rebalance analysis
  - 10-day rebalance implementation
  
- **[skew/](./factors/skew/)** - Skew Factor
  - Strategy documentation and backtest summaries
  - Short-only comparison analysis
  
- **[trendline/](./factors/trendline/)** - Trendline Factor
  - Breakout detection and integration
  - Complete implementation guide and quick start
  
- **[volatility/](./factors/volatility/)** - Volatility Factor
  - Specs, params, and rebalance period analysis
  - Backtest results

### [data-collection/](./data-collection/)
Data collection, APIs, and data pipeline documentation (27 files):

- **Coinalyze Integration**: API setup, rate limiting, caching, and implementation
- **Open Interest (OI) Data**: Auto-refresh, data loading, freshness checks, divergence signals
- **Funding Rates**: Historical data collection and top 100 cryptocurrencies
- **Data Validation**: Validation summaries and quality checks
- **Category Data**: Cryptocurrency category data summaries
- **Monthly Snapshots**: Monthly data snapshot documentation

### [execution/](./execution/)
Execution and trading system documentation (currently empty - execution code exists in `/execution` directory)

### [infrastructure/](./infrastructure/)
Infrastructure, testing, and system-level documentation (21 files):

- **Backtesting**: Backtest framework, summary scripts, consistency reports
- **Caching**: Cache implementation and optimization
- **Rate Limiting**: Implementation guides and visual documentation
- **Testing**: Test summaries and test suite documentation
- **Code Quality**: Merge summaries, commit guidelines, robustness checks
- **Refactoring**: Strategy registry, reporting module, signal scalability
- **Research Planning**: Research TODO and implementation tracking

### [robustness/](./robustness/)
Robustness testing and enhancement documentation (7 files):

- Quick start guides
- Implementation guides
- Enhancement plans
- Command references

## ?? Quick Navigation

### By Topic

**Getting Started:**
- [Robustness Quick Start](./robustness/START_HERE.md)
- [Backtesting README](./infrastructure/BACKTEST_README.md)

**Factor Research:**
- Browse [factors/](./factors/) directory for specific factor documentation
- Each factor has its own subdirectory with specs, results, and implementation details

**Data Collection:**
- [Coinalyze API Setup](./data-collection/COINALYZE_README.md)
- [Funding Rates](./data-collection/FUNDING_RATES_README.md)
- [OI Divergence Signals](./data-collection/OI_DIVERGENCE_SIGNALS_README.md)

**System Infrastructure:**
- [Rate Limiting Visual Guide](./infrastructure/RATE_LIMITING_VISUAL_GUIDE.md)
- [Cache Implementation](./infrastructure/CACHE_IMPLEMENTATION_SUMMARY.md)
- [Testing Guide](./infrastructure/TESTS_README.md)

## ?? Factor Summary

The project currently includes 12 distinct factor categories:

1. **ADF** (Augmented Dickey-Fuller) - Mean reversion detection
2. **Beta** - Market correlation and exposure
3. **Breakout** - Price breakout signals
4. **IQR Spread** - Interquartile range-based spreads
5. **Kurtosis** - Distribution tail behavior
6. **Mean Reversion** - General mean reversion strategies
7. **Pairs Trading** - Statistical arbitrage between pairs
8. **Reversal** - Price reversal patterns
9. **Size** - Market cap and size-based factors
10. **Skew** - Distribution skewness
11. **Trendline** - Technical trendline analysis
12. **Volatility** - Volatility-based strategies

## ?? Contributing

When adding new documentation:

1. **Factor Documentation**: Place in `/docs/factors/{factor-name}/`
2. **Data Collection**: Place in `/docs/data-collection/`
3. **Execution Systems**: Place in `/docs/execution/`
4. **Infrastructure/Testing**: Place in `/docs/infrastructure/`
5. **Robustness Testing**: Place in `/docs/robustness/`

Maintain clear naming conventions and include dates when relevant.
