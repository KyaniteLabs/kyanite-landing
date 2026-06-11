FROM python:3.14-alpine

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ ./templates/
COPY products/ ./products/
COPY static/ ./static/
EXPOSE 3002

CMD ["gunicorn", "--bind", "0.0.0.0:3002", "--workers", "2", "--timeout", "120", "app:app"]
