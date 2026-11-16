# Una sola imagen base para todas las piezas; cada una elige carpeta, módulo y puerto.
# Contexto de build: la carpeta evaluacion2 (ver deploy/docker-compose.yml).
FROM python:3.12-slim
ARG SVC_DIR
ARG SVC_MODULE
ARG SVC_PORT
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/common SVC_MODULE=${SVC_MODULE} SVC_PORT=${SVC_PORT}
WORKDIR /app
COPY apigateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apigateway/common /app/common
COPY ${SVC_DIR} /app/svc
RUN useradd --no-create-home --uid 10001 app
USER app
EXPOSE ${SVC_PORT}
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ['SVC_PORT']+'/health',timeout=2).status==200 else 1)"
CMD ["sh", "-c", "exec uvicorn ${SVC_MODULE}:app --app-dir /app/svc --host 0.0.0.0 --port ${SVC_PORT}"]
