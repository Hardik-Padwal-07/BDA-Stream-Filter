"""Generate PaySim-like synthetic CSV locally (fallback if Kaggle download fails)."""
import argparse
import os
import random

import pandas as pd

TYPES = ["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"]


def make_paysim_like(n: int, out: str, fraud_ratio=0.005, seed=42):
    rng = random.Random(seed)
    num_users = max(5000, min(100000, n // 3))
    users = [f"C{i}" for i in range(num_users)]
    fraudsters = set(rng.sample(users, max(20, num_users // 100)))

    rows = []
    for step in range(n):
        is_fraud = 1 if rng.random() < fraud_ratio else 0
        if is_fraud and rng.random() < 0.8:
            orig = rng.choice(sorted(fraudsters))
        else:
            orig = rng.choice(users)
        amount = round(rng.uniform(10, 200000), 2)
        old_org = round(rng.uniform(0, 500000), 2)
        new_org = round(max(0, old_org - amount if rng.random() < 0.7 else old_org), 2)
        dest = f"M{rng.randint(0, 20000)}"
        old_dest = round(rng.uniform(0, 500000), 2)
        new_dest = round(old_dest + amount, 2)
        rows.append({
            "step": step % 744,
            "type": rng.choice(TYPES),
            "amount": amount,
            "nameOrig": orig,
            "oldbalanceOrg": old_org,
            "newbalanceOrig": new_org,
            "nameDest": dest,
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "isFraud": is_fraud,
            "isFlaggedFraud": 0,
        })
        if len(rows) >= 50000:
            # flush incrementally to keep memory low
            df = pd.DataFrame(rows)
            header = not os.path.exists(out)
            df.to_csv(out, mode="a", index=False, header=header)
            rows = []
    if rows:
        df = pd.DataFrame(rows)
        header = not os.path.exists(out)
        df.to_csv(out, mode="a", index=False, header=header)
    print(f"Wrote {out} ({n} rows requested)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--out", type=str, default="data/paysim_sample.csv")
    ap.add_argument("--fraud-ratio", type=float, default=0.005)
    args = ap.parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(base)
    out = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    make_paysim_like(args.n, out, fraud_ratio=args.fraud_ratio)
