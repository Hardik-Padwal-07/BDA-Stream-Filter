"""Try to download real PaySim, fallback to synthetic generator.
Usage: python scripts/download_paysim.py --n 500000
"""
import argparse
import os
import sys
import urllib.request

CANDIDATE_URLS = [
    # small public samples / mirrors (full PaySim ~500MB lives on Kaggle, needs login)
    "https://raw.githubusercontent.com/EdgarLopezPhD/PaySim/master/data/paysim_sample.csv",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def try_download(url: str, dest: str) -> bool:
    try:
        print(f"Trying {url} ...")
        urllib.request.urlretrieve(url, dest)
        if os.path.getsize(dest) > 1000:
            print(f"Downloaded {dest}")
            return True
        os.remove(dest)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"Failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100000,
                    help="rows for synthetic fallback")
    ap.add_argument("--out", type=str, default="data/paysim_sample.csv")
    args = ap.parse_args()
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    for url in CANDIDATE_URLS:
        tmp = out + ".tmp"
        if try_download(url, tmp):
            os.replace(tmp, out)
            print("Real PaySim sample downloaded.")
            return

    print("No public direct download (full PaySim needs Kaggle login).")
    print(f"Generating synthetic PaySim-like data ({args.n} rows) ...")
    sys.path.insert(0, ROOT)
    from scripts.make_synthetic import make_paysim_like
    if os.path.exists(out):
        os.remove(out)
    make_paysim_like(args.n, out)
    print("Done. To use REAL PaySim: download PS_20174392719_1491204439457_log.csv "
          "from Kaggle (search 'paysim1') and save as data/paysim_full.csv")


if __name__ == "__main__":
    main()
