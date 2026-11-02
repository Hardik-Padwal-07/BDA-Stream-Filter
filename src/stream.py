"""Stream simulator - Module 4.1 Stream Data Model.
Replays PaySim CSV row-by-row as a stream, or generates synthetic stream.
PaySim schema: step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,
nameDest,oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud
"""
import os
import random
import time
from collections.abc import Iterator

import pandas as pd

COLUMNS = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
]


def stream_from_csv(path: str, n: int | None = None, delay: float = 0.0) -> Iterator[dict]:
    usecols = ["amount", "nameOrig", "nameDest", "isFraud", "type"]
    # read in chunks to avoid loading 500MB at once for replay
    chunks = pd.read_csv(path, usecols=usecols, chunksize=50000)
    yielded = 0
    for chunk in chunks:
        for row in chunk.itertuples(index=False):
            if n is not None and yielded >= n:
                return
            d = {
                "amount": float(row.amount),
                "nameOrig": str(row.nameOrig),
                "nameDest": str(row.nameDest),
                "isFraud": int(row.isFraud),
                "type": str(row.type),
            }
            if delay:
                time.sleep(delay)
            yield d
            yielded += 1


def synthetic_stream(
    n: int = 50000, fraud_ratio: float = 0.005, seed: int = 42,
    num_users: int = 20000, num_fraudsters: int = 200,
) -> Iterator[dict]:
    """PaySim-like generator. Reuses accounts so distinct-counting is meaningful."""
    rng = random.Random(seed)
    users = [f"C{i}" for i in range(num_users)]
    fraudsters = rng.sample(users, min(num_fraudsters, num_users))
    types = ["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"]
    for _ in range(n):
        is_fraud = 1 if rng.random() < fraud_ratio else 0
        if is_fraud and rng.random() < 0.8:
            orig = rng.choice(fraudsters)  # repeat fraudsters -> Bloom should catch
        else:
            orig = rng.choice(users)
        yield {
            "amount": round(rng.uniform(10, 50000), 2),
            "nameOrig": orig,
            "nameDest": f"M{rng.randint(0, 5000)}",
            "isFraud": is_fraud,
            "type": rng.choice(types),
        }


def get_stream(csv_path: str | None, n: int, synthetic_fallback: bool = True,
               fraud_ratio: float = 0.005) -> Iterator[dict]:
    if csv_path and os.path.exists(csv_path):
        yield from stream_from_csv(csv_path, n=n)
    elif synthetic_fallback:
        yield from synthetic_stream(n=n, fraud_ratio=fraud_ratio)
    else:
        raise FileNotFoundError(f"CSV not found: {csv_path}")


def load_dataframe_for_eval(csv_path: str | None, n: int) -> pd.DataFrame:
    """Load first n rows into memory for exact baselines (eval only)."""
    if csv_path and os.path.exists(csv_path):
        return pd.read_csv(csv_path, usecols=["amount", "nameOrig", "isFraud", "type"], nrows=n)
    # synthetic -> materialize generator
    rows = list(synthetic_stream(n=n))
    return pd.DataFrame(rows)
