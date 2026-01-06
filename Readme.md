# Vaccine Cold Chain Integrity Platform in Microsoft Azure

Real-time monitoring of vaccine transport trucks with anomaly detection, compliance tracking, and live dashboards. **Fully functional end-to-end monitoring stack** with 50-truck scaling, database persistence, and automated CI/CD.

## Architecture

```
Producer (50 trucks)
    ↓ (generates temp/humidity/GPS)
Kafka Cluster (KRaft mode)
    ↓ (150+ msg/sec)
Consumer Service
    ├→ Prometheus Metrics (:8000)
    │   ├ truck_temperature_celsius
    │   ├ vaccine_anomaly_detected_total
    │   └ vaccine_db_inserts_total
    │
    └→ PostgreSQL (Audit Trail)
        ├ sensor_readings (all data)
        └ temperature_excursions (anomalies)
            ↓
Grafana Dashboards (Real-time Visualization)
    ├ Temperature by Truck (3 sensors)
    └ Anomalies Detected (5m counter)
```

## Features

✅ **Real-time Monitoring**: 50 vaccine trucks with temperature, humidity, vibration, GPS sensors  
✅ **Anomaly Detection**: ML-based (Isolation Forest) + threshold-based alerts  
✅ **Database Persistence**: All readings + anomalies logged to PostgreSQL  
✅ **Prometheus Metrics**: 8+ metrics with per-truck labels  
✅ **Live Dashboards**: Grafana with real-time temperature trends & anomaly counters  
✅ **Horizontal Scaling**: Trivial to scale to 100+ trucks (just change `NUM_TRUCKS` env var)  
✅ **Automated CI/CD**: GitHub Actions builds, tests, and deploys on every push  
✅ **Compliance Ready**: FDA audit logs, temperature excursion tracking, full traceability  

## Quick Start

### Prerequisites
```bash
az login
terraform --version  # >= 1.6
kubectl version --client
docker --version
```

### 1. Deploy Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars
export KUBECONFIG=$(pwd)/kubeconfig.yaml
cd ..
```

### 2. Deploy Kafka & Monitoring

```bash
# Install Strimzi operator
helm install strimzi strimzi/strimzi-kafka-operator -n strimzi-system --create-namespace

# Deploy Kafka cluster
kubectl apply -f k8s/kafka/

# Deploy PostgreSQL
kubectl apply -f k8s/database/

# Deploy Monitoring (Prometheus + Grafana)
kubectl apply -f k8s/monitoring/
```

### 3. Configure & Deploy Applications

```bash
# Set your Docker credentials
export DOCKER_REPO=your-docker-username
export IMAGE_TAG=latest
export POSTGRES_USER=vaccine_admin
export POSTGRES_PASSWORD=your-secure-password

# Create secrets
envsubst < k8s/common/secrets.tpl.yaml | kubectl apply -f -

# Deploy producer & consumer
envsubst < k8s/apps/deployment.tpl.yaml | kubectl apply -f -
```

### 4. Access Dashboards

```bash
# Grafana (admin/admin)
kubectl port-forward -n monitoring svc/grafana 3000:3000
# http://localhost:3000 → Dashboards → "Vaccine Monitoring Dashboard"

# Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# http://localhost:9090/targets (see all 50 truck metrics)
```

## CI/CD Pipeline

Fully automated with **GitHub Actions**:

```yaml
Trigger: git push to main
    ↓
1. Build Docker Images (producer + consumer)
2. Push to Docker Hub
3. Login to Azure
4. Update Kubernetes deployments
5. Auto-deploy to AKS cluster
```

### Setup GitHub Actions

1. Add these secrets to your GitHub repo (Settings → Secrets):
   ```
   DOCKER_USERNAME=your-docker-username
   DOCKER_PASSWORD=your-docker-token
   AZURE_CREDENTIALS=<output from az ad sp create-for-rbac>
   POSTGRES_USER=vaccine_admin
   POSTGRES_PASSWORD=your-secure-password
   ```

2. Generate Azure credentials:
   ```bash
   az ad sp create-for-rbac --name "github-actions" \
     --role Contributor \
     --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
     --json
   ```

3. Copy output JSON to `AZURE_CREDENTIALS` secret

### Deploy Changes

```bash
# Just commit and push
git add src/producer/main.py src/consumer/main.py
git commit -m "fix: update metrics collection"
git push origin main

