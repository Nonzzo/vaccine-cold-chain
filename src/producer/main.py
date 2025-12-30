import time
import json
import random
import os
from kafka import KafkaProducer

# Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'vaccine-cluster-kafka-bootstrap.kafka.svc:9092')
TOPIC = 'vaccine-telemetry'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

truck_ids = ["TRUCK-001", "TRUCK-002", "TRUCK-003"]

print(f"Starting Producer connected to {KAFKA_BROKER}")

while True:
    for truck in truck_ids:
        # Simulate Normal Temp (-20 to -15)
        temp = round(random.uniform(-20, -15), 2)
        
        # 10% chance of Cooling Failure (Temp rises to -5)
        if random.random() < 0.1:
            temp = round(random.uniform(-5, 0), 2)
            print(f"⚠️  SIMULATING FAILURE on {truck}: {temp}C")
            print(f"⚠️  SIMULATING FAILURE...", flush=True)

        payload = {
            "truck_id": truck,
            "timestamp": time.time(),
            "temperature": temp,
            "gps_lat": 40.7128,
            "gps_lon": -74.0060
        }
        
        producer.send(TOPIC, payload)
        
    time.sleep(2) # Send batch every 2 seconds