FROM python:3.9-slim
WORKDIR /app
COPY main.py .
RUN pip install kafka-python prometheus_client
CMD ["python", "main.py"]