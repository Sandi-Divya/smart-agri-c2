from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import json
import math
from collections import defaultdict
from datetime import datetime

# ── Kafka Setup ──────────────────────────────────────────
consumer = KafkaConsumer(
    'sensor.soil_moisture',
    'sensor.soil_temp',
    'sensor.ambient_temp',
    'sensor.humidity',
    'sensor.pressure',
    'sensor.solar_radiation',
    bootstrap_servers='kafka.cropwise.garden:9094',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest',
    group_id='c2-stream-processor'
)

producer = KafkaProducer(
    bootstrap_servers='kafka.cropwise.garden:9094',
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# ── InfluxDB Setup ───────────────────────────────────────
influx_client = InfluxDBClient(
    url="https://influxdb.cropwise.garden",
    token="my-super-secret-auth-token",
    org="smart_agri"
)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)
BUCKET = "sensor_data"

# ── Rolling Window ───────────────────────────────────────
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
print("📊 Connected to kafka.cropwise.garden:9094")
print("💾 Connected to InfluxDB at influxdb.cropwise.garden")
print("🔍 Z-score anomaly detection running...")

for message in consumer:
    data = message.value
    parameter = data.get('parameter')
    value = data.get('value')
    device_id = data.get('device_id', 'unknown')
    field_id = data.get('field_id', 'field1')

    # Rolling window
    readings[parameter].append(value)
    if len(readings[parameter]) > 100:
        readings[parameter].pop(0)

    values = readings[parameter]
    mean = sum(values) / len(values)
    zscore = compute_zscore(value, values)

    # Delta value
    delta = value - values[-2] if len(values) > 1 else 0.0

    enriched = {
        **data,
        'zscore': round(zscore, 4),
        'rolling_mean': round(mean, 4),
        'delta_value': round(delta, 4),
        'rolling_count': len(values),
        'processed_at': datetime.utcnow().isoformat() + 'Z'
    }

    # Write to InfluxDB
    try:
        point = Point("sensor_data") \
            .tag("device_id", device_id) \
            .tag("field_id", field_id) \
            .tag("parameter", parameter) \
            .field("value", float(value)) \
            .field("zscore", float(zscore)) \
            .field("rolling_mean", float(mean)) \
            .field("delta_value", float(delta))
        write_api.write(bucket=BUCKET, record=point)
    except Exception as e:
        print(f"⚠️ InfluxDB write error: {e}")

    # Anomaly detection
    if zscore > 3:
        enriched['anomaly_type'] = 'statistical_outlier'
        enriched['is_anomaly'] = True
        producer.send('sensor.anomaly_candidates', enriched)
        print(f"🚨 ANOMALY! {parameter}={value} Z={zscore:.2f}")
    else:
        enriched['is_anomaly'] = False
        print(f"✅ Normal: {parameter}={value} Z={zscore:.2f}")

    producer.flush()