FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app.py db.py ./
RUN useradd --system --no-create-home appuser
USER appuser
EXPOSE 5000
CMD ["gunicorn","-b","0.0.0.0:5000","-w","1","app:app"]
