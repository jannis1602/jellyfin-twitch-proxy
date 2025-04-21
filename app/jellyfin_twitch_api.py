import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

class TwitchAPI:
    def __init__(self):
        self.base_url = "https://api.twitch.tv/helix"
        self.access_token = self.get_oauth_token()
        self.headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {self.access_token}"
        }
        print("CLIENT_ID:", os.getenv("CLIENT_ID"))

    def get_oauth_token(self):
        """
        Ruft ein OAuth-Token von der Twitch-API ab.
        """
        url = 'https://id.twitch.tv/oauth2/token'
        params = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception(f"Fehler beim Abrufen des OAuth-Tokens: {response.status_code} - {response.text}")

    def get_stream_title(self, username):
        """
        Ruft den Titel eines Twitch-Livestreams ab.
        
        :param username: Der Benutzername des Twitch-Kanals.
        :return: Der Titel des Livestreams oder None, wenn der Kanal offline ist.
        """
        url = f"{self.base_url}/streams"
        params = {"user_login": username}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                return data["data"][0]["title"]  # Titel des Livestreams
            else:
                return None  # Kanal ist offline
        elif response.status_code == 401:  # Unauthorized (Token abgelaufen)
            self.access_token = self.get_oauth_token()  # Token erneuern
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            return self.get_stream_title(username)  # Erneut versuchen
        else:
            raise Exception(f"Fehler bei der Twitch-API-Anfrage: {response.status_code} - {response.text}")

    def get_stream_start_time(self, username):
        """
        Ruft die Startzeit eines Twitch-Livestreams ab.
        
        :param username: Der Benutzername des Twitch-Kanals.
        :return: Die Startzeit des Livestreams als datetime-Objekt oder None, wenn der Kanal offline ist.
        """
        url = f"{self.base_url}/streams"
        params = {"user_login": username}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                started_at = data["data"][0]["started_at"]  # Startzeit des Livestreams
                return datetime.fromisoformat(started_at.replace("Z", "+00:00"))  # ISO 8601 in datetime umwandeln
            else:
                return None  # Kanal ist offline
        elif response.status_code == 401:  # Unauthorized (Token abgelaufen)
            self.access_token = self.get_oauth_token()  # Token erneuern
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            return self.get_stream_start_time(username)  # Erneut versuchen
        else:
            raise Exception(f"Fehler bei der Twitch-API-Anfrage: {response.status_code} - {response.text}")

    def get_user_profile_image(self, username):
        """
        Ruft das Profilbild eines Twitch-Benutzers ab.

        :param username: Der Benutzername des Twitch-Kanals.
        :return: Die URL des Profilbilds oder None, wenn der Benutzer nicht gefunden wurde.
        """
        url = f"{self.base_url}/users"
        params = {"login": username}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                return data["data"][0]["profile_image_url"]  # URL des Profilbilds
            else:
                return None  # Benutzer nicht gefunden
        elif response.status_code == 401:  # Unauthorized (Token abgelaufen)
            self.access_token = self.get_oauth_token()  # Token erneuern
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            return self.get_user_profile_image(username)  # Erneut versuchen
        else:
            raise Exception(f"Fehler bei der Twitch-API-Anfrage: {response.status_code} - {response.text}")

    def get_online_status(self, usernames):
        """
        Überprüft den Online-Status mehrerer Twitch-Benutzer.

        :param usernames: Eine Liste von Twitch-Benutzernamen.
        :return: Ein Dictionary mit Benutzernamen als Schlüssel und True (online) oder False (offline) als Wert.
        """
        url = f"{self.base_url}/streams"
        online_status = {}

        # Twitch-API erlaubt maximal 100 Benutzer pro Anfrage
        for i in range(0, len(usernames), 100):
            batch = usernames[i:i + 100]  # Teile die Liste in Batches von 100
            params = {"user_login": batch}
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                data = response.json()
                # Erstelle ein Dictionary für die Benutzer, die online sind
                online_users = {stream["user_login"]: True for stream in data["data"]}
                # Füge alle Benutzer aus dem Batch hinzu (online oder offline)
                for user in batch:
                    online_status[user] = online_users.get(user, False)
            elif response.status_code == 401:  # Unauthorized (Token abgelaufen)
                self.access_token = self.get_oauth_token()  # Token erneuern
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                return self.get_online_status(usernames)  # Erneut versuchen
            else:
                raise Exception(f"Fehler bei der Twitch-API-Anfrage: {response.status_code} - {response.text}")

        return online_status

    def example_usage(self):
        """
        Beispiel zur Verwendung der get_stream_title- und get_stream_start_time-Methoden.
        """
        username = "papaplatte"
        try:
            title = self.get_stream_title(username)
            if title:
                print(f"Der Titel des Livestreams von {username} ist: {title}")
            else:
                print(f"{username} ist derzeit offline.")
            
            print(f"{self.get_user_profile_image(username)}")

            start_time = self.get_stream_start_time(username)
            if start_time:
                print(f"Der Livestream von {username} hat begonnen am: {start_time}")
            else:
                print(f"{username} ist derzeit offline.")
        except Exception as e:
            print(f"Fehler: {e}")


# Beispiel direkt ausführen, wenn die Datei ausgeführt wird
if __name__ == "__main__":
    twitch_api = TwitchAPI()
    twitch_api.example_usage()