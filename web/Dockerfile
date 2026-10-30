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

CMD ["sh", "-c", "python init_db.py && gunicorn -w 3 -b 0.0.0.0:8000 --access-logfile - wsgi:app"]
