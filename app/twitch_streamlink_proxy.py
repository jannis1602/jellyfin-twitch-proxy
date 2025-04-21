from flask import Flask, redirect, request, send_file, url_for, render_template
import subprocess
import threading
import time
from jellyfin_twitch_api import TwitchAPI
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlparse
import requests
from io import StringIO
from dotenv import load_dotenv 
import pytz


# Globaler Puffer für die Konsolenausgabe
console_output = StringIO()

# Standardausgabe umleiten
# sys.stdout = console_output
# sys.stderr = console_output

app = Flask(__name__)

# Speichert gestartete Prozesse, um doppelte Starts zu vermeiden
running_streams = {}

load_dotenv()

#TODO add webui port env
BASE_STREAMLINK_PORT = os.getenv("BASE_STREAMLINK_PORT", "8888")
JELLYFIN_URL = os.getenv("JELLYFIN_URL")  # Fallback-Wert
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

print("BASE_STREAMLINK_PORT:", os.getenv("BASE_STREAMLINK_PORT"))

# TwitchAPI-Instanz erstellen
twitch_api = TwitchAPI()

STREAMERS_FILE = "streamers.txt"  # Datei mit der Liste der Streamer

# Überprüfen, ob die Datei existiert, und sie erstellen, falls nicht
if not os.path.exists(STREAMERS_FILE):
    with open(STREAMERS_FILE, "w") as f:
        pass  # Leere Datei erstellen

XMLTV_FILE = "twitch.xmltv"  # Ausgabe-XMLTV-Datei

# Funktion zum Starten von streamlink als HTTP-Proxy
def start_streamlink_proxy(streamer_name, port):
    try:
        process = subprocess.Popen([
            "streamlink",
            "--twitch-disable-ads",
            "--player-external-http",
            "--player-external-http-port", str(port),
            f"https://twitch.tv/{streamer_name}",
            "best"
        ])
        print(f"Streamlink gestartet für {streamer_name} auf Port {port}, PID: {process.pid}")
        time.sleep(4)  # Kurz warten, bis der Proxy verfügbar ist
    except Exception as e:
        print(f"Fehler beim Start von Streamlink für {streamer_name}: {e}")

@app.route("/proxy/<streamer>")
def stream_proxy(streamer):
    print(f"Anfrage für Streamer: {streamer}")

    # Wenn der Update-Stream angefragt wird, Jellyfin-Scan auslösen und Anfrage abweisen
    if streamer == "timestream":
        print("Update-Stream angefragt. Jellyfin-Scan wird ausgelöst.")
        trigger_jellyfin_scan()
        return "Update-Stream nicht verfügbar. Jellyfin-Scan wurde ausgelöst.", 403

    if (streamer not in running_streams):
        port = BASE_STREAMLINK_PORT + len(running_streams)  # Dynamischer Port
        print(f"Starte neuen Proxy auf Port: {port}")
        t = threading.Thread(target=start_streamlink_proxy, args=(streamer, port))
        t.daemon = True
        t.start()
        running_streams[streamer] = port
    else:
        port = running_streams[streamer]
        print(f"Verwende bestehenden Proxy auf Port: {port}")

    # Dynamische URL basierend auf der Anfrage
    parsed_url = urlparse(request.host_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.hostname}"
    print(f"REDIRECT: {base_url}:{port}/")
    return redirect(f"{base_url}:{port}/", code=302)

def get_stream_title(streamer):
    try:
        title = twitch_api.get_stream_title(streamer)
        if title:
            print(f"Der Titel des Livestreams von {streamer} ist: {title}")
            return title
        else:
            print(f"{streamer} ist derzeit offline.")
            return f"offline"
    except Exception as e:
        print(f"Fehler: {e}")
    return f"Live-Stream von {streamer}"  # Fallback-Titel

