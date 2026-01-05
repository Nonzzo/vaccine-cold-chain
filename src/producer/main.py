import time
import json
import random
import os
from kafka import KafkaProducer
from prometheus_client import start_http_server, Counter, Gauge

start_http_server(8000)

# Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'vaccine-cluster-kafka-bootstrap.kafka.svc:9092')
TOPIC = 'vaccine-telemetry'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

truck_ids = ["TRUCK-001", "TRUCK-002", "TRUCK-003"]

print(f"Starting Producer connected to {KAFKA_BROKER}")

# Metrics
ANOMALY_COUNTER = Counter('vaccine_anomaly_detected_total', 'Total temperature violations detected', ['truck_id'])
TEMP_GAUGE = Gauge('truck_temperature_celsius', 'Current temperature', ['truck_id'])
MESSAGES_PRODUCED = Counter('vaccine_messages_produced_total', 'Total messages produced', ['truck_id'])

while True:
    for truck in truck_ids:
        # Simulate Normal Temp (-20 to -15)
        temp = round(random.uniform(-20, -15), 2)
        
        # 10% chance of Cooling Failure (Temp rises to -5)
        is_anomaly = False
        if random.random() < 0.1:
            temp = round(random.uniform(-5, 0), 2)
            print(f"⚠️  SIMULATING FAILURE on {truck}: {temp}C", flush=True)
            ANOMALY_COUNTER.labels(truck_id=truck).inc()  # ← UPDATE METRIC
            is_anomaly = True

        payload = {
            "truck_id": truck,
            "timestamp": time.time(),
            "temperature": temp,
            "gps_lat": 40.7128,
            "gps_lon": -74.0060
        }
        
        producer.send(TOPIC, payload)
        
        TEMP_GAUGE.labels(truck_id=truck).set(temp)
        MESSAGES_PRODUCED.labels(truck_id=truck).inc()
        
    time.sleep(2)