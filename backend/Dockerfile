FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PRESSURE_ROOM_DB=/app/data/pressure_room.db
WORKDIR /app

# Exported from uv.lock; CI verifies it remains synchronized.
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && useradd --create-home --uid 10001 pressure-room \
    && mkdir -p /app/data && chown pressure-room:pressure-room /app/data
COPY app ./app
USER pressure-room
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
