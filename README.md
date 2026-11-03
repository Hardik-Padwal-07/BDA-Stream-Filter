# Real-Time Stream Fraud Filter - BDA Mini Project (Module 4)

Real-Time Fraud Detection on Payment Data Streams using Bloom Filter, Flajolet-Martin and DGIM

No Hadoop. Pure Python + Streamlit. Single-pass mining of a payment stream.

## Problem (genuine)
UPI-like stream: thousands of payments/sec, infinite. With finite memory you must answer live:
1. Is this account a known fraud? (can't store full blacklist on edge)
2. How many **distinct** users today? (can't store all IDs)
3. How many frauds in the **last N** payments? (can't rescan)

Exact solutions need O(n) memory. Stream needs O(1).

## Solution (maps to syllabus)
| Question | Syllabus | Implementation `src/` |
|---|---|---|
| Live stream model, stream queries | 4.1 Stream Data Model, Issues in Stream Processing | `stream.py` replays PaySim CSV row-by-row |
| Fraud membership, low memory | 4.3 Filtering Streams: Bloom Filter with Analysis | `bloom.py` from scratch, FP analysis |
| Distinct users, one pass | 4.4 Count-Distinct, Flajolet-Martin, Combining Estimates, Space | `fm.py`, median of 10 hashes |
| Frauds in window | 4.5 Counting Ones in Window, DGIM, Query Answering, Decaying Windows | `dgim.py` buckets |

## Dataset
- **Real:** PaySim mobile-money (`PS_20174392719_1491204439457_log.csv`, ~6M rows) from Kaggle - search `paysim1`, save as `data/paysim_full.csv`.
- **Auto:** `python scripts/download_paysim.py --n 100000` tries public mirror, else generates PaySim-like `data/paysim_sample.csv` (same columns). Demo works offline either way.

## Run
```bash
pip install -r requirements.txt
python scripts/download_paysim.py --n 100000
python scripts/run_evaluation.py --n 20000   # CLI numbers for report
streamlit run app.py                          # live dashboard for viva
```

## What to show in viva
- Bloom FP-rate ≈ theory `(1-e^-kn/m)^k`, memory KB vs MB exact.
- FM estimate within ~10-15% using 96B vs ~180KB exact (20k rows).
- DGIM line tracks exact window count with ~3-7 buckets vs 1000 window.
- Note: with only ~39 fraud IDs in a 20k demo, Bloom (2.5KB) looks bigger than a
  Python set (~0.5KB). Win appears at scale: 1M fraud IDs ≈ 12MB exact vs 2.5KB
  Bloom. Mention this line in viva + report scale table.