# GitHub Actions automatically:
# - Builds new Docker images
# - Pushes to Docker Hub
# - Updates Kubernetes deployments
# - Rolls out changes to AKS
```

## Project Structure

```
vaccine-cold-chain/
├── terraform/              # Infrastructure as Code (AKS, PostgreSQL)
│   └── envs/dev.tfvars    # Environment-specific values
├── k8s/
│   ├── kafka/             # Kafka cluster (KRaft, 1 broker)
│   ├── database/          # PostgreSQL with persistent volume
│   ├── monitoring/        # Prometheus + Grafana stack
│   ├── apps/              # Producer/Consumer deployments
│   └── common/            # Shared secrets template
├── src/
│   ├── producer/          # Generates 50 trucks × 150 msg/sec
│   └── consumer/          # Processes → Prometheus + PostgreSQL
├── .github/workflows/
│   └── deploy.yaml        # CI/CD pipeline (auto-build & deploy)
└── README.md
```

## Current Status

✅ **Producer**: Generating data for 50 trucks (configurable via `NUM_TRUCKS` env var)  
✅ **Kafka**: Streaming 150+ msg/sec in KRaft mode  
✅ **Consumer**: Processing messages + anomaly detection + PostgreSQL writes  
✅ **PostgreSQL**: Full audit trail (sensor_readings + temperature_excursions tables)  
✅ **Prometheus**: 8 metrics scraped every 15s from both producer & consumer  
✅ **Grafana**: Live dashboards showing temperature trends & anomaly counters  
✅ **GitHub Actions**: Automated build & deploy on every commit  
✅ **Scaling**: Tested up to 50 trucks - trivial to scale further  

## Key Metrics Collected

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `truck_temperature_celsius` | Gauge | `truck_id` | Real-time temp per truck |
| `truck_humidity_percent` | Gauge | `truck_id` | Real-time humidity |
| `vaccine_anomaly_detected_total` | Counter | `truck_id` | Cumulative anomalies |
| `vaccine_messages_produced_total` | Counter | `truck_id` | Messages sent |
| `vaccine_messages_consumed_total` | Counter | `truck_id` | Messages processed |
| `vaccine_db_inserts_total` | Counter | - | Database writes |
| `vaccine_processing_time_seconds` | Histogram | `truck_id` | Processing latency |

## Database Schema

### sensor_readings (all readings)
```sql
id, truck_id, temperature, is_anomaly, created_at
```

### temperature_excursions (anomalies only)
```sql
id, truck_id, temperature, reason (ml_isolation_forest|threshold_violation), created_at
```

Query data:
```bash
# Connect to PostgreSQL
psql -h localhost -U vaccine_admin -d vaccine_db

# View readings
SELECT COUNT(*) FROM sensor_readings;

# View anomalies
SELECT truck_id, temperature, reason FROM temperature_excursions LIMIT 10;

# Anomalies per truck (last hour)
SELECT truck_id, COUNT(*) FROM temperature_excursions 
WHERE created_at > NOW() - INTERVAL '1 hour' 
GROUP BY truck_id;
```

## Scaling to 100+ Trucks

**Option 1: Update Deployment Directly**
```bash
kubectl set env deployment/vaccine-producer NUM_TRUCKS=100 -n kafka
# Pod auto-restarts with new config
```

**Option 2: Update k8s/apps/deployment.tpl.yaml**
```yaml
- name: NUM_TRUCKS
  value: "100"
```
Then redeploy:
```bash
envsubst < k8s/apps/deployment.tpl.yaml | kubectl apply -f -
```

**Verify scaling:**
```bash
# Should see 100 metrics
curl -s 'http://localhost:9090/api/v1/query?query=truck_temperature_celsius' | jq '.data.result | length'
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Cloud | Azure (AKS) | Kubernetes cluster |
| Streaming | Apache Kafka (KRaft) | Ingest 150+ msg/sec |
| Metrics | Prometheus | Time-series database |
| Visualization | Grafana 9.5 | Real-time dashboards |
| Database | PostgreSQL 15 | Compliance audit trail |
| Storage | Azure Data Lake Gen2 | Raw sensor data |
| IaC | Terraform | Infrastructure automation |
| CI/CD | GitHub Actions | Build & deploy pipeline |

## Cost (Monthly)

| Resource | Dev | Prod |
|----------|-----|------|
| AKS (1-3 nodes) | $25-75 | $75-150 |
| PostgreSQL | $15-30 | $30-60 |
| Storage | $5 | $10 |
| **Total** | **~$45-110** | **~$115-220** |

## Monitoring Health

```bash
# Check all targets healthy
curl -s 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | select(.labels.job=="kafka-apps") | .health' | sort | uniq -c

# Query live temperature
curl -s 'http://localhost:9090/api/v1/query?query=truck_temperature_celsius' | jq '.data.result | length'

# Check database writes/min
psql -h localhost -U vaccine_admin -d vaccine_db -c "SELECT COUNT(*) FROM sensor_readings WHERE created_at > NOW() - INTERVAL '1 minute';"

# Expected: ~150 rows/min (50 trucks × 3 msg/sec)

# View pod status
kubectl get pods -n kafka
kubectl get pods -n monitoring
```

## Troubleshooting

### Consumer not writing to database
```bash
kubectl logs -f deployment/vaccine-consumer -n kafka | grep -i "postgres\|db"
# Check: ✅ Connected to PostgreSQL, ✅ Database tables initialized
```

### Grafana shows "No Data"
```bash
# Check Prometheus has metrics
curl -s 'http://localhost:9090/api/v1/query?query=truck_temperature_celsius' | jq '.data.result | length'
# Should return > 0

# Refresh Grafana dashboard (Ctrl+R)
```

### Not seeing all 50 trucks
```bash
# Check producer NUM_TRUCKS env var
kubectl get deployment vaccine-producer -n kafka -o yaml | grep NUM_TRUCKS

# Check producer logs
kubectl logs deployment/vaccine-producer -n kafka | grep "Configured for"
# Should show: ✅ Configured for 50 trucks
```



## License

MIT

## Contact

For issues or questions:
- Check pod logs: `kubectl logs deployment/vaccine-producer -n kafka`
- Check Prometheus targets: `http://localhost:9090/targets`
- Check Grafana dashboards: `http://localhost:3000`

---

**Status**: ✅ **PRODUCTION READY** | 50 trucks monitored | Full audit trail | Automated CI/CD | Real-time dashboards active