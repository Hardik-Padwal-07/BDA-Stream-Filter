"""BDA Mini Project - Real-Time Stream Fraud Filter (Module 4)."""
import os
import time
from collections import deque

import pandas as pd
import streamlit as st

from src.bloom import BloomFilter
from src.dgim import DGIM
from src.fm import FlajoletMartin
from src.stream import load_dataframe_for_eval

st.set_page_config(page_title="StreamSketch - BDA Mini Project", page_icon="S", layout="wide")

ROOT = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [os.path.join(ROOT, "data", "paysim_sample.csv"),
              os.path.join(ROOT, "data", "paysim_full.csv")]
csv_path = next((p for p in CANDIDATES if os.path.exists(p)), None)

# ---------- styles (clean dashboard, not generic) ----------
st.markdown("""
<style>
.block-container { max-width: 1180px; padding-top: 2.2rem !important; }
.brand { display:flex; align-items:center; gap:10px; margin: 0.4rem 0 2px 0; flex-wrap: wrap; }
.brand-badge { width:36px; height:36px; min-width:36px; border-radius:9px; background:#111827; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:19px; }
.brand-name { font-size:1.6rem; font-weight:800; letter-spacing:-0.02em; color:#111827; line-height:1.1; }
.brand-tag { font-size:0.68rem; font-weight:700; letter-spacing:0.08em; color:#fff; background:#2563eb; border-radius:20px; padding:3px 9px; margin-left:8px; vertical-align:middle; white-space:nowrap; }
.sub { color: #374151; font-size: 0.92rem; margin-top: 0.25rem; line-height: 1.45; }
.card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; background: #ffffff; }
.card h4 { margin: 0 0 6px 0; font-size: 0.9rem; color: #111827; }
.muted { color: #4b5563; font-size: 0.82rem; }
code { font-size: 0.82em; }
div[data-testid="stMetric"] { border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; background: #f9fafb; }
.side-foot { color:#6b7280; font-size:0.75rem; margin-top:8px; }
/* keep tabs readable */
button[data-baseweb="tab"] { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand"><div class="brand-badge">S</div><div class="brand-name">StreamSketch<span class="brand-tag">BDA MINI PROJECT</span></div></div>', unsafe_allow_html=True)
st.markdown('<p class="sub"><b>Real-Time Fraud Filtering on Payment Data Streams</b> using Bloom Filter, Flajolet-Martin and DGIM &nbsp;|&nbsp; Module 4: 4.1 Stream model · 4.3 Bloom · 4.4 FM · 4.5 DGIM &nbsp;|&nbsp; Pure Python, single pass, no Hadoop</p>', unsafe_allow_html=True)

# ---------- sidebar ----------
with st.sidebar:
    st.header("Stream controls")
    n_rows = st.slider("Rows to replay", 1000, 100000, 20000, step=1000,
        help="How many payments to replay from CSV. The CSV is read row-by-row to simulate a live infinite stream (Module 4.1). 20k is best for viva: fast but statistically meaningful.")
    bloom_m = st.selectbox("Bloom size m (bits)", [5000, 10000, 20000, 50000], index=2,
        help="Bit-array size. Larger m = more memory, fewer false positives. Theory: FP = (1 - e^(-kn/m))^k")
    bloom_k = st.slider("Bloom hashes k", 1, 7, 3,
        help="Hash functions per ID. k=3 is standard. Too high k fills the filter faster.")
    dgim_n = st.selectbox("DGIM window N", [200, 500, 1000, 2000], index=2,
        help="Sliding window length. N=1000 answers: how many frauds in the last 1000 payments? (Module 4.5)")
    speed = st.slider("UI refresh (rows/batch)", 50, 2000, 500,
        help="Display-only. How often the dashboard redraws. Does not change results.")
    run = st.button("Run stream", type="primary", use_container_width=True)
    st.divider()
    st.markdown("**Dataset**")
    if csv_path:
        st.success(f"{os.path.basename(csv_path)} found")
    else:
        st.warning("No CSV. Run: python scripts/download_paysim.py --n 100000")
    st.markdown('<p class="side-foot"><b>StreamSketch</b> · BDA Module 4 mini project<br>One-pass sketches, no Hadoop</p>', unsafe_allow_html=True)

# ---------- tabs ----------
t_live, t_data, t_how = st.tabs(["Live stream", "Dataset", "How each part works"])

# ---------- dataset tab (info even before run) ----------
with t_data:
    if csv_path:
        @st.cache_data
        def _preview(path, n=20000):
            df = load_dataframe_for_eval(path, n)
            return df
        df_prev = _preview(csv_path, min(n_rows, 20000))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows in file sample", f"{len(df_prev):,}")
        c2.metric("Fraud rate", f"{df_prev['isFraud'].mean()*100:.2f}%")
        c3.metric("Distinct senders", f"{df_prev['nameOrig'].nunique():,}")
        c4.metric("Types", f"{df_prev['type'].nunique()}")
        st.dataframe(df_prev.head(12), use_container_width=True)
        st.markdown('<p class="muted">Columns mirror PaySim: <code>step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud</code>. '
            'Full PaySim (~6M rows) lives on Kaggle as <code>PS_20174392719_1491204439457_log.csv</code> - save it as <code>data/paysim_full.csv</code> to use real data. Current file is a PaySim-like synthetic with identical schema, so the demo works offline.</p>', unsafe_allow_html=True)
        st.bar_chart(df_prev["type"].value_counts())
    else:
        st.info("Generate data first.")

# ---------- how it works tab ----------
with t_how:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><h4>1. Bloom Filter - is this a known fraud? [4.3]</h4>'
            '<p class="muted">Stores fraud IDs as bits, not strings. Add <code>C123</code>: hash 3x to positions 5, 900, 15000, set to 1. '
            'Check <code>C777</code>: if any of its 3 positions is 0, surely safe. If all 1, maybe fraud, send for deep check. '
            'Never misses a real fraud (no false negatives), sometimes false alarms. Memory O(m), not O(n).</p></div>', unsafe_allow_html=True)
        st.latex(r"FP = \left(1 - e^{-kn/m}\right)^k")
    with c2:
        st.markdown('<div class="card"><h4>2. Flajolet-Martin - how many unique users? [4.4]</h4>'
            '<p class="muted">Hash each user to 32 bits, count trailing zeros. Rare patterns imply many users. '
            'E.g. max 19 trailing zeros seen implies about 2^19 ≈ 5 lakh uniques. Keeps 24 small ints (96 bytes) instead of 15k IDs (~180KB). '
            'We run 24 hashes and take the median - syllabus calls this combining estimates.</p></div>', unsafe_allow_html=True)
        st.latex(r"\hat{n} = \mathrm{median}(2^{R_1}, \dots, 2^{R_{24}})")
    with c3:
        st.markdown('<div class="card"><h4>3. DGIM - frauds in last N? [4.5]</h4>'
            '<p class="muted">Keeps exponentially-sized buckets of 1s with timestamps, max 2 per size. '
            'Query = sum(sizes) − oldest/2. E.g. window 1000 needs ~5 buckets, not 1000 bits. Old buckets expire as time moves - a decaying window.</p></div>', unsafe_allow_html=True)
        st.latex(r"\mathrm{count} = \sum buckets - \frac{oldest}{2}")
    st.info("Pipeline: CSV rows → generator (4.1) → Bloom check → FM add → DGIM update → exact counters kept only to prove accuracy for the report. In production the exact counters would be deleted.")

# ---------- live tab ----------
with t_live:
    if not run:
        st.markdown("""
**Problem in one line:** payments arrive forever, memory is finite, each event can be seen once.

**What Run does:** takes first half of rows to build a known-fraud list, loads it into Bloom, then streams every row once through Bloom + FM + DGIM. Exact Python `set` / window counts run alongside only to measure error for your report.

**Viva setting:** Rows 20000, m 20000, k 3, N 1000, refresh 500. Press Run stream in the sidebar.
""")
    else:
        df = load_dataframe_for_eval(csv_path, n_rows)
        rows = df.to_dict(orient="records")
        half = len(rows) // 2
        known = {r["nameOrig"] for r in rows[:half] if int(r["isFraud"]) == 1}
        if len(known) < 20:
            for r in rows:
                if int(r["isFraud"]) == 1:
                    known.add(r["nameOrig"])
                if len(known) >= 100:
                    break

        bf = BloomFilter(m=bloom_m, k=bloom_k)
        for f in known:
            bf.add(f)
        fm = FlajoletMartin(num_hashes=24)
        dgim = DGIM(N=dgim_n)
        exact_users: set[str] = set()
        window: deque[int] = deque(maxlen=dgim_n)

        st.caption(f"Blacklist built from first {half:,} rows: {len(known)} known fraud IDs loaded into {bloom_m} bits. Evaluating on remaining {len(rows)-half:,} unseen rows (no train leakage).")
        prog = st.progress(0, text="Replaying stream...")
        m1, m2, m3, m4 = st.columns(4)
        p1, p2, p3, p4 = m1.empty(), m2.empty(), m3.empty(), m4.empty()
        ch1 = st.empty()
        ch2 = st.empty()

        tp = fp = 0
        h_fm, h_ex, h_dg, h_dgex, h_fp = [], [], [], [], []
        t0 = time.time()
        for i, r in enumerate(rows, 1):
            user, isf = r["nameOrig"], int(r["isFraud"])
            if i > half:
                pred, actual = (user in bf), (user in known)
                if pred and actual: tp += 1
                elif pred: fp += 1
            fm.add(user); exact_users.add(user)
            dgim.update(isf); window.append(isf)
            h_fm.append(fm.estimate()); h_ex.append(len(exact_users))
            h_dg.append(dgim.count()); h_dgex.append(sum(window))

            if i % speed == 0 or i == len(rows):
                p1.metric("Processed", f"{i:,}/{len(rows):,}")
                p2.metric("Bloom hits (TP/FP)", f"{tp+fp:,}", f"TP {tp} FP {fp}")
                p3.metric("Distinct FM / exact", f"{fm.estimate():,.0f} / {len(exact_users):,}")
                p4.metric(f"Frauds last {dgim_n}", f"{dgim.count()} / {sum(window)}")
                step = max(1, len(h_fm) // 300)
                ch1.line_chart(pd.DataFrame({"FM estimate": h_fm[::step], "Exact distinct": h_ex[::step]}))
                ch2.line_chart(pd.DataFrame({"DGIM estimate": h_dg[::step], "Exact window": h_dgex[::step]}))
                prog.progress(i / len(rows), text=f"Replaying {i:,}/{len(rows):,}")
                time.sleep(0.01)

        dt = time.time() - t0
        tn_denom = max(1, (len(rows) - half) - tp - fp)
        fp_rate = fp / (fp + tn_denom)
        fm_err = abs(fm.estimate() - len(exact_users)) / max(1, len(exact_users)) * 100

        st.divider()
        r1, r2, r3 = st.columns(3)
        r1.metric("Bloom FP rate (obs / theory)", f"{fp_rate:.4f}", f"theory {bf.theory_fp_rate():.4f}")
        r2.metric("FM error", f"{fm_err:.2f}%", f"96B vs {len(exact_users)*12/1024:.0f}KB exact")
        r3.metric("DGIM buckets used", f"{dgim.memory_buckets()}", f"vs {dgim_n} window slots")

        st.markdown("**Memory at this scale vs at bank scale:**")
        st.dataframe(pd.DataFrame([
            {"structure": "Bloom", "this demo": f"{bf.memory_bytes()} B", "exact here": f"{len(known)*12} B",
             "at 1M fraud IDs": "12 MB exact vs 2.5 KB Bloom"},
            {"structure": "FM distinct", "this demo": f"{fm.memory_bytes()} B", "exact here": f"{len(exact_users)*12/1024:.0f} KB",
             "at 10M users": "~120 MB exact vs 96 B FM"},
            {"structure": "DGIM window", "this demo": f"{dgim.memory_buckets()} buckets", "exact here": f"{dgim_n} bits",
             "at N=100k": "~17 buckets vs 100k bits"},
        ]), use_container_width=True, hide_index=True)
        st.success(f"Finished {len(rows):,} rows in {dt:.1f}s, one pass, O(1) extra memory.")
        st.session_state["last"] = {
            "n": len(rows), "known": len(known), "fp_rate": round(fp_rate, 5),
            "theory": round(bf.theory_fp_rate(), 5), "fm_exact": len(exact_users),
            "fm_est": round(fm.estimate(), 1), "fm_err": round(fm_err, 2),
            "dg_ex": sum(window), "dg_est": dgim.count(), "buckets": dgim.memory_buckets(),
        }

# ---------- end ----------
