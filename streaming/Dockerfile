FROM python:3.9-slim

WORKDIR /app

COPY stream_processor.py .

RUN pip install kafka-python

CMD ["python", "/app/stream_processor.py"]