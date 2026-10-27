# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
WORKDIR /app

# Install dependencies in a separate layer for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app.py db.py ./

FROM base AS final
EXPOSE 5000
CMD ["python", "app.py"]
