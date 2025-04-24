import time
import os
import platform
import pyfiglet
import shutil
import keyboard
import paramiko
import openmeteo_requests
import requests_cache
from retry_requests import retry
import sys

def get_terminal_size():
    """Ermittelt die aktuelle Terminalgröße"""
    columns, rows = shutil.get_terminal_size()
    return columns, rows

def center_text(text, width):
    """Zentriert Text innerhalb der angegebenen Breite"""
    return text.center(width)

def create_large_text(text, font='big'):
    """Erstellt ASCII-Art aus Text mit pyfiglet"""
    return pyfiglet.figlet_format(text, font=font)

def establish_ssh_connection():
    """Stellt eine SSH-Verbindung zum Remote-Gerät her"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        hostname = os.environ.get('SSH_HOST', '127.0.0.1') # Hostname oder IP-Adresse
        port = int(os.environ.get('SSH_PORT', 22)) # SSH-Port, standardmäßig 22
        username = os.environ.get('SSH_USER', 'oliver') # Benutzername auf dem Remote-Gerät
        password = os.environ.get('SSH_PASSWORD', "1m2o3r4a5w6s7k8i!") # SSH-Passwort
        key_path = os.environ.get('SSH_KEY_PATH', None) # Pfad zum SSH-Schlüssel für schlüsselbasierte Authentifizierung
        
        if password:
            client.connect(hostname, port, username, password)
        elif key_path:
            key = paramiko.RSAKey.from_private_key_file(key_path)
            client.connect(hostname, port, username, pkey=key)
        else:
            raise ValueError("Keine Authentifizierungsmethode angegeben. Setzen Sie SSH_PASSWORD oder SSH_KEY_PATH als Umgebungsvariable.")
        
        print(f"SSH-Verbindung zu {hostname} hergestellt")
        return client
    
    except Exception as e:
        print(f"Fehler beim Aufbau der SSH-Verbindung: {str(e)}")
        return None

def send_data_over_ssh(client, data):
    """Sendet Anzeigedaten über SSH zum Remote-Gerät"""
    if not client:
        return False
    
    try:
        escaped_data = data.replace('"', '\\"')
        command = f'echo "{escaped_data}" > /tmp/display.txt'
        stdin, stdout, stderr = client.exec_command(command)
        
        error = stderr.read().decode('utf-8')
        if error:
            print(f"SSH-Befehlsfehler: {error}")
            return False
        
        return True
    
    except Exception as e:
        print(f"Fehler beim Senden der Daten über SSH: {str(e)}")
        return False

def current_time():
    """Ermittelt aktuelle Uhrzeit und Datum"""
    time_now = time.strftime("%H:%M:%S")
    date_now = time.strftime("%d.%m.%Y")
    return time_now, date_now

def current_weather():
    """Ruft aktuelle Wetterdaten von der Open-Meteo API ab"""
    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 49.4759,
            "longitude": 10.9886,
            "daily": ["temperature_2m_max", "temperature_2m_min", "sunrise", "sunset"],
            "timezone": "auto",
            "forecast_days": 1
        }
        
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        daily = response.Daily()
        
        temp_min = daily.Variables(1).ValuesAsNumpy()[0]
        temp_max = daily.Variables(0).ValuesAsNumpy()[0]
        sunrise = time.strftime("%H:%M", time.localtime(daily.Variables(2).ValuesInt64AsNumpy()[0]))
        sunset = time.strftime("%H:%M", time.localtime(daily.Variables(3).ValuesInt64AsNumpy()[0]))
        
        return {
            'temp_min': temp_min,
            'temp_max': temp_max,
            'sunrise': sunrise,
            'sunset': sunset
        }
    except Exception as e:
        print(f"Fehler beim Abrufen der Wetterdaten: {str(e)}")
        return None

def clear_screen():
    """Löscht den Bildschirminhalt"""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def format_clock_weather_view(time_str, date_str, weather_data):
    """Formatiert die kombinierte Uhr- und Wetteransicht"""
    columns, rows = get_terminal_size()
    
    # Große Zeitanzeige erstellen
    large_time = create_large_text(time_str)
    large_time_lines = large_time.split('\n')
    
    # Jede Zeile zentrieren
    centered_output = []
    for line in large_time_lines:
        centered_output.append(center_text(line, columns))
    
    # Zentriertes Datum hinzufügen
    centered_output.append('\n' + center_text(date_str, columns))
    
    # Wetterinformationen hinzufügen
    if weather_data:
        temp_text = f"{weather_data['temp_min']:.1f}°C - {weather_data['temp_max']:.1f}°C"
        large_temp = create_large_text(temp_text, font='small')
        for line in large_temp.split('\n'):
            centered_output.append(center_text(line, columns))
            
        sun_info = f"Sonnenaufgang: {weather_data['sunrise']} | Sonnenuntergang: {weather_data['sunset']}"
        centered_output.append('\n' + center_text(sun_info, columns))
    else:
        centered_output.append('\n' + center_text("Wetterdaten nicht verfügbar", columns))
    
    return '\n'.join(centered_output)

def format_weather_only_view(weather_data):
    """Formatiert die reine Wetteransicht"""
    columns, rows = get_terminal_size()
    centered_output = []
    
    # Titel hinzufügen
    title = create_large_text("Wetter", font='cosmic')
    for line in title.split('\n'):
        centered_output.append(center_text(line, columns))
    
    if weather_data:
        # Temperatur anzeigen
        temp_text = f"{weather_data['temp_min']:.1f}°C - {weather_data['temp_max']:.1f}°C"
        large_temp = create_large_text(temp_text, font='standard')
        for line in large_temp.split('\n'):
            centered_output.append(center_text(line, columns))
        
        # Sonnenzeiten anzeigen
        sunrise_text = f"Sonnenaufgang: {weather_data['sunrise']}"
        sunset_text = f"Sonnenuntergang: {weather_data['sunset']}"
        
        large_sunrise = create_large_text(sunrise_text, font='small')
        large_sunset = create_large_text(sunset_text, font='small')
        
        centered_output.append('\n')
        for line in large_sunrise.split('\n'):
            centered_output.append(center_text(line, columns))
        
        centered_output.append('\n')
        for line in large_sunset.split('\n'):
            centered_output.append(center_text(line, columns))
    else:
        centered_output.append('\n' + center_text("Wetterdaten nicht verfügbar", columns))
    
    return '\n'.join(centered_output)

def format_clock_only_view(time_str, date_str):
    """Formatiert die reine Uhransicht"""
    columns, rows = get_terminal_size()
    
    # Extra große Zeitanzeige erstellen
    large_time = create_large_text(time_str, font='standard')
    large_time_lines = large_time.split('\n')
    
    # Jede Zeile zentrieren
    centered_output = []
    for line in large_time_lines:
        centered_output.append(center_text(line, columns))
    
    # Großes Datum hinzufügen
    large_date = create_large_text(date_str, font='small')
    for line in large_date.split('\n'):
        centered_output.append(center_text(line, columns))
    
    return '\n'.join(centered_output)

def main():
    """Hauptfunktion der Anwendung"""
    last_time = ""
    last_date = ""
    last_weather = None
    weather_update_interval = 300  # Wetteraktualisierung alle 5 Minuten
    last_weather_update = 0
    current_view = 0  # 0: Uhr+Wetter, 1: nur Wetter, 2: nur Uhr
    total_views = 3
    
    try:
        # SSH-Verbindung einrichten (auskommentiert, bis zur Verwendung)
        # ssh_client = establish_ssh_connection()
        ssh_client = None  # Diese Zeile entfernen, wenn SSH aktiviert wird
        
        def change_view(direction):
            nonlocal current_view
            current_view = (current_view + direction) % total_views
        
        # Tastenbelegungen einrichten
        keyboard.on_press_key("right", lambda _: change_view(1))
        keyboard.on_press_key("left", lambda _: change_view(-1))
        keyboard.on_press_key("q", lambda _: sys.exit(0))
        
        print('Starte Wetter-Uhr-Anzeige...')
        print('Benutze ← → Pfeiltasten zum Wechseln der Ansicht, Q zum Beenden')
        
        while True:
            time_now, date_now = current_time()
            
            # Wetterdaten aktualisieren
            if time.time() - last_weather_update >= weather_update_interval:
                last_weather = current_weather()
                last_weather_update = time.time()
            
            # Anzeige nur aktualisieren, wenn sich Zeit ändert
            if time_now != last_time or date_now != last_date:
                clear_screen()
                
                if current_view == 0:
                    display_text = format_clock_weather_view(time_now, date_now, last_weather)
                elif current_view == 1:
                    display_text = format_weather_only_view(last_weather)
                else:
                    display_text = format_clock_only_view(time_now, date_now)
                
                print(display_text)
                print("\nBenutze ← → Pfeiltasten zum Wechseln der Ansicht, Q zum Beenden")
                
                # Daten über SSH senden, falls verbunden
                if ssh_client:
                    send_data_over_ssh(ssh_client, display_text)
                
                last_time = time_now
                last_date = date_now
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgramm vom Benutzer beendet")
        if ssh_client:
            ssh_client.close()
    except Exception as e:
        print(f"\nFehler: {str(e)}")
        if 'ssh_client' in locals() and ssh_client:
            ssh_client.close()

if __name__ == '__main__':
    main()