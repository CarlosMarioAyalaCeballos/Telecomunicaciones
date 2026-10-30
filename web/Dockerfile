FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_FOLDER=/app/uploads

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/uploads

EXPOSE 8000

# PORT lo asigna Render (local: 8000). WEB_CONCURRENCY limita la memoria en planes pequeños.
CMD ["sh", "-c", "python init_db.py && exec gunicorn -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - wsgi:app"]
