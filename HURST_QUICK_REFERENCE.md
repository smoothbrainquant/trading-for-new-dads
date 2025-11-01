# Hurst Exponent Factor - Quick Reference Card

**Analysis:** Top 100 Market Cap Coins | 2023-2025 | 5-day Forward Returns

---

## 🎯 THE FINDING

**High Hurst Exponent (trending) coins return +100.6% annualized in DOWN markets**  
**Low Hurst Exponent (mean-reverting) coins return -3.3% in DOWN markets**  
**→ 103.9 percentage point spread!**

---

## 📊 Performance Matrix

```
                    UP Markets      DOWN Markets    OVERALL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Low HE              +35.6% ✓       -3.3% ❌        +13.4%
(Mean-Reverting)    

High HE             +23.0%         +100.6% ⭐      +57.7%
(Trending)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Sharpe Ratios:**
- High HE / Down: **0.81** ⭐
- Low HE / Up: 0.32
- High HE / Up: 0.23
- Low HE / Down: **-0.04** ❌

---

## 💡 Simple Strategy

**→ Long High Hurst Exponent coins**

**Expected:** +57.7% annualized (Sharpe: 0.51)

**Why it works:**
- Captures +100.6% in down markets (extreme alpha)
- Still +23.0% in up markets (acceptable)
- No regime detection needed (simple)

---

## 📈 Key Statistics

| Metric | Value |
|--------|-------|
| **Best Segment** | High HE / Down: +100.6% |
| **Worst Segment** | Low HE / Down: -3.3% |
| **High HE Overall** | +57.7% annualized |
| **Low HE Overall** | +13.4% annualized |
| **HE Performance Gap** | 44.4 percentage points |
| **Total Observations** | 39,062 coin-days |
| **Unique Coins** | 65 |
| **Time Period** | Jan 2023 - Oct 2025 |

---

## 🔑 What is Hurst Exponent?

- **H < 0.5**: Mean-reverting (price bounces back)
- **H = 0.5**: Random walk (no pattern)
- **H > 0.5**: Trending (momentum/persistence)

**Median in crypto: 0.671** (most coins are trending)

---

## ⚡ Key Insights

1. **High HE dominates** (+57.7% vs +13.4%)
2. **Down markets are the edge** (+100.6% vs -3.3%)
3. **"Defensive" narrative fails** (Low HE loses money when down)
4. **Trending beats mean-reversion** in crypto

---

## 📁 Files Generated

- `hurst_direction_top100_2023_segment_results.csv` - Full metrics
- `hurst_direction_analysis_charts.png` - Visualizations
- `hurst_direction_heatmap.png` - 2×2 matrix
- `HURST_DIRECTION_ANALYSIS_RESULTS.md` - Complete analysis

---

## 🔄 How to Run

```bash
python3 backtests/scripts/analyze_hurst_by_direction.py \
  --top-n 100 \
  --start-date 2023-01-01
```

---

## ⚠️ Caveats

- 2023-2025 was high volatility period (V-shaped recoveries)
- Transaction costs not included
- Top 100 only (large caps)
- Test on other periods for robustness

---

## 🎬 Action Items

✅ **Immediate**: Long High HE coins  
⏳ Test on 2020-2022 period  
⏳ Build regime-switching model  
⏳ Add transaction costs  

---

**Bottom Line**: Trending cryptocurrencies (High HE) deliver 100%+ annualized returns during down markets, driving massive overall outperformance vs. mean-reverting coins.
