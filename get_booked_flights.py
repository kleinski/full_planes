#!/usr/bin/env python3

import os
import time
from datetime import date, timedelta

import requests

# --- KONFIGURATION ---
# Trage hier deine Amadeus API Credentials ein
# Die Credentials werden aus den Umgebungsvariablen AMADEUS_API_KEY und AMADEUS_API_SECRET geladen.
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Definiere die Flughäfen und den Suchzeitraum
# IATA Codes: FRA=Frankfurt, MUC=München, BER=Berlin, DUS=Düsseldorf etc.
ORIGIN_AIRPORTS = ['FRA', 'MUC', 'BER', 'DUS', 'HAM', 'CGN', 'STR', 'HAJ', 'LEJ', 'DRE']
# Füge hier deine Wunsch-Ziele hinzu
DESTINATION_AIRPORTS = ['LHR', 'JFK', 'BCN', 'PMI'] 
# Anzahl der Tage, die in die Zukunft gesucht werden soll
DAYS_TO_SEARCH = 7
# Schwellenwert: Flüge mit so wenigen oder weniger Plätzen werden gemeldet
SEAT_THRESHOLD = 1
# Pause zwischen den API-Anfragen in Sekunden, um das Ratenlimit (429 Too Many Requests) zu vermeiden
REQUEST_DELAY_SECONDS = 0.5 # z.B. 0.2s -> 5 Anfragen/Sekunde

# Amadeus API URLs (Testumgebung)
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def get_amadeus_token():
    """Holt einen OAuth2 Access Token von der Amadeus API."""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': API_SECRET
    }
    try:
        response = requests.post(AMADEUS_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()  # Wirft einen Fehler bei HTTP-Fehlercodes
        print("Successfully obtained Amadeus API token.")
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error getting Amadeus token: {e}")
        print(f"Response Body: {response.text}")
        return None

def find_nearly_full_flights(token, origin, destination, departure_date):
    """Sucht nach Flügen und gibt diejenigen zurück, die fast ausgebucht sind."""
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'adults': 1,
        'nonStop': 'true', # Nur Direktflüge für eine einfachere Auswertung
        'max': 10 # Wir brauchen nur ein paar Angebote, um die Verfügbarkeit zu prüfen
    }
    
    found_flights = []
    
    try:
        response = requests.get(AMADEUS_SEARCH_URL, headers=headers, params=params)
        
        # API gibt 400 zurück, wenn keine Angebote gefunden wurden, das ist kein Fehler
        if response.status_code == 400:
            return found_flights

        response.raise_for_status()
        flight_offers = response.json().get('data', [])

        for offer in flight_offers:
            # Wir nehmen das erste Segment des ersten Itinerary an (für Direktflüge)
            segment = offer['itineraries'][0]['segments'][0]
            number_of_seats = segment.get('numberOfBookableSeats', 99) # 99 als Default, falls nicht vorhanden
            
            if number_of_seats <= SEAT_THRESHOLD:
                flight_info = {
                    'date': departure_date,
                    'from': origin,
                    'to': destination,
                    'flight': f"{segment['carrierCode']} {segment['number']}",
                    'seats': number_of_seats,
                    'price': f"{offer['price']['total']} {offer['price']['currency']}"
                }
                found_flights.append(flight_info)
                
    except requests.exceptions.RequestException as e:
        print(f"API request failed for {origin}->{destination} on {departure_date}: {e}")
    
    return found_flights

def generate_html_report(flights_data):
    """Erstellt eine HTML-Datei aus den Flugdaten."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Flight Availability Report</title>
        <style>
            body { font-family: sans-serif; margin: 2em; background-color: #f4f4f9; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            thead { background-color: #007bff; color: white; }
            tbody tr:nth-child(even) { background-color: #f2f2f2; }
            tbody tr:hover { background-color: #ddd; }
        </style>
    </head>
    <body>
        <h1>Flight Availability Report</h1>
        <p>Showing flights with """ + str(SEAT_THRESHOLD) + """ or fewer available seats.</p>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Flight No.</th>
                    <th>Available Seats</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
    """
    
    if not flights_data:
        html_content += '<tr><td colspan="6" style="text-align:center;">No nearly-full flights found for the selected criteria.</td></tr>'
    else:
        for flight in flights_data:
            html_content += f"""
                <tr>
                    <td>{flight['date']}</td>
                    <td>{flight['from']}</td>
                    <td>{flight['to']}</td>
                    <td>{flight['flight']}</td>
                    <td>{flight['seats']}</td>
                    <td>{flight['price']}</td>
                </tr>
            """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("\nSuccessfully generated HTML report: report.html")


if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("!!! FEHLER: Die Umgebungsvariablen AMADEUS_API_KEY und AMADEUS_API_SECRET wurden nicht gefunden.")
        print("Bitte setze sie, bevor du das Skript ausführst, um deine Zugangsdaten zu schützen.")
        print("\nBeispiel für Linux/macOS (in deinem Terminal):")
        print("  export AMADEUS_API_KEY='dein_api_key'")
        print("  export AMADEUS_API_SECRET='dein_api_secret'")
        print("\nBeispiel für Windows (in der Eingabeaufforderung):")
        print("  set AMADEUS_API_KEY=dein_api_key")
        print("  set AMADEUS_API_SECRET=dein_api_secret")

    else:
        token = get_amadeus_token()
        if token:
            all_nearly_full_flights = []
            start_date = date.today()
            
            print("\nStarting flight search... This may take a while.")
            
            # Schleife durch alle Tage, Origins und Destinations
            for day_offset in range(DAYS_TO_SEARCH):
                current_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                for origin in ORIGIN_AIRPORTS:
                    for destination in DESTINATION_AIRPORTS:
                        print(f"Searching: {origin} -> {destination} on {current_date}")
                        flights = find_nearly_full_flights(token, origin, destination, current_date)
                        all_nearly_full_flights.extend(flights)
                        # Kurze Pause, um das API-Ratenlimit nicht zu überschreiten
                        time.sleep(REQUEST_DELAY_SECONDS)
            
            # Sortiere die Ergebnisse nach Datum
            all_nearly_full_flights.sort(key=lambda x: x['date'])
            
            generate_html_report(all_nearly_full_flights)