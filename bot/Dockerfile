FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir aiogram==3.13.1 httpx==0.27.2

COPY bot ./bot

ENV PYTHONPATH=/app

CMD ["python", "-m", "bot.main"]

