# Sito Django per l'hosting (Render, Railway, Fly...). Costruire dalla cartella apps/web: docker build -t lanostracitta apps/web
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN DJANGO_SECRET_KEY=solo-per-collectstatic python manage.py collectstatic --noinput
EXPOSE 8000
# All'avvio si applicano le migrazioni di Django (tabelle di sessioni e admin; lo schema del dominio è in db/migrations).
# Un solo processo con più thread: limiti di frequenza e blocchi usano la cache in memoria del processo.
# Il disco persistente va montato su DATA_DIR (foto, video, archivio temporaneo della verifica)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --threads ${WEB_THREADS:-4} --timeout 60 --access-logfile -"]
