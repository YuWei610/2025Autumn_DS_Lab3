

---

# **Distributed Systems Lab 3 – Resilience and Chaos Engineering**

## **1. Overview**

This lab demonstrates how to build a resilient distributed system using **FastAPI microservices** deployed on **Kubernetes**.
Two core services were developed:

* **Client Service** – Sends synchronous HTTP requests to the backend and implements **Circuit Breaker** and **Retry** patterns.
* **Backend Service** – Provides a basic endpoint with random delays or simulated failures.

The experiment includes **baseline tests**, **resilience pattern verification**, and a **chaos engineering phase** using the **Chaos Toolkit**.

---

## **2. Architecture**

```
[ Client Service ]  →  [ Backend Service ]
       ↑                       ↓
   Circuit Breaker, Retry   Random Delay / Failure
       |
 [ Chaos Toolkit ]
 (Terminates backend pod to simulate faults)
```

Both services are containerized and deployed within the same Kubernetes namespace (`lab3`).

---

## **3. Setup & Deployment**

### **3.1 Build Docker Images**

```bash
docker build -t lab3-backend:latest ./backend_service
docker build -t lab3-client:latest ./client_service
```

### **3.2 Deploy to Kubernetes**

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/client.yaml
```

### **3.3 Verify Deployment**

```bash
kubectl get pods -n lab3
kubectl logs -f deployment/client -n lab3
```

---

### **3.4 Rebuild and Deployment Workflow**

This section summarizes all essential commands for rebuilding Docker images, updating configurations, and verifying Kubernetes deployments during the experiment.
Each step includes English comments for quick reference when re-running the system or troubleshooting deployment issues.

---

#### **Environment & Cluster Setup**

```bash
# 1️⃣ Switch Docker environment to Minikube
eval $(minikube docker-env)
# (Allows building images directly inside Minikube's Docker daemon)
```

---

#### **Build & Verify Images**

```bash
# 2️⃣ Rebuild backend image without cache
docker build --no-cache -t lab3-backend:latest ./backend_service

# 3️⃣ Rebuild client image without cache
docker build --no-cache -t lab3-client:latest ./client_service

# 4️⃣ List Docker images inside Minikube
docker images
# (Check that the newly built 'lab3-backend' and 'lab3-client' images have the latest CREATED time)
```

---

#### **Clean Up Old Pods / Redeploy**

```bash
# 5️⃣ Delete old pods before redeployment
kubectl delete pod -l app=backend -n lab3
kubectl delete pod -l app=client -n lab3
# (Ensure old pods are removed before using new Docker images)
```

---

#### **Update Configurations**

```bash
# 6️⃣ Apply updated Kubernetes manifests (e.g., modified config or environment variables)
kubectl apply -f k8s/backend.yaml -n lab3
kubectl apply -f k8s/client.yaml -n lab3
# (Reapplies updated Deployment / ConfigMap / Environment settings)
```

---

#### **Restart Deployments (After Config Update)**

```bash
# 7️⃣ Restart client or backend to load new configurations
kubectl rollout restart deployment/client -n lab3
kubectl rollout restart deployment/backend -n lab3
# (Only restart the service whose configuration has changed)
```

---

#### **Monitor Pods and Logs**

```bash
# 8️⃣ Check current pod status
kubectl get pods -n lab3 -w
# (Use -w to continuously monitor until pods reach Running state)

# 9️⃣ View real-time logs of the client service
kubectl logs -f deployment/client -n lab3
# (Displays Circuit Breaker, Retry, and Chaos experiment logs)

# 🔟 Optional: View backend service logs
kubectl logs -f deployment/backend -n lab3
```

---

#### **Log Capture for Chaos Experiment**

```bash
# 🔹 Save client logs during chaos execution
kubectl logs -f deployment/client -n lab3 | tee chaos_client.log
# (Stores log output in a local file for visualization using c_observation.py)
```

---

## **4. Experiment Phases**

### **Part A: Baseline**

* Purpose: Establish the normal client–backend interaction.
* Observation:
  Client timed out when the backend became temporarily unavailable but recovered without system crash.

### **Part B: Resilience Patterns**

* Implemented **Circuit Breaker** (via `pybreaker`) and **Retry with Exponential Backoff** (via `tenacity`).
* The client maintained stability even under simulated backend delays.
* **Figure B** illustrated success rates across retry attempts, showing stable but limited recovery capability under repeated transient faults.

### **Part C: Chaos Engineering**

* Tool: **Chaos Toolkit** with Kubernetes extension.
* Action: Terminate backend pod (`terminate_pods`) and observe auto-recovery.
* Log capture:

  ```bash
  kubectl logs -f deployment/client -n lab3 | tee chaos_client.log
  ```
* **Figure C** visualized Circuit Breaker transitions (CLOSED → HALF-OPEN → OPEN) before, during, and after chaos injection.

---

## **5. Observations**

* The system recovered automatically after the backend pod restart.
* Frequent *OPEN ↔ HALF-OPEN* transitions indicated the breaker’s sensitivity to retry intervals.
* Kubernetes’ rapid pod recreation occasionally overlapped with the breaker’s cool-down window, suggesting that application- and platform-level resilience mechanisms must be tuned together.
* Overall, the resilience patterns prevented full service collapse during chaos injection.

---

## **6. Key Files**

| File                                 | Description                                           |
| ------------------------------------ | ----------------------------------------------------- |
| `backend_service/main.py`            | Backend endpoint with random delay/failure simulation |
| `client_service/main.py`             | Client with Circuit Breaker and Retry logic           |
| `client_service/a_baseline_main.py`  | Baseline client without resilience patterns           |
| `chaos/kill-backend-pod.json`        | Chaos Toolkit experiment definition                   |
| `result/b1`, `result/b2`, `result/c` | Logs and visualizations for each experiment phase     |

---

## **7. Conclusion Summary**

* **Architecture Learning:**
  Microservice separation improves fault isolation; Circuit Breaker + Retry mechanisms effectively contain transient failures.
* **Unexpected Findings:**
  Breaker transitions overlapped with Kubernetes recovery cycles, showing interaction complexity.
* **Recommendations:**
  Integrate observability (Prometheus, Grafana), expand fault injection types, and automate chaos testing within CI/CD pipelines.

---

## **8. References**

* *Chaos Toolkit Documentation*: [https://chaostoolkit.org](https://chaostoolkit.org)
* *PyBreaker*: [https://pypi.org/project/pybreaker](https://pypi.org/project/pybreaker)
* *Tenacity*: [https://tenacity.readthedocs.io](https://tenacity.readthedocs.io)
* *FastAPI Framework*: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)


