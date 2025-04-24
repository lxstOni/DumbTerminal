import serial
import time
import openmeteo_requests
import requests_cache
from retry_requests import retry
import os
import platform
import pyfiglet
import shutil
import keyboard

def get_terminal_size():
    columns, rows = shutil.get_terminal_size()
    return columns, rows

def center_text(text, width):
    return text.center(width)

def create_large_text(text, font='big'):
    return pyfiglet.figlet_format(text, font=font)

def serial_connection():
    ser = serial.Serial('/dev/ttyAMA0', baudrate=9600)
    return ser

def current_time():
    time_now = time.strftime("%H:%M:%S")
    date_now = time.strftime("%d.%m.%Y")
    return time_now, date_now

def current_weather():
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
        return None

def clear_screen():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def format_clock_weather_view(time_str, date_str, weather_data):
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
    
    # Wetterinformationen mit größerem Text hinzufügen
    if weather_data:
        temp_text = f"{weather_data['temp_min']:.1f}°C - {weather_data['temp_max']:.1f}°C"
        large_temp = create_large_text(temp_text, font='small')
        for line in large_temp.split('\n'):
            centered_output.append(center_text(line, columns))
            
        sun_info = f"Sunrise: {weather_data['sunrise']} | Sunset: {weather_data['sunset']}"
        centered_output.append('\n' + center_text(sun_info, columns))
    else:
        centered_output.append('\n' + center_text("Weather data unavailable", columns))
    
    return '\n'.join(centered_output)

def format_weather_only_view(weather_data):
    columns, rows = get_terminal_size()
    centered_output = []
    
    # Titel hinzufügen
    title = create_large_text("Weather", font='cosmic')
    for line in title.split('\n'):
        centered_output.append(center_text(line, columns))
    
    if weather_data:
        # Temperatur
        temp_text = f"{weather_data['temp_min']:.1f}°C - {weather_data['temp_max']:.1f}°C"
        large_temp = create_large_text(temp_text, font='standard')
        for line in large_temp.split('\n'):
            centered_output.append(center_text(line, columns))
        # Sonnenzeit
        sunrise_text = f"Sunrise: {weather_data['sunrise']}"
        sunset_text = f"Sunset: {weather_data['sunset']}"
        
        large_sunrise = create_large_text(sunrise_text, font='small')
        large_sunset = create_large_text(sunset_text, font='small')
        
        centered_output.append('\n')
        for line in large_sunrise.split('\n'):
            centered_output.append(center_text(line, columns))
        
        centered_output.append('\n')
        for line in large_sunset.split('\n'):
            centered_output.append(center_text(line, columns))
    else:
        centered_output.append('\n' + center_text("Weather data unavailable", columns))
    
    return '\n'.join(centered_output)

def format_clock_only_view(time_str, date_str):
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
    last_time = ""
    last_date = ""
    last_weather = None
    weather_update_interval = 300  # Wetteraktualisierung alle 5 Minuten
    last_weather_update = 0
    current_view = 0  # 0: clock+weather, 1: weather only, 2: clock only
    total_views = 3
    
    try:
        #ser = serial_connection()
        
        def change_view(direction):
            nonlocal current_view
            current_view = (current_view + direction) % total_views
        
        keyboard.on_press_key("right", lambda _: change_view(1))
        keyboard.on_press_key("left", lambda _: change_view(-1))
        
        while True:
            current_time_value, current_date_str = current_time()
            
            # Wetteraktualisierung alle 5 Minuten
            if time.time() - last_weather_update >= weather_update_interval:
                last_weather = current_weather()
                last_weather_update = time.time()
            
            if current_time_value != last_time or current_date_str != last_date:
                clear_screen()
                
                if current_view == 0:
                    display_text = format_clock_weather_view(current_time_value, current_date_str, last_weather)
                elif current_view == 1:
                    display_text = format_weather_only_view(last_weather)
                else:
                    display_text = format_clock_only_view(current_time_value, current_date_str)
                
                print(display_text)
                print("\nUse ← → arrow keys to change views")
                #ser.write(display_text.encode())
                
                last_time = current_time_value
                last_date = current_date_str
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        #ser.close()
    except Exception as e:
        print(f"\nError: {str(e)}")
        if 'ser' in locals():
            #ser.close()
            pass

if __name__ == '__main__':
    main()