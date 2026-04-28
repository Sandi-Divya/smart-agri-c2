# MQTT Configuration

## C1 Broker Details
- Broker: broker.hivemq.com
- Port: 1883
- Base Topic: zone1/sensors/

## Topic Mapping
| C1 Topic | Kafka Topic |
|---|---|
| zone1/sensors/temperature | sensor.ambient_temp |
| zone1/sensors/humidity | sensor.humidity |
| zone1/sensors/pressure | sensor.pressure |
| zone1/sensors/soil_moisture | sensor.soil_moisture |