import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime

# === 1. Load success rate data ===
# Read CSV containing the client's success rate over time
df = pd.read_csv("outcome_rate.csv")
df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S")

# === 2. Parse circuit breaker transitions from log ===
# Updated regex: now matches states with hyphens (e.g., "HALF-OPEN")
pattern = re.compile(r"([0-9]{2}:[0-9]{2}:[0-9]{2}).*\[CB Transition\]\s+([A-Z\-]+)\s+->\s+([A-Z\-]+)")
records = []

with open("cb_states.log") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            records.append({
                "time": datetime.strptime(m[1], "%H:%M:%S"),
                "from": m[2],
                "to": m[3]
            })

cb = pd.DataFrame(records)

# === 3. Compute state intervals ===
# Each breaker state lasts until the next transition occurs
cb["next_time"] = cb["time"].shift(-1, fill_value=df["time"].max())
cb["state"] = cb["to"]

# === 4. Extend short intervals for better visualization ===
# Some states only last milliseconds; set a minimum 1s duration for display
min_interval = pd.Timedelta(seconds=1)
cb["next_time"] = cb["next_time"].where(
    (cb["next_time"] - cb["time"]) > min_interval,
    cb["time"] + min_interval
)

# === 5. Define colors and transparency for each breaker state ===
state_colors = {
    "OPEN": ("#FF4C4C", 0.35),       # Bright red
    "HALF-OPEN": ("#FFD700", 0.45),  # Gold
    "CLOSED": ("#32CD32", 0.25)      # Lime green
}

# === 6. Create visualization ===
fig, ax1 = plt.subplots(figsize=(14, 6))

# --- (a) Plot the success rate line ---
ax1.plot(df["time"], df["success_rate"], color="blue", linewidth=1.8, label="Success Rate")
ax1.set_xlabel("Time")
ax1.set_ylabel("Success Rate", color="blue")
ax1.tick_params(axis='y', labelcolor="blue")
ax1.grid(True, linestyle="--", alpha=0.4)

# --- (b) Overlay breaker state regions ---
for state, (color, alpha) in state_colors.items():
    subset = cb[cb["state"] == state]
    for _, row in subset.iterrows():
        ax1.axvspan(row["time"], row["next_time"],
                    color=color, alpha=alpha, zorder=-1, label=state)

# --- (c) Add state transition markers (optional for debugging) ---
for _, row in cb.iterrows():
    ax1.text(row["time"], 1.02, f"{row['from']}→{row['to']}",
             rotation=90, fontsize=6, color="green", ha="center", va="bottom")

# --- (d) Remove duplicate legends ---
handles, labels = ax1.get_legend_handles_labels()
unique = dict(zip(labels, handles))
ax1.legend(unique.values(), unique.keys(), loc="upper left")

# --- (e) Final layout and title ---
ax1.set_title("Circuit Breaker State Timeline vs Success Rate (FAILURE_RATE=0.7)", fontsize=13)
plt.tight_layout()
plt.show()
