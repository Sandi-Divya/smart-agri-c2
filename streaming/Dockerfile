FROM apache/spark:3.5.0

USER root

WORKDIR /app

RUN pip install influxdb-client kafka-python

COPY stream_processor.py .

CMD ["/opt/spark/bin/spark-submit", \
     "--master", "local[*]", \
     "--packages", \
     "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", \
     "/app/stream_processor.py"]