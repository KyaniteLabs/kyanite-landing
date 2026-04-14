FROM python:3.13-alpine

WORKDIR /app
RUN pip install --no-cache-dir flask gunicorn psycopg2-binary requests pyyaml

COPY app.py .
COPY templates/ ./templates/
COPY products/ ./products/
EXPOSE 3002

CMD ["gunicorn", "--bind", "0.0.0.0:3002", "--workers", "2", "--timeout", "120", "app:app"]
