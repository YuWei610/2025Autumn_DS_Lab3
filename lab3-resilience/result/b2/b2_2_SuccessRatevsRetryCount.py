# === Figure B: Success Rate vs Retry Count (based on real log data, normalized 0–1) ===
import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# === 1. Read client log ===
with open("client.log") as f:
    log_lines = f.readlines()

# === 2. Extract request outcomes (ok / error) ===
pattern = re.compile(r'(\d{2}:\d{2}:\d{2}).*result=\{\'(ok|error)\'')
records = []
for line in log_lines:
    m = pattern.search(line)
    if m:
        records.append({
            "time": datetime.strptime(m[1], "%H:%M:%S"),
            "status": m[2]
        })

df_status = pd.DataFrame(records)

# === 3. Compute success rate grouped by retry segments ===
if not df_status.empty:
    bins = 6  # 分成6段（依log長度可調整）
    df_status["group"] = pd.cut(df_status.index, bins=bins, labels=False) + 1

    # 計算每段成功率（0~1）
    retry_summary = (
        df_status.groupby("group")["status"]
        .apply(lambda x: (x == "ok").mean())
        .reset_index(name="success_rate")
    )

    # === 4. Plot ===
    plt.figure(figsize=(8, 5))
    plt.plot(
        retry_summary["group"],
        retry_summary["success_rate"],
        marker="o",
        color="blue",
        linewidth=1.6
    )

    # 平均成功率參考線
    avg_success = retry_summary["success_rate"].mean()
    plt.axhline(y=avg_success, color="gray", linestyle="--", alpha=0.6,
                label=f"Average = {avg_success:.2f}")

    # === 標題與標籤 ===
    plt.title("Figure B: Success Rate vs Retry Count (Observed)")
    plt.xlabel("Retry Attempt Group")
    plt.ylabel("Success Rate (0–1)")
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()
else:
    print("⚠️ No valid 'ok' or 'error' entries found in client.log.")
