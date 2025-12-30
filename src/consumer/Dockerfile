FROM python:3.9-slim
WORKDIR /app
COPY main.py .
RUN pip install kafka-python scikit-learn prometheus-client numpy psycopg2-binary
CMD ["python", "main.py"]

