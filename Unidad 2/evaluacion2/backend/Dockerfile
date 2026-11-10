# Una sola imagen base para los 7 servicios; cada uno elige su carpeta con SVC_DIR.
FROM python:3.12-slim
ARG SVC_DIR
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/common
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common /app/common
COPY ${SVC_DIR} /app/svc
RUN useradd --no-create-home --uid 10001 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)"
CMD ["uvicorn", "main:app", "--app-dir", "/app/svc", "--host", "0.0.0.0", "--port", "8000"]
