import time
import json
import random
import os
import sys
from kafka import KafkaProducer
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# PROMETHEUS METRICS

start_http_server(8000)

TEMP_GAUGE = Gauge('truck_temperature_celsius', 'Current temperature', ['truck_id'])
HUMIDITY_GAUGE = Gauge('truck_humidity_percent', 'Current humidity', ['truck_id'])
ANOMALY_COUNTER = Counter('vaccine_anomaly_detected_total', 'Anomalies', ['truck_id'])
MESSAGES_PRODUCED = Counter('vaccine_messages_produced_total', 'Messages sent', ['truck_id'])
PRODUCTION_TIME = Histogram('vaccine_production_time_seconds', 'Time to produce message', ['truck_id'])

# CONFIGURATION (supports scaling)

NUM_TRUCKS = int(os.getenv('NUM_TRUCKS', '50'))  # Scale to 50+ easily
ANOMALY_RATE = float(os.getenv('ANOMALY_RATE', '0.1'))  # 10% chance

# Generate truck IDs based on count
truck_ids = [f"TRUCK-{i:03d}" for i in range(1, NUM_TRUCKS + 1)]

print(f"✅ Configured for {NUM_TRUCKS} trucks")
print(f"📍 Trucks: {', '.join(truck_ids[:5])}{'...' if len(truck_ids) > 5 else ''}")

# KAFKA SETUP

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'vaccine-cluster-kafka-bootstrap.kafka.svc:9092')
TOPIC = 'vaccine-telemetry'

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        retries=3
    )
    print(f"✅ Kafka producer connected to {KAFKA_BROKER}")
except Exception as e:
    print(f"❌ Kafka connection failed: {e}")
    sys.exit(1)

print(f"🚀 Starting producer for {NUM_TRUCKS} trucks...")
print(f"📊 Metrics: http://localhost:8000/metrics")
print(f"⚠️  Anomaly rate: {ANOMALY_RATE*100}%")
print("")

# SIMULATION STATE (per truck)

truck_state = {
    truck_id: {
        'last_temp': random.uniform(-20, -15),
        'last_humidity': random.uniform(35, 55),
        'anomaly_streak': 0
    }
    for truck_id in truck_ids
}

# MAIN PRODUCTION LOOP

try:
    iteration = 0
    while True:
        iteration += 1
        
        for truck in truck_ids:
            start_time = time.time()
            
            # Get or initialize truck state
            state = truck_state[truck]
            
            # SIMULATE REALISTIC TEMPERATURE CHANGES
            
            # Normal drift toward -17°C
            drift = (-17 - state['last_temp']) * 0.01
            noise = random.gauss(0, 0.1)
            temp = state['last_temp'] + drift + noise
            
            # INJECT ANOMALIES
            
            is_anomaly = False
            if random.random() < ANOMALY_RATE:
                # Cooling failure - temp rises
                temp = random.uniform(-5, 0)
                state['anomaly_streak'] += 1
                is_anomaly = True
                ANOMALY_COUNTER.labels(truck_id=truck).inc()
                
                if state['anomaly_streak'] == 1:
                    print(f"⚠️  ANOMALY START: {truck} at {temp:.2f}°C")
            else:
                if state['anomaly_streak'] > 0:
                    print(f"✅ ANOMALY RESOLVED: {truck} (duration: {state['anomaly_streak']} messages)")
                state['anomaly_streak'] = 0
            
            # Keep temp in reasonable range
            temp = max(-25, min(5, temp))
            state['last_temp'] = temp
            
            # SIMULATE HUMIDITY
            
            humidity_drift = (45 - state['last_humidity']) * 0.01
            humidity = state['last_humidity'] + humidity_drift + random.gauss(0, 0.5)
            humidity = max(20, min(80, humidity))
            state['last_humidity'] = humidity
            
            # CREATE MESSAGE
            
            payload = {
                "truck_id": truck,
                "timestamp": time.time(),
                "temperature": round(temp, 2),
                "humidity": round(humidity, 1),
                "gps_lat": 40.7128 + random.uniform(-0.1, 0.1),
                "gps_lon": -74.0060 + random.uniform(-0.1, 0.1),
                "is_anomaly": is_anomaly
            }
            
            # SEND TO KAFKA
            
            try:
                producer.send(TOPIC, payload)
                
                # Update metrics
                TEMP_GAUGE.labels(truck_id=truck).set(temp)
                HUMIDITY_GAUGE.labels(truck_id=truck).set(humidity)
                MESSAGES_PRODUCED.labels(truck_id=truck).inc()
                
                production_time = time.time() - start_time
                PRODUCTION_TIME.labels(truck_id=truck).observe(production_time)
                
            except Exception as e:
                print(f"❌ Kafka send error: {e}")
        
        # Log progress every 50 iterations
        if iteration % 50 == 0:
            total_messages = sum(
                MESSAGES_PRODUCED.labels(truck_id=truck)._value.get() or 0
                for truck in truck_ids
            )
            print(f"📊 Iteration {iteration}: {total_messages} total messages produced")
        
        # Send batch every 2 seconds
        time.sleep(2)

except KeyboardInterrupt:
    print("\n⏹️  Shutting down...")
except Exception as e:
    print(f"❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
finally:
    producer.flush()
    producer.close()
    print("✅ Producer closed")