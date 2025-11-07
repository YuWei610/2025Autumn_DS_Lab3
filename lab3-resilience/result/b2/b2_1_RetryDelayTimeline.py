# === Figure A: Retry delay timeline (Exponential Backoff + Jitter) ===
import re, pandas as pd, matplotlib.pyplot as plt
from datetime import datetime

pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ WARNING Retrying .* in ([\d\.]+) seconds')
records = []

with open("client.log") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            records.append({
                "time": datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S"),
                "delay": float(m[2])
            })

df = pd.DataFrame(records)
plt.figure(figsize=(10,5))
plt.plot(df["time"], df["delay"], marker="o", color="orange")
plt.title("Figure A: Retry Delay Timeline (Exponential Backoff + Jitter)")
plt.xlabel("Time")
plt.ylabel("Delay before next retry (s)")
plt.grid(True, alpha=0.4)
plt.tight_layout()
plt.show()