def generate_xmltv():
    """Erstellt eine XMLTV-Datei basierend auf den gespeicherten Streamern."""
    if not os.path.exists(STREAMERS_FILE):
        return

    # Root-Element
    tv = ET.Element("tv")
    tv.set("source-info-name", "Twitch")
    tv.set("source-info-url", "https://www.twitch.tv")
    tv.set("generator-info-name", "Twitch XMLTV Generator")

    # Streamer-Kanäle hinzufügen
    with open(STREAMERS_FILE, "r") as f:
        streamers = [line.strip() for line in f.readlines()]

    for streamer in streamers:
        # Kanal-Element
        channel = ET.SubElement(tv, "channel", id=streamer.lower())
        ET.SubElement(channel, "display-name").text = streamer
        ET.SubElement(channel, "url").text = f"https://www.twitch.tv/{streamer}"

        # Programminformationen
        now = datetime.utcnow()
        title = get_stream_title(streamer)  # Titel des Streams abrufen
        start_time = twitch_api.get_stream_start_time(streamer)  # Startzeit des Streams abrufen
        print(f"Startzeit: {start_time}")
        # Fallback-Startzeit, falls der Stream offline ist
        if not start_time:
            start_time = now

        program = ET.SubElement(tv, "programme", start=start_time.strftime("%Y%m%d%H%M%S") + " +0000",
                                 stop=(now + timedelta(hours=2)).strftime("%Y%m%d%H%M%S") + " +0000",
                                 channel=streamer)
        ET.SubElement(program, "title").text = title
        ET.SubElement(program, "desc").text = f"Dies ist der Live-Stream von {streamer} auf Twitch."

    # XML-Datei speichern
    tree = ET.ElementTree(tv)
    with open(XMLTV_FILE, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

@app.route("/xmltv")
def get_xmltv():
    # Schritt 1: Datei löschen + kurz warten
    if os.path.exists(XMLTV_FILE):
        os.remove(XMLTV_FILE)
        time.sleep(1)  # wichtig!

    # Schritt 2: Neue Datei schreiben
    generate_xmltv()
    if os.path.exists(XMLTV_FILE):
        # Timestamp generieren
        timestamp = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y%m%d%H%M%S")
        return send_file(XMLTV_FILE, as_attachment=True, download_name=f"twitch_{timestamp}.xml", mimetype="application/xml")
    return "<tv></tv>", 200, {'Content-Type': 'application/xml'}

# @app.route("/")
# def home():
#     return "Twitch Streamlink Proxy läuft", 200

@app.route("/m3u")  # TODO add stream with last time update
def generate_m3u():
    base_url = request.host_url.rstrip('/')
    lines = ["#EXTM3U"]
    id = 1
    with open(STREAMERS_FILE, "r") as f:
        streamers = [line.strip() for line in f.readlines()]
    for name in streamers:
        # Profilbild-URL abrufen
        profile_image_url = twitch_api.get_user_profile_image(name)
        # Ausnahme 
        if name.lower() == "sparkofphoenixtv":
            profile_image_url = "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcRaOqBSvY4P9dTVdexIZBrXx4zTMX1XYWWL2xgvUaep2eMWDwpW"
        if profile_image_url:
            tvg_logo = f'tvg-logo="{profile_image_url}"'
        else:
            tvg_logo = ""  # Fallback, falls kein Profilbild gefunden wird

        # Stream-Status überprüfen
        try:
            stream_title = twitch_api.get_stream_title(name)    
        except Exception as e:
            print(f"Fehler beim Abrufen des Streamtitels für {name}: {e}")
            stream_title = None
        if stream_title != None:
            status_symbol = "🟢"  # Online-Symbol
        else:
            status_symbol = "🟥"  # Offline-Symbol

        # M3U-Eintrag erstellen
        lines.append(f'#EXTINF:-1 tvg-id="{name.lower()}" tvg-name="{id:02d} {name}" {tvg_logo} group-title="Twitch",{status_symbol} {name}')
        lines.append(f'{base_url}/proxy/{name}')
        id += 1

    # Dummy-Stream mit aktueller Zeit hinzufügen
    current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M")
    lines.append(f'#EXTINF:-1 tvg-id="time" tvg-name="Time Stream" group-title="Twitch",Update {current_time}')
    lines.append(f'{base_url}/proxy/timestream')

    return "\n".join(lines), 200, {'Content-Type': 'audio/x-mpegurl'}

@app.route("/download-m3u")
def download_m3u():
    # Generiere die M3U-Datei
    m3u_content, status, headers = generate_m3u()
    
    # Speichere die Datei temporär
    m3u_file_path = "twitch_streams.m3u"
    with open(m3u_file_path, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    # Biete die Datei als Download an
    return send_file(m3u_file_path, as_attachment=True, download_name="twitch_streams.m3u", mimetype="audio/x-mpegurl")

def trigger_jellyfin_scan():

    print(f"Streamer ist jetzt live")
    # POST-Anfrage an Jellyfin senden
    url = f"{JELLYFIN_URL}/ScheduledTasks/Running/bea9b218c97bbf98c5dc1303bdb9a0ca"
    headers = {
        'Content-Type': 'application/json',
        'X-Emby-Token': JELLYFIN_API_KEY,
    }
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print(f"Jellyfin TV Guide erfolgreich aktualisiert.")
        else:
            print(f"Fehler beim Aktualisieren des Jellyfin TV Guide: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Fehler beim Senden der POST-Anfrage: {e}")

@app.route("/trigger-jellyfin-scan", methods=["POST"])
def trigger_jellyfin_scan_route():
    trigger_jellyfin_scan()
    return redirect(url_for("index"))

def monitor_streamers():
    """
    Überwacht den Online-Status der Streamer und triggert einen Jellyfin-Scan bei Änderungen.
    """
    # Aktueller und vorheriger Status der Streamer
    previous_status = {}

    while True:
        print("Überprüfe den Online-Status der Streamer...")
        with open(STREAMERS_FILE, "r") as f:
            streamers = [line.strip() for line in f.readlines()]

        try:
            # Online-Status der Streamer abfragen
            current_status = twitch_api.get_online_status(streamers)
        except Exception as e:
            print(f"Fehler beim Abrufen des Online-Status: {e}")
            current_status = previous_status  # Behalte den alten Status bei Fehler

        # Änderungen im Status erkennen
        for streamer, is_online in current_status.items():
            if streamer not in previous_status or previous_status[streamer] != is_online:
                status = "online" if is_online else "offline"
                print(f"Statusänderung erkannt: {streamer} ist jetzt {status}")

                # Jellyfin-Scan auslösen
                trigger_jellyfin_scan()

        # Status aktualisieren
        previous_status = current_status

        # Wartezeit zwischen den Überprüfungen (z. B. 60 Sekunden)
        time.sleep(300)

def remove_streamers(streamers_to_remove):
    with open(STREAMERS_FILE, "r") as f:
        streamers = [line.strip() for line in f.readlines()]
    streamers = [streamer for streamer in streamers if streamer not in streamers_to_remove]
    with open(STREAMERS_FILE, "w") as f:
        f.write("\n".join(streamers) + "\n")

@app.route("/")
def index():
    # Dynamisch die aktuelle Domain oder IP-Adresse abrufen
    base_url = request.host_url.rstrip('/')  # z. B. "http://127.0.0.1:5000"
    m3u_url = f"{base_url}/m3u"
    xmltv_url = f"{base_url}/xmltv"
    
    # URLs an das Template übergeben
    if os.path.exists(STREAMERS_FILE):
        with open(STREAMERS_FILE, "r") as f:
            streamers = [line.strip() for line in f.readlines()]
    else:
        streamers = []
    return render_template("index.html", streamers=streamers, m3u_url=m3u_url, xmltv_url=xmltv_url)

@app.route("/add", methods=["POST"])
def add_streamer():
    streamer = request.form.get("streamer").strip()
    if streamer:
        with open(STREAMERS_FILE, "a") as f:
            f.write(streamer + "\n")
        generate_m3u()
    return redirect(url_for("index"))


@app.route("/remove", methods=["POST"])
def remove_selected_streamers():
    selected_streamers = request.form.getlist("selected_streamer")
    if selected_streamers:
        remove_streamers(selected_streamers)
        generate_m3u()
    return redirect(url_for("index"))

@app.route("/logs")
def view_logs():
    # Konsolenausgabe aus dem Puffer lesen
    console_output.seek(0)
    logs = console_output.read()
    return render_template("logs.html", logs=logs)

if __name__ == "__main__":
    threading.Thread(target=monitor_streamers, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
