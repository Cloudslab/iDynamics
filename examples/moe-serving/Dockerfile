FROM python:3.11-slim

WORKDIR /app
COPY moe_service/server.py /app/server.py

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "/app/server.py"]
