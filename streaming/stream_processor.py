from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType
)
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ── Spark Session ─────────────────────────────────────
spark = SparkSession.builder \
    .appName("SmartAgri-C2-StreamProcessor") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("✅ Spark Session started!")

# ── Schema ────────────────────────────────────────────
sensor_schema = StructType([
    StructField("device_id",  StringType(), True),
    StructField("field_id",   StringType(), True),
    StructField("timestamp",  StringType(), True),
    StructField("parameter",  StringType(), True),
    StructField("value",      FloatType(),  True),
    StructField("unit",       StringType(), True),
])

# ── Read from Kafka ───────────────────────────────────
topics = "sensor.soil_moisture,sensor.soil_temp,sensor.ambient_temp,sensor.humidity,sensor.pressure,sensor.solar_radiation"

raw_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", topics) \
    .option("startingOffsets", "latest") \
    .load()

print("📊 Reading from 6 Kafka topics...")

# ── Parse JSON ────────────────────────────────────────
parsed_df = raw_df.select(
    col("topic"),
    from_json(
        col("value").cast("string"),
        sensor_schema
    ).alias("data"),
    col("timestamp").alias("kafka_time")
).select("topic", "data.*", "kafka_time")

# ── InfluxDB Config ───────────────────────────────────
INFLUX_URL    = "https://influxdb.cropwise.garden"
INFLUX_TOKEN  = "my-super-secret-auth-token"
INFLUX_ORG    = "smart_agri"
INFLUX_BUCKET = "sensor_data"

# ── Rolling Window Store ──────────────────────────────
readings_store = {}

# ── Process Each Batch ────────────────────────────────
def write_batch(batch_df, batch_id):
    rows = batch_df.collect()
    if not rows:
        return

    client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    for row in rows:
        parameter = row.parameter
        value = float(row.value) if row.value else 0.0

        # Rolling window of 100 readings
        if parameter not in readings_store:
            readings_store[parameter] = []
        readings_store[parameter].append(value)
        if len(readings_store[parameter]) > 100:
            readings_store[parameter].pop(0)

        vals = readings_store[parameter]
        mean_val = sum(vals) / len(vals)
        variance = sum((x - mean_val)**2 for x in vals) / len(vals)
        std_val = variance ** 0.5
        zscore = abs((value - mean_val) / std_val) \
            if std_val > 0 else 0.0
        delta = value - vals[-2] if len(vals) > 1 else 0.0

        # Write to InfluxDB
        point = Point("sensor_data") \
            .tag("device_id",  row.device_id or "unknown") \
            .tag("field_id",   row.field_id  or "field1") \
            .tag("parameter",  parameter) \
            .field("value",        float(value)) \
            .field("zscore",       round(zscore, 4)) \
            .field("rolling_mean", round(mean_val, 4)) \
            .field("delta_value",  round(delta, 4))

        write_api.write(bucket=INFLUX_BUCKET, record=point)

        if zscore > 3:
            print(f"🚨 ANOMALY! {parameter}={value} Z={zscore:.2f}")
            # Send to anomaly_candidates
            from kafka import KafkaProducer
            import json
            producer = KafkaProducer(
                bootstrap_servers='kafka:9092',
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            producer.send('sensor.anomaly_candidates', {
                **row.asDict(),
                'zscore': round(zscore, 4),
                'anomaly_type': 'statistical_outlier',
                'is_anomaly': True
            })
            producer.flush()
        else:
            print(f"✅ Normal: {parameter}={value} Z={zscore:.2f}")

    client.close()

# ── Start Streaming ───────────────────────────────────
print("🔍 Z-score anomaly detection running...")
print("💾 Writing to InfluxDB...")

query = parsed_df \
    .writeStream \
    .foreachBatch(write_batch) \
    .trigger(processingTime="30 seconds") \
    .option("checkpointLocation", "/tmp/checkpoint-c2") \
    .start()

query.awaitTermination()