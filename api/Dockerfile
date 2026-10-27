FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app.py db.py ./
EXPOSE 5000
CMD ["sh", "-c", "exec gunicorn --workers 1 --bind 0.0.0.0:${API_PORT:-5000} app:app"]
