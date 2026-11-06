# Malhamix — Django + DRF backend va PWA frontend bitta konteynerda
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN sed -i "s/\r$//" docker/entrypoint.sh && chmod +x docker/entrypoint.sh \
    && DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
