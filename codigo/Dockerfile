# Fin Pro na VPS (EasyPanel). Python 3.12: o OCR tem wheel estável.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LEITOR_HOST=0.0.0.0 \
    LEITOR_PORT=8000 \
    LEITOR_ABRIR_NAVEGADOR=0 \
    LEITOR_DADOS_DIR=/app/dados \
    TZ=America/Cuiaba

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

COPY requirements.vps.txt /tmp/requirements.vps.txt
RUN pip install --no-cache-dir -r /tmp/requirements.vps.txt

COPY app ./app
COPY web ./web
COPY ferramentas ./ferramentas

RUN mkdir -p /app/dados

EXPOSE 8000

CMD ["python", "-m", "app", "--navegador"]
