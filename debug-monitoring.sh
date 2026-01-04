#!/bin/bash

echo "=== 1. Check Producer Metrics ==="
kubectl exec -it deployment/vaccine-producer -n kafka -- curl -s localhost:8000/metrics 2>/dev/null | head -10 || echo "ERROR: Can't reach metrics"

echo ""
echo "=== 2. Check Consumer Metrics ==="
kubectl exec -it deployment/vaccine-consumer -n kafka -- curl -s localhost:8000/metrics 2>/dev/null | head -10 || echo "ERROR: Can't reach metrics"

echo ""
echo "=== 3. Check Prometheus Targets ==="
curl -s 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | {labels: .labels, health: .health}' 2>/dev/null || echo "ERROR: Prometheus not accessible"

echo ""
echo "=== 4. Check Available Metrics in Prometheus ==="
curl -s 'http://localhost:9090/api/v1/label/__name__/values' | jq '.data[]' 2>/dev/null | grep -v "^prometheus" | grep -v "^process" | head -20 || echo "ERROR: No custom metrics found"

echo ""
echo "=== 5. Query Temperature Metric ==="
curl -s 'http://localhost:9090/api/v1/query?query=truck_temperature_celsius' | jq '.data.result' 2>/dev/null || echo "No data for truck_temperature_celsius"

echo ""
echo "=== 6. Query Anomaly Metric ==="
curl -s 'http://localhost:9090/api/v1/query?query=vaccine_anomaly_detected_total' | jq '.data.result' 2>/dev/null || echo "No data for vaccine_anomaly_detected_total"

echo ""
echo "=== 7. Check Grafana Health ==="
curl -s 'http://localhost:3000/api/health' | jq '.' 2>/dev/null || echo "ERROR: Grafana not accessible"

echo ""
echo "=== Done ==="