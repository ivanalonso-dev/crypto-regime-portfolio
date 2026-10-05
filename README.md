# crypto-regime-portfolio

Combines the validated pieces of projects **006 → 008** into one portfolio, to use the capital each system leaves idle. **No new trading rules** — only allocation.

| Sleeve | Weight | Rule |
|---|---|---|
| **Core** | 60% | BTC when [006](https://github.com/ivanalonso-dev/btc-regime-detector) says bull (strong or weak); when not bull, [008](https://github.com/ivanalonso-dev/crypto-bear-regime-system)'s S2 (BTC only if MVRV < 1), otherwise cash |
| **Satellite** | 40% | [007](https://github.com/ivanalonso-dev/crypto-bull-regime-system) v2 trend system, 1% risk per trade, 19 coins |
| **Idle cash** | — | earns 4% a year (stablecoin / T-bill assumption); 0% variant shown |

Monthly rebalancing to 60/40 with 0.10% cost on the traded amount. Period 2017-08 → 2026-10; in-sample < 2023 ≤ out-of-sample.

**Pre-registered adoption rule:** Calmar above "006 alone" (BTC in bull regime, cash at 0% otherwise) in total and out-of-sample, **and** max drawdown better than −35%.

## Results

| Portfolio | CAGR | Max DD | Sharpe | Calmar | OOS CAGR | OOS max DD | OOS Calmar |
|---|---|---|---|---|---|---|---|
| **60/40, cash 4%** | **53.6%** | **−42.9%** | **1.43** | **1.25** | 40.1% | **−19.9%** | **2.01** |
| 60/40, cash 0% | 50.0% | −44.9% | 1.36 | 1.11 | 36.8% | −22.8% | 1.62 |
| 80/20, cash 4% *(sensitivity)* | 59.5% | −52.3% | 1.34 | 1.14 | 43.6% | −24.3% | 1.79 |
| 40/60, cash 4% *(sensitivity)* | 46.7% | −31.2% | 1.51 | 1.50 | 36.0% | −20.1% | 1.79 |
| Core only (006 + S2) | 64.4% | −60.1% | 1.26 | 1.07 | 46.7% | −32.1% | 1.46 |
| Satellite only (007 v2, 1%) | 30.4% | −24.8% | 1.23 | 1.22 | 26.6% | −23.2% | 1.15 |
| *006 alone* | 51.6% | −44.4% | 1.20 | 1.16 | 35.1% | −33.2% | 1.05 |
| *Buy & hold BTC* | 38.9% | −83.8% | 0.83 | 0.46 | 55.1% | −53.1% | 1.04 |

![equity](resultados/equity.png)

**Verdict under the pre-registered rule: not adopted.** The 60/40 portfolio beats 006 alone on every metric — higher return, higher Sharpe, higher Calmar (1.25 vs 1.16 total, **2.01 vs 1.05 out-of-sample**) and a slightly smaller drawdown — but its maximum drawdown (−42.9%, Dec 2017 → Dec 2018) breaks the −35% limit. With a 60% BTC core, the 2018 crash before the regime detector reacts is unavoidable; the limit turned out to be stricter than the benchmark itself (−44%).

Other findings:
- The diversification benefit is real: combining a high-return, high-drawdown sleeve (006) with a low-correlated, lower-return one (007) lifts out-of-sample Calmar from ~1.1–1.5 to 2.0.
- The 4% yield on idle cash adds ~3.5 points of CAGR.
- S2 (MVRV < 1 accumulation) **hurt** the core in this window (Calmar 1.07 vs 1.16 for 006 alone): its Nov 2018 entry deepened the 2018 drawdown.
- The 40/60 mix would meet all three conditions, but it was a sensitivity case; picking it now would be selection after seeing results. Choosing a lower BTC weight is a legitimate **risk-tolerance** decision, documented as such.

## Limitations

- Same caveats as 006–008: few cycles, survivorship in the coin universe, regime detector chosen after seeing 2020–26.
- Cash yield assumed flat at 4%; stablecoin yield carries counterparty/platform risk.
- Rebalancing assumed frictionless apart from fees.

## Usage

Requires the 006, 007 and 008 folders next to this one (with their data downloaded):

```bash
pip install -r requirements.txt
python portfolio.py                 # --yield-pct 4 --risk 1
```

Prints today's allocation (core in BTC or cash; satellite positions from 007). `run_daily.bat` runs it after 006, 007 and 008.

---
*Author: Ivan Alonso · [github.com/ivanalonso-dev](https://github.com/ivanalonso-dev)*
