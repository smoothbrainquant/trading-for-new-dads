# Strategy Research TODOs (Prioritized)

Reappraise and update this list after every research session. Keep priorities current.

## Priority Key
- [P1] High: immediate next work
- [P2] Medium: important, next wave
- [P3] Low: exploratory/nice-to-have

## TODOs

1. [P1] ✅ Beta Factor Strategy (COMPLETE)
   - ✅ Specification document created
   - ✅ Backtest script implemented (backtest_beta_factor.py)
   - ✅ All 4 strategy variants tested:
     - Betting Against Beta (BAB) - Equal Weight: +177.7% return
     - Betting Against Beta (BAB) - Risk Parity: +218.5% return (BEST)
     - Traditional Risk Premium: -82.4% return (failed)
     - Long Low Beta: -56.9% return
     - Long High Beta: -91.2% return
   - ✅ Results documented (BETA_FACTOR_BACKTEST_RESULTS.md)
   - Key Finding: BAB anomaly exists in crypto; low beta coins outperform high beta
   - See: docs/BETA_FACTOR_SPEC.md, docs/BETA_FACTOR_BACKTEST_RESULTS.md

2. [P1] Pairs Trading Strategy (Category-Based)
   - ✅ Phase 1: Category definition & data collection (COMPLETE)
   - ✅ Phase 2: Correlation & covariance analysis (COMPLETE)
   - [ ] Phase 3: Divergence signal generation
   - [ ] Phase 4: Backtesting & performance analysis
   - See: docs/PAIRS_TRADING_SPEC.md, docs/PAIRS_TRADING_PHASE2_COMPLETE.md

2. [P1] Breakout backtests
   - Check parameters; include short side
   - Cluster performance by market cap, funding, open interest, size
   - Validate no-lookahead; use next-day returns

3. [P1] Days-from-high factor
   - Tune parameters; include short side
   - Cluster on auxiliary features (market cap, funding, OI, size)
   - Verify signal timing and return alignment

4. [P1] Carry and mean reversion
   - Re-test carry factor; try alternative windows
   - Mean reversion: parameter sweep; include short side
   - Cluster results on other features

5. [P1] Portfolio-of-strategies backtest (no lookahead)
   - Combine breakout, carry, mean reversion, days-from-high
   - Ensure signals at t use returns at t+1
   - Record per-strategy and aggregate metrics

6. [P2] Cross-sectional momentum
   - Test rank-based CS momentum and z-score variants
   - Compare to time-series momentum baselines

7. [P2] Open interest divergence setups
   - Define concrete entry/exit setups
   - Backtest with sensitivity analysis and risk controls

## Notes
- Maintain consistent data vintages across tests
- Persist configs, metrics, and artifacts alongside results
- Tag and summarize each backtest run in `backtests/results/`