import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime


log_file = "transitions.log"
pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .* \[CB Transition\] (\w+) -> (\w+)"

rows = []
with open(log_file) as f:
    for line in f:
        m = re.search(pattern, line)
        if m:
            t, from_state, to_state = m.groups()
            rows.append({"time": datetime.strptime(t, "%Y-%m-%d %H:%M:%S"),
                         "from": from_state, "to": to_state})

df = pd.DataFrame(rows)


fig, ax = plt.subplots(figsize=(10, 3))
ax.plot(df["time"], df["to"], marker="o", linestyle="-")
ax.set_title("Circuit Breaker State Transitions Over Time")
ax.set_xlabel("Time")
ax.set_ylabel("State")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
