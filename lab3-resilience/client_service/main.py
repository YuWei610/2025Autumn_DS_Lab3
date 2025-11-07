# -*- coding: utf-8 -*-
# FastAPI client with Circuit Breaker + Retry (with visible retry logs)

import os
import time
import threading
import logging
import httpx
from typing import Optional
from fastapi import FastAPI
from pybreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerListener
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log
)

# === Logging setup ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# Enable tenacity retry logs (this line makes retry attempts visible)
logging.getLogger("tenacity.retry").setLevel(logging.INFO)

app = FastAPI()

# === Load environment variables ===
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/work")
CB_FAIL_MAX = int(os.getenv("CB_FAIL_MAX", "2"))
CB_RESET_TIMEOUT = int(os.getenv("CB_RESET_TIMEOUT", "1"))
CB_HALF_OPEN_MAX_CALLS = int(os.getenv("CB_HALF_OPEN_MAX_CALLS", "1"))
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "1"))
RETRY_BASE = float(os.getenv("RETRY_BASE", "0.2"))
RETRY_MAX = float(os.getenv("RETRY_MAX", "2.0"))

# === Listener for state transitions ===
class LogTransitions(CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logging.warning(
            f"[CB Transition] {getattr(old_state, 'name', str(old_state)).upper()} -> {getattr(new_state, 'name', str(new_state)).upper()}"
        )

# === Circuit Breaker setup ===
breaker = CircuitBreaker(
    fail_max=CB_FAIL_MAX,
    reset_timeout=CB_RESET_TIMEOUT,
    name="backend-breaker",
    listeners=[LogTransitions()]
)

client = httpx.Client(timeout=2.0)

# === Custom transient error ===
class TransientError(Exception):
    pass

# === Retry logic (now with visible log messages) ===
@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    wait=wait_exponential_jitter(exp_base=RETRY_BASE, max=RETRY_MAX),
    retry=retry_if_exception_type(TransientError),
    before_sleep=before_sleep_log(logging.getLogger("tenacity.retry"), logging.WARNING)
)
def fetch_with_retry() -> dict:
    """GET backend with retry and exponential backoff + jitter"""
    r = client.get(BACKEND_URL)
    if r.status_code >= 500:
        raise TransientError(f"server error {r.status_code}")
    return r.json()

def call_backend() -> Optional[dict]:
    try:
        return breaker.call(fetch_with_retry)
    except CircuitBreakerError:
        logging.warning("Breaker OPEN: fast-fail without calling backend")
        return {"error": "circuit breaker open"}
    except Exception as e:
        return {"error": str(e)}

# === Worker loop ===
def worker_loop():
    last_state = None
    while True:
        state_obj = breaker.current_state
        state_name = getattr(state_obj, "name", str(state_obj)).upper()

        if state_name != last_state:
            logging.warning(f"Breaker state changed → {state_name}")
            last_state = state_name

        try:
            # Handle OPEN state manually
            if state_name == "OPEN":
                opened_at = getattr(breaker._state_storage, "_CircuitBreakerStorage__state_opened_at", None)
                if opened_at:
                    elapsed = time.time() - opened_at
                    if elapsed >= breaker.reset_timeout:
                        logging.warning(
                            f"Breaker has been OPEN for {elapsed:.2f}s ≥ {breaker.reset_timeout}s → forcing HALF_OPEN test call..."
                        )
                        try:
                            breaker.call(fetch_with_retry)
                        except Exception as e:
                            logging.warning(f"HALF_OPEN test failed: {e}")
                        time.sleep(0.5)
                        continue
                    else:
                        logging.info(f"Breaker still OPEN ({elapsed:.2f}s/{breaker.reset_timeout}s)")
                        time.sleep(0.3)
                        continue

            result = call_backend()
            logging.info(f"Breaker={state_name} result={result}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        time.sleep(0.3)

threading.Thread(target=worker_loop, daemon=True).start()

@app.get("/health")
def health():
    return {
        "breaker_state": str(breaker.current_state),
        "config": {
            "CB_FAIL_MAX": CB_FAIL_MAX,
            "CB_RESET_TIMEOUT": CB_RESET_TIMEOUT,
            "CB_HALF_OPEN_MAX_CALLS": CB_HALF_OPEN_MAX_CALLS,
            "RETRY_MAX_ATTEMPTS": RETRY_MAX_ATTEMPTS,
        },
    }

@app.get("/")
def root():
    return {"message": "Client resilience service running"}
