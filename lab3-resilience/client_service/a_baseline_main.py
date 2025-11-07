# -*- coding: utf-8 -*-
# ============================================================
# Part A: Baseline version (No Circuit Breaker, No Retry)
# ============================================================
# This client simply calls the backend directly without any resilience mechanisms.

from fastapi import FastAPI
import requests
import time

app = FastAPI()

BACKEND_URL = "http://backend:8000/process"


@app.get("/call-backend")
def call_backend():
    """Call backend directly without retry or circuit breaker"""
    start = time.time()
    try:
        response = requests.get(BACKEND_URL, timeout=2)  # direct call
        latency = round(time.time() - start, 3)
        return {
            "state": "success",
            "latency": f"{latency}s",
            "result": response.json()
        }
    except requests.exceptions.RequestException as e:
        latency = round(time.time() - start, 3)
        print(f"Request failed: {e}")
        return {
            "state": "failed",
            "latency": f"{latency}s",
            "error": str(e)
        }


# === NEWLY ADDED SECTION ===
# Optional: simple root endpoint for quick health check
@app.get("/")
def root():
    return {"message": "Client baseline is running"}


# === FastAPI entry point ===
# Use this command in Dockerfile: uvicorn main:app --host 0.0.0.0 --port 8001


# ============================================================
# === NEWLY ADDED SECTION ===
# Part B: Resilience version (Circuit Breaker + Retry + Jitter)
# ============================================================

import os
import threading
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from pybreaker import CircuitBreaker, CircuitBreakerError

# === NEWLY ADDED SECTION ===
# Create a new FastAPI app for the Resilience version
resilient_app = FastAPI(title="Client Service with Resilience Patterns")

# === NEWLY ADDED SECTION ===
# Read environment variables from ConfigMap
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/work")
CB_FAIL_MAX = int(os.getenv("CB_FAIL_MAX", "5"))
CB_RESET_TIMEOUT = int(os.getenv("CB_RESET_TIMEOUT", "10"))
CB_HALF_OPEN_MAX_CALLS = int(os.getenv("CB_HALF_OPEN_MAX_CALLS", "1"))
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_BASE = float(os.getenv("RETRY_BASE", "0.2"))
RETRY_MAX = float(os.getenv("RETRY_MAX", "2.0"))

# === NEWLY ADDED SECTION ===
# Initialize circuit breaker and retry logic
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
breaker = CircuitBreaker(fail_max=CB_FAIL_MAX, reset_timeout=CB_RESET_TIMEOUT, name="backend-cb")
client = httpx.Client(timeout=2.0)

class TransientError(Exception):
    """Custom exception for retryable transient errors"""
    pass

@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    wait=wait_exponential_jitter(exp_base=RETRY_BASE, max=RETRY_MAX),
    retry=retry_if_exception_type(TransientError)
)
def fetch_with_retry():
    """Call backend with retry and backoff"""
    try:
        r = client.get(BACKEND_URL)
        if r.status_code >= 500:
            raise TransientError(f"server error {r.status_code}")
        return r.json()
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        raise TransientError("timeout")

def call_backend_with_resilience():
    """Call backend through circuit breaker"""
    try:
        return breaker.call(fetch_with_retry)
    except CircuitBreakerError:
        logging.warning("Breaker OPEN: fast-fail without calling backend")
        return {"error": "circuit breaker open"}
    except Exception as e:
        logging.warning(f"Request failed: {e}")
        return {"error": str(e)}

def background_worker():
    """Continuous backend calling for resilience test"""
    while True:
        result = call_backend_with_resilience()
        logging.info(f"Breaker={breaker.current_state} result={result}")
        time.sleep(1)

threading.Thread(target=background_worker, daemon=True).start()

@resilient_app.get("/health")
def health():
    """Expose breaker state"""
    return {"breaker_state": str(breaker.current_state)}

# === NEWLY ADDED SECTION ===
# To switch from Baseline → Resilience:
#   Modify Dockerfile CMD to use resilient_app instead of app
#   CMD ["uvicorn", "main:resilient_app", "--host", "0.0.0.0", "--port", "8001"]
