import json
import os
import sys
import time
from kafka import KafkaConsumer
from sklearn.ensemble import IsolationForest
import numpy as np
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import traceback

# PROMETHEUS METRICS
start_http_server(8000)

TEMP_GAUGE = Gauge('truck_temperature_celsius', 'Current temperature', ['truck_id'])
ANOMALY_COUNTER = Counter('vaccine_anomaly_detected_total', 'Total anomalies', ['truck_id'])
MESSAGES_CONSUMED = Counter('vaccine_messages_consumed_total', 'Messages consumed', ['truck_id'])
DB_INSERT_COUNTER = Counter('vaccine_db_inserts_total', 'Database inserts')
DB_ERROR_COUNTER = Counter('vaccine_db_errors_total', 'Database errors')
PROCESSING_TIME = Histogram('vaccine_processing_time_seconds', 'Message processing time', ['truck_id'])

# DATABASE SETUP

DB_HOST = os.getenv("DB_HOST", "postgres-service.kafka.svc.cluster.local")
DB_NAME = os.getenv("DB_NAME", "vaccine_db")
DB_USER = os.getenv("DB_USER", "vaccine_admin")
DB_PASS = os.getenv("DB_PASS", "")

def get_db_connection():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=5
        )
        print(f"✅ Connected to PostgreSQL at {DB_HOST}")
        return conn
    except Exception as e:
        print(f"⚠️  PostgreSQL connection failed: {e}")
        return None

def init_db(conn):
    """Create tables if they don't exist"""
    try:
        cur = conn.cursor()
        
        # Create sensor readings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id SERIAL PRIMARY KEY,
                truck_id VARCHAR(50),
                temperature FLOAT,
                is_anomaly BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create anomalies table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS temperature_excursions (
                id SERIAL PRIMARY KEY,
                truck_id VARCHAR(50),
                temperature FLOAT,
                reason VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️  Error initializing database: {e}")
        return False
    return True

# ML MODEL SETUP

rng = np.random.RandomState(42)
X_train = rng.uniform(-20, -15, (100, 1))
clf = IsolationForest(max_samples=100, random_state=rng)
clf.fit(X_train)

print("✅ ML model trained")

# KAFKA SETUP

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'vaccine-cluster-kafka-bootstrap.kafka.svc:9092')
TOPIC = 'vaccine-telemetry'

try:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        group_id='monitor-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        session_timeout_ms=6000,
        heartbeat_interval_ms=3000
    )
    print(f"✅ Kafka consumer connected to {KAFKA_BROKER}")
except Exception as e:
    print(f"❌ Kafka connection failed: {e}")
    sys.exit(1)

# ESTABLISH DATABASE CONNECTION

conn = get_db_connection()
if conn:
    init_db(conn)
    db_available = True
else:
    print("⚠️  Continuing without PostgreSQL (metrics still work)")
    db_available = False

print("🚀 Starting message processing...")
print(f"📊 Metrics: http://localhost:8000/metrics")
print("")

# MAIN PROCESSING LOOP

try:
    for message in consumer:
        start_time = time.time()
        
        try:
            data = message.value
            truck_id = data.get('truck_id', 'UNKNOWN')
            temp = data.get('temperature', None)
            timestamp = data.get('timestamp', time.time())
            
            if temp is None:
                continue
            
            # 1. UPDATE METRICS
            TEMP_GAUGE.labels(truck_id=truck_id).set(temp)
            MESSAGES_CONSUMED.labels(truck_id=truck_id).inc()
            
            # 2. ML ANOMALY DETECTION
            pred = clf.predict([[temp]])
            is_ml_anomaly = bool(pred[0] == -1)
            
            # 3. THRESHOLD-BASED DETECTION

            is_threshold_anomaly = (temp > -5 or temp < -25)
            is_anomaly = is_ml_anomaly or is_threshold_anomaly
            anomaly_reason = None
            
            if is_anomaly:
                ANOMALY_COUNTER.labels(truck_id=truck_id).inc()
                
                if is_ml_anomaly:
                    anomaly_reason = "ml_isolation_forest"
                elif is_threshold_anomaly:
                    anomaly_reason = "threshold_violation"
                
                print(f"🚨 ANOMALY: {truck_id} at {temp}°C ({anomaly_reason})")
            
            # 4. WRITE TO POSTGRESQL
            if conn and db_available:
                try:
                    cur = conn.cursor()
                    
                    # Insert sensor reading
                    cur.execute(
                        "INSERT INTO sensor_readings (truck_id, temperature, is_anomaly) VALUES (%s, %s, %s)",
                        (truck_id, temp, is_anomaly)
                    )
                    
                    # If anomaly, also log to excursions table
                    if is_anomaly:
                        cur.execute(
                            "INSERT INTO temperature_excursions (truck_id, temperature, reason) VALUES (%s, %s, %s)",
                            (truck_id, temp, anomaly_reason)
                        )
                    
                    conn.commit()
                    DB_INSERT_COUNTER.inc()
                    cur.close()
                    
                except Exception as e:
                    print(f"⚠️  DB Write Error: {e}")
                    DB_ERROR_COUNTER.inc()
                    try:
                        conn.rollback()
                    except:
                        pass
                    
                    # Attempt reconnect
                    try:
                        conn = get_db_connection()
                        if conn:
                            init_db(conn)
                    except:
                        conn = None
            
            # 5. RECORD PROCESSING TIME
            
            processing_time = time.time() - start_time
            PROCESSING_TIME.labels(truck_id=truck_id).observe(processing_time)
            
        except Exception as e:
            print(f"❌ Processing error: {e}")
            traceback.print_exc()

except KeyboardInterrupt:
    print("\n⏹️  Shutting down...")
except Exception as e:
    print(f"❌ Fatal error: {e}")
    traceback.print_exc()
finally:
    consumer.close()
    if conn:
        conn.close()
    print("✅ Consumer closed")