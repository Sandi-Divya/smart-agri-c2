from kafka import KafkaConsumer, KafkaProducer
import json
import math
from collections import defaultdict
from datetime import datetime

# Kafka setup
consumer = KafkaConsumer(
    'sensor.soil_moisture',
    'sensor.soil_temp', 
    'sensor.ambient_temp',
    'sensor.humidity',
    'sensor.pressure',
    'sensor.solar_radiation',
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest',
    group_id='spark-processor'
)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Rolling window for Z-score (last 100 readings per parameter)
readings = defaultdict(list)

def compute_zscore(value, values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return abs((value - mean) / std)

print("✅ Stream processor started!")
print("📊 Reading from 6 sensor topics...")
print("🔍 Z-score anomaly detection running...")

for message in consumer:
    data = message.value
    parameter = data.get('parameter')
    value = data.get('value')

    # Keep rolling window of 100 readings
    readings[parameter].append(value)
    if len(readings[parameter]) > 100:
        readings[parameter].pop(0)

    # Compute Z-score
    zscore = compute_zscore(value, readings[parameter])

    # Add derived fields
    values = readings[parameter]
    mean = sum(values) / len(values)

    enriched = {
        **data,
        'zscore': round(zscore, 4),
        'rolling_mean': round(mean, 4),
        'rolling_count': len(values),
        'processed_at': datetime.utcnow().isoformat() + 'Z'
    }

    if zscore > 3:
        enriched['anomaly_type'] = 'statistical_outlier'
        enriched['is_anomaly'] = True
        producer.send('sensor.anomaly_candidates', enriched)
        print(f"🚨 ANOMALY detected! {parameter}={value} Z={zscore:.2f}")
    else:
        enriched['is_anomaly'] = False
        print(f"✅ Normal: {parameter}={value} Z={zscore:.2f}")

    producer.flush()