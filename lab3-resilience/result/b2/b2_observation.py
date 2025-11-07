# === Purpose: Visualize Retry + Backoff + Jitter behavior (3 figures) ===
# Figure A: Retry delay timeline (exponential backoff + jitter)
# Figure B: Success rate vs retry count
# Figure C: Combined view with Circuit Breaker states overlay

import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# === Read logs ===
with open("client.log") as f:
    log_lines = f.readlines()

# === Extract retry delays ===
retry_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ WARNING Retrying .* in ([\d\.]+) seconds')
retry_records = []
for line in log_lines:
    m = retry_pattern.search(line)
    if m:
        retry_records.append({
            "time": datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S"),
            "delay": float(m[2])
        })
df_retry = pd.DataFrame(retry_records)

# === Extract success rate (if available) ===
# You may reuse your previous outcome_rate.csv
df_success = pd.read_csv("outcome_rate.csv")
df_success["time"] = pd.to_datetime(df_success["time"], format="%H:%M:%S")

# === Extract Circuit Breaker transitions ===
cb_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}).*\[CB Transition\] (\w+) -> (\w+)')
cb_records = []
for line in log_lines:
    m = cb_pattern.search(line)
    if m:
        cb_records.append({
            "time": datetime.strptime(m[1], "%H:%M:%S"),
            "from": m[2],
            "to": m[3]
        })
df_cb = pd.DataFrame(cb_records)
df_cb["next_time"] = df_cb["time"].shift(-1, fill_value=df_success["time"].max())
df_cb["state"] = df_cb["to"]

# === Color mapping for states ===
state_colors = {
    "OPEN": ("#FF4C4C", 0.25),
    "HALF-OPEN": ("#FFD700", 0.35),
    "CLOSED": ("#32CD32", 0.2)
}

# === FIGURE A: Retry delay timeline ===
plt.figure(figsize=(10,5))
plt.plot(df_retry["time"], df_retry["delay"], marker="o", color="orange", linewidth=1.8)
plt.title("Figure A: Retry Delay Timeline (Exponential Backoff + Jitter)")
plt.xlabel("Time")
plt.ylabel("Delay before next retry (s)")
plt.grid(True, alpha=0.4)
plt.tight_layout()
plt.show()

# === FIGURE B: Success rate vs retry count ===
# Simulated example: aggregate retry attempts into bins
if not df_retry.empty:
    df_retry["attempt_id"] = range(1, len(df_retry)+1)
    retry_summary = df_retry.groupby(pd.cut(df_retry["attempt_id"], bins=5)).agg({"delay": "mean"}).reset_index()
    retry_summary["success_rate"] = [60, 70, 80, 85, 90]  # demo values, adjust from your experiment
    plt.figure(figsize=(8,5))
    plt.plot(range(1,6), retry_summary["success_rate"], marker="o", color="blue")
    plt.title("Figure B: Success Rate Improvement per Retry Attempt")
    plt.xlabel("Retry Attempt")
    plt.ylabel("Success Rate (%)")
    plt.grid(True, alpha=0.5)
    plt.tight_layout()
    plt.show()

# === FIGURE C: Combined Breaker states + Success rate ===
plt.figure(figsize=(12,6))
plt.plot(df_success["time"], df_success["success_rate"], color="blue", linewidth=1.5, label="Success Rate")

# Overlay breaker states as background spans
for _, row in df_cb.iterrows():
    color, alpha = state_colors.get(row["state"], ("gray", 0.15))
    plt.axvspan(row["time"], row["next_time"], color=color, alpha=alpha)

# Overlay retry markers
plt.scatter(df_retry["time"], [1.05]*len(df_retry), color="orange", s=30, label="Retry Events", zorder=5)

plt.xlabel("Time")
plt.ylabel("Success Rate")
plt.title("Figure C: Combined View (Circuit Breaker States + Retry Events)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.show()
