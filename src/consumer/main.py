import json
import os
import psycopg2
import time
from kafka import KafkaConsumer
from sklearn.ensemble import IsolationForest
import numpy as np
from prometheus_client import start_http_server, Counter, Gauge

# Connection Config
DB_HOST = "postgres-service.kafka.svc.cluster.local"
DB_NAME = "vaccine_db"
DB_USER = "vaccine_admin"
DB_PASS = "SuperSecretPassword"

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to DB: {e}")
        return None

# Metrics
ANOMALY_COUNTER = Counter('vaccine_anomaly_detected_total', 'Total temperature violations detected', ['truck_id'])
TEMP_GAUGE = Gauge('truck_temperature_celsius', 'Current temperature', ['truck_id'])
DB_INSERT_COUNTER = Counter('vaccine_db_inserts_total', 'Rows written to DB')

# ML Setup
rng = np.random.RandomState(42)
X_train = 0.3 * rng.randn(100, 1) - 20 
clf = IsolationForest(max_samples=100, random_state=rng)
clf.fit(X_train)

# Kafka Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'vaccine-cluster-kafka-bootstrap.kafka.svc:9092')
TOPIC = 'vaccine-telemetry'

print("Starting Consumer...")
start_http_server(8000) 

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    group_id='monitor-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Establish DB Connection
conn = get_db_connection()

print("Listening for messages...")
for message in consumer:
    try:
        data = message.value
        truck_id = data['truck_id']
        temp = data['temperature']
        
        # 1. Update Metrics
        TEMP_GAUGE.labels(truck_id=truck_id).set(temp)
        
        # 2. ML Check
        pred = clf.predict([[temp]])
        is_anomaly = False
        if pred[0] == -1:
            print(f"🚨 ANOMALY: {truck_id} at {temp}°C")
            ANOMALY_COUNTER.labels(truck_id=truck_id).inc()
            is_anomaly = True
        
        # 3. Write to DB (The Data Engineering Part)
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO sensor_readings (truck_id, temperature, is_anomaly) VALUES (%s, %s, %s)",
                    (truck_id, temp, is_anomaly)
                )
                conn.commit()
                DB_INSERT_COUNTER.inc()
                cur.close()
            except Exception as e:
                print(f"DB Write Error: {e}")
                conn.rollback()
                # Reconnect strategy could go here
    except Exception as e:
        print(f"Processing Error: {e}")