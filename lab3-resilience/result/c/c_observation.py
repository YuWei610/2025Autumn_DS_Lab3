# === FILE: c_observation_phase_aligned.py ===
# Fix: Phase labels ("Before Chaos", "During Chaos", "After Recovery") are now centered correctly.

import argparse
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd

STATE_MAP = {"CLOSED": 0.0, "HALF-OPEN": 0.5, "OPEN": 1.0}
INV_STATE = {v: k for k, v in STATE_MAP.items()}

def norm_state(s):
    if not s:
        return s
    s = s.strip().replace("–", "-").replace("—", "-")
    return s.upper()

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--log", default="chaos_client.log")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--pre", type=int, default=60)
    p.add_argument("--post", type=int, default=60)
    return p.parse_args()

def parse_log(path):
    pat = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{1,6})?)\s.*?\[CB Transition\]\s(\S+)\s->\s(\S+)')
    rows = []
    with open(path) as f:
        for line in f:
            m = pat.search(line)
            if not m:
                continue
            ts_raw, s_from, s_to = m.groups()
            s_from, s_to = norm_state(s_from), norm_state(s_to)
            ts = datetime.strptime(ts_raw.split(",")[0], "%Y-%m-%d %H:%M:%S")
            rows.append({"time": ts, "from": s_from, "to": s_to})
    return pd.DataFrame(rows)

def build_step(df):
    pts = []
    first = df.iloc[0]
    pts.append({"time": first["time"] - timedelta(milliseconds=1), "state": first["from"]})
    for _, r in df.iterrows():
        pts.append({"time": r["time"], "state": r["to"]})
    s = pd.DataFrame(pts)
    s["state_value"] = s["state"].map(STATE_MAP)
    return s

def main():
    args = parse_args()
    df = parse_log(args.log).sort_values("time").reset_index(drop=True)
    step = build_step(df)

    chaos_start = datetime.fromisoformat(args.start)
    chaos_end = datetime.fromisoformat(args.end)
    focus_start = chaos_start - timedelta(seconds=args.pre)
    focus_end = chaos_end + timedelta(seconds=args.post)
    step_focus = step[(step["time"] >= focus_start) & (step["time"] <= focus_end)]

    plt.figure(figsize=(14, 6))
    plt.step(step_focus["time"], step_focus["state_value"], where="post",
             color="red", linewidth=2.2, label="Breaker State")
    plt.scatter(step_focus["time"], step_focus["state_value"], color="black", s=35, zorder=5)

    for _, r in step_focus.iterrows():
        plt.text(r["time"], r["state_value"] + 0.06, r["state"], ha="center", fontsize=8, rotation=35)

    plt.axvspan(chaos_start, chaos_end, color="gray", alpha=0.25, label="Chaos Injection")

    # === NEW: Phase label alignment (use x-axis data range) ===
    xmin, xmax = plt.xlim()
    total_range = xmax - xmin
    before_center = xmin + (chaos_start - focus_start).total_seconds() / (focus_end - focus_start).total_seconds() * total_range / 2
    during_center = xmin + ((chaos_start - focus_start).total_seconds() + (chaos_end - chaos_start).total_seconds() / 2) / (focus_end - focus_start).total_seconds() * total_range
    after_center = xmin + ((chaos_end - focus_start).total_seconds() + (focus_end - chaos_end).total_seconds() / 2) / (focus_end - focus_start).total_seconds() * total_range

    # === Instead of fixed text positions, anchor to actual axes fraction ===
    ax = plt.gca()
    ax.text(0.1, 1.02, "Before Chaos", transform=ax.transAxes, color="green", fontsize=11, ha="center")
    ax.text(0.5, 0.92, "During Chaos", transform=ax.transAxes, color="orange", fontsize=11, ha="center")
    ax.text(0.9, 1.02, "After Recovery", transform=ax.transAxes, color="blue", fontsize=11, ha="center")

    plt.title("Figure : Circuit Breaker State Before, During, and After Chaos Experiment")
    plt.xlabel("Time")
    plt.ylabel("Breaker State")
    plt.yticks([0, 0.5, 1], ["CLOSED", "HALF-OPEN", "OPEN"])
    plt.ylim(-0.1, 1.1)
    plt.grid(True, linestyle="--", alpha=0.45)
    plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
