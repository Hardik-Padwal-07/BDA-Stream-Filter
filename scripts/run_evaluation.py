"""CLI evaluation for report numbers."""
import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.evaluate import evaluate_stream
from src.stream import load_dataframe_for_eval


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--csv", type=str, default=None)
    ap.add_argument("--bloom-m", type=int, default=20000)
    ap.add_argument("--bloom-k", type=int, default=3)
    ap.add_argument("--window", type=int, default=1000)
    args = ap.parse_args()

    if args.csv:
        csv_path = args.csv if os.path.isabs(args.csv) else os.path.join(ROOT, args.csv)
    else:
        for cand in ["data/paysim_full.csv", "data/paysim_sample.csv"]:
            p = os.path.join(ROOT, cand)
            if os.path.exists(p):
                csv_path = p
                break
        else:
            csv_path = None

    print(f"Loading {args.n} rows from {csv_path or 'synthetic generator'} ...")
    df = load_dataframe_for_eval(csv_path, args.n)
    rows = df.to_dict(orient="records")
    res = evaluate_stream(rows, bloom_m=args.bloom_m, bloom_k=args.bloom_k, dgim_n=args.window)

    print(f"\nN={res['n']}, known_fraud={res['known_fraud_size']}")
    b = res["bloom"]
    print(f"Bloom: TP={b['tp']} FP={b['fp']} TN={b['tn']} FN={b['fn']} "
          f"fp_rate={b['fp_rate']:.4f} theory={b['theory_fp']:.4f} "
          f"mem={b['memory_bytes']}B vs exact~{b['exact_memory_bytes']}B")
    f = res["fm"]
    print(f"FM: exact={f['exact_distinct']} est={f['estimate']:.0f} "
          f"err={f['error_pct']:.2f}% mem={f['memory_bytes']}B vs exact~{f['exact_memory_bytes']}B")
    d = res["dgim"]
    print(f"DGIM(N={d['window']}): exact={d['final_exact']} est={d['final_estimate']} "
          f"buckets={d['buckets']}")

    out = os.path.join(ROOT, "results", "metrics.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value"])
        w.writerow(["n", res["n"]])
        w.writerow(["bloom_fp_rate", round(b["fp_rate"], 5)])
        w.writerow(["bloom_theory_fp", round(b["theory_fp"], 5)])
        w.writerow(["fm_exact", f["exact_distinct"]])
        w.writerow(["fm_estimate", round(f["estimate"], 1)])
        w.writerow(["fm_error_pct", round(f["error_pct"], 2)])
        w.writerow(["dgim_exact", d["final_exact"]])
        w.writerow(["dgim_estimate", d["final_estimate"]])
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
