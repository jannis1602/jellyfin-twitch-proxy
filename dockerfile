# Basis-Image: Python 3.9
FROM python:3.9-slim

# Arbeitsverzeichnis im Container erstellen
WORKDIR /app

# Streamlink installieren
# RUN apt-get update && \
#     apt-get install -y curl && \
    # apt install streamlink -y
    #curl -sSL https://github.com/streamlink/streamlink/releases/download/7.1.3/streamlink-7.1.3.tar.gz | tar -xz -C /usr/local/bin

# Kopiere dein Python-Skript und andere n  tige Dateien in den Container
# COPY . /app/

# Optional: Wenn du eine requirements.txt hast, installiere alle Python-Abh  ngigkeiten
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY /app/twitch_streamlink_proxy.py /app/
COPY /app/jellyfin_twitch_api.py /app/
COPY /app/templates /app/templates/
COPY /app/static /app/static/

# RUN ls -la /app

# Python-Skript automatisch beim Start des Containers ausf  hren
CMD ["python", "/app/twitch_streamlink_proxy.py"]