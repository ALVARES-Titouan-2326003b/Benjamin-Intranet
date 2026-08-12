FROM python:3.13.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libpq5 \
        tesseract-ocr \
        tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

RUN addgroup --system django \
    && adduser --system --ingroup django --home /app django \
    && mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R django:django /app

COPY --chown=django:django . .

USER django

EXPOSE 8000

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "config.wsgi:application"]
