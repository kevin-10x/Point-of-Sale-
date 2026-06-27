FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-docker.txt

COPY . .

ENV FLASK_APP=run.py
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
