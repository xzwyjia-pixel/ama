FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ruleguard_server.py ruleguard_quota.py ./
COPY ama/ ./ama/

RUN mkdir -p data/quotas

ENV PORT=7860

CMD ["uvicorn", "ruleguard_server:app", "--host", "0.0.0.0", "--port", "7860"]
