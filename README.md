# Jellyfin Twitch Streamlink Proxy

Dieses Projekt bietet eine Flask-basierte Anwendung, die Twitch-Streams als HTTP-Proxies bereitstellt und M3U- sowie XMLTV-Dateien generiert. Es ermöglicht die Integration von Twitch-Streams in Medienserver wie Jellyfin.

## Features

- **Twitch-Stream-Proxy**: Startet Streamlink-Prozesse, um Twitch-Streams als HTTP-Proxies bereitzustellen.
- **M3U-Generierung**: Erstellt dynamische M3U-Playlisten für Twitch-Streams.
- **XMLTV-Generierung**: Generiert XMLTV-Dateien mit Programminformationen für Twitch-Streams.
- **Streamer-Verwaltung**: Hinzufügen und Entfernen von Streamern über eine Weboberfläche.
- **Jellyfin-Integration**: Automatische Aktualisierung des Jellyfin TV Guides bei Änderungen im Streamer-Status.
- **Logs**: Anzeige der Konsolenausgabe über die Weboberfläche.

## Voraussetzungen

- **Python 3.9 oder höher**
- Abhängigkeiten aus der Datei `requirements.txt`:
  - `streamlink`
  - `dotenv`
  - `flask`
  - `requests`
  - `pytz`


## Docker Compose
```yaml
services:
  jellyfin:
    image: jellyfin-twitch:latest
    container_name: jellyfin-twitch
    # volumes:
    #   - /docker/jellyfin-twitch/:/app
    ports:
      - 5096:5000
      - 8888:8888
      - 8889:8889
      - 8890:8890
      - 8891:8891
      - 8892:8892
    environment:
      BASE_STREAMLINK_PORT: 8888
      JELLYFIN_URL: ""
      JELLYFIN_API_KEY: ""
      CLIENT_ID: ""
      CLIENT_SECRET: ""
    restart: unless-stopped
```