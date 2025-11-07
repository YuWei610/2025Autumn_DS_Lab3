# -*- coding: utf-8 -*-
# FastAPI backend that randomly delays or fails.
# Environment variables control behavior:
#   FAILURE_RATE: float in [0,1], probability of HTTP 500
#   MAX_DELAY_MS: int, max random latency in milliseconds
#   SLOW_RATE: float in [0,1], probability to add latency

import os
import random
import time
from fastapi import FastAPI, Response

app = FastAPI()

FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.2"))
SLOW_RATE = float(os.getenv("SLOW_RATE", "0.3"))
MAX_DELAY_MS = int(os.getenv("MAX_DELAY_MS", "800"))

@app.get("/work")
def work():
    # Maybe add latency
    if random.random() < SLOW_RATE:
        # Add random delay up to MAX_DELAY_MS
        time.sleep(random.randint(0, MAX_DELAY_MS) / 1000.0)
    # Maybe fail
    if random.random() < FAILURE_RATE:
        return Response(content="backend error", status_code=500)
    return {"ok": True, "ts": time.time()}
