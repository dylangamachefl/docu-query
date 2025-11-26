# Stage 1: Build the application
FROM python:3.10-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stage 2: Final image
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
