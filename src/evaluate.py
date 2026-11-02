"""Evaluation: exact vs approximate. Used by CLI and Streamlit."""
from collections import deque

from src.bloom import BloomFilter
from src.dgim import DGIM
from src.fm import FlajoletMartin


def evaluate_stream(rows: list[dict], bloom_m=20000, bloom_k=3,
                    fm_hashes=24, dgim_n=1000) -> dict:
    """Single-pass evaluation over materialized rows (for report)."""
    # Build blacklist from FIRST HALF frauds (simulate known fraud DB),
    # evaluate Bloom on SECOND HALF (unseen stream). FM/DGIM run on full stream.
    half = len(rows) // 2
    known_fraud = {r["nameOrig"] for r in rows[:half] if r["isFraud"] == 1}
    if len(known_fraud) < 20:
        # top-up from full stream so demo has meaningful blacklist size
        for r in rows:
            if r["isFraud"] == 1:
                known_fraud.add(r["nameOrig"])
            if len(known_fraud) >= 100:
                break

    bf = BloomFilter(m=bloom_m, k=bloom_k)
    for f in known_fraud:
        bf.add(f)

    fm = FlajoletMartin(num_hashes=fm_hashes)
    dgim = DGIM(N=dgim_n)

    exact_users: set[str] = set()
    window: deque[int] = deque(maxlen=dgim_n)

    tp = fp = tn = fn = 0
    fm_hist, exact_distinct_hist = [], []
    dgim_hist, exact_window_hist = [], []

    for idx, r in enumerate(rows):
        user, is_fraud = r["nameOrig"], int(r["isFraud"])
        # Bloom: predict fraud if user in known-fraud set (approx)
        # count stats only on second half (unseen stream, no train leakage)
        if idx >= half:
            pred = user in bf
            actual = user in known_fraud
            if pred and actual:
                tp += 1
            elif pred and not actual:
                fp += 1
            elif not pred and not actual:
                tn += 1
            else:
                fn += 1

        fm.add(user)
        exact_users.add(user)
        bit = 1 if is_fraud else 0
        dgim.update(bit)
        window.append(bit)

        fm_hist.append(fm.estimate())
        exact_distinct_hist.append(len(exact_users))
        dgim_hist.append(dgim.count())
        exact_window_hist.append(sum(window))

    exact_distinct = len(exact_users)
    fm_est = fm.estimate()
    denom = tp + fp
    precision = tp / denom if denom else 0.0

    return {
        "n": len(rows),
        "known_fraud_size": len(known_fraud),
        "bloom": {
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "fp_rate": fp / (fp + tn) if (fp + tn) else 0.0,
            "precision": precision,
            "theory_fp": bf.theory_fp_rate(),
            "memory_bytes": bf.memory_bytes(),
            "exact_memory_bytes": len(known_fraud) * 12,  # ~12 bytes per ID
        },
        "fm": {
            "exact_distinct": exact_distinct,
            "estimate": fm_est,
            "error_pct": abs(fm_est - exact_distinct) / exact_distinct * 100 if exact_distinct else 0,
            "memory_bytes": fm.memory_bytes(),
            "exact_memory_bytes": exact_distinct * 12,
            "hist_estimate": fm_hist,
            "hist_exact": exact_distinct_hist,
        },
        "dgim": {
            "window": dgim_n,
            "final_exact": exact_window_hist[-1] if exact_window_hist else 0,
            "final_estimate": dgim_hist[-1] if dgim_hist else 0,
            "buckets": dgim.memory_buckets(),
            "hist_estimate": dgim_hist,
            "hist_exact": exact_window_hist,
        },
    }
