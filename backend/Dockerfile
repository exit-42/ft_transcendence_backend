FROM python:3.11.4-slim

WORKDIR /app/backend

COPY requirements.txt .
COPY entrypoint.sh .
COPY manage.py .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["/app/backend/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
