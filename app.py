#!/usr/bin/env python3
'''
Full Planes - Flight Search Web App 

This web application allows users to search for direct flights from German airports to various destinations in the Schengen and non-Schengen areas using the Amadeus Flight Offers API.

Copyright (C) 2025 Marcus Klein
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
'''

import os
import time
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

load_dotenv()

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__)

# --- CONFIGURATION ---
# Credentials are loaded from environment variables.
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Pause between API requests in seconds to avoid rate limiting
REQUEST_DELAY_SECONDS = 1.0 

# Global cache for the Amadeus token
amadeus_token_cache = {
    'token': None,
    'expires_at': 0
}

# Amadeus API URLs (Test environment)
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

# List of German departure airports for the dropdown menu
GERMAN_AIRPORTS = [
    {'city': 'Berlin', 'name': 'Flughafen Berlin Brandenburg "Willy Brandt"', 'iata': 'BER'},
    {'city': 'Bremen', 'name': 'Bremen Airport Hans Koschnick', 'iata': 'BRE'},
    {'city': 'Dortmund', 'name': 'Dortmund Airport 21', 'iata': 'DTM'},
    {'city': 'Dresden', 'name': 'Flughafen Dresden International', 'iata': 'DRS'},
    {'city': 'Düsseldorf', 'name': 'Düsseldorf Airport', 'iata': 'DUS'},
    {'city': 'Erfurt', 'name': 'Flughafen Erfurt-Weimar', 'iata': 'ERF'},
    {'city': 'Frankfurt', 'name': 'Flughafen Frankfurt am Main', 'iata': 'FRA'},
    {'city': 'Frankfurt', 'name': 'Flughafen Frankfurt-Hahn', 'iata': 'HHN'},
    {'city': 'Friedrichshafen', 'name': 'Bodensee-Airport Friedrichshafen', 'iata': 'FDH'},
    {'city': 'Hamburg', 'name': 'Hamburg Airport Helmut Schmidt', 'iata': 'HAM'},
    {'city': 'Hannover', 'name': 'Hannover Airport', 'iata': 'HAJ'},
    {'city': 'Karlsruhe', 'name': 'Flughafen Karlsruhe/Baden-Baden', 'iata': 'FKB'},
    {'city': 'Köln/Bonn', 'name': 'Köln Bonn Airport "Konrad Adenauer"', 'iata': 'CGN'},
    {'city': 'Leipzig/Halle', 'name': 'Flughafen Leipzig/Halle', 'iata': 'LEJ'},
    {'city': 'Memmingen', 'name': 'Memmingen Airport', 'iata': 'FMM'},
    {'city': 'München', 'name': 'Flughafen München "Franz Josef Strauß"', 'iata': 'MUC'},
    {'city': 'Münster/Osnabrück', 'name': 'Flughafen Münster/Osnabrück', 'iata': 'FMO'},
    {'city': 'Nürnberg', 'name': 'Albrecht Dürer Airport Nürnberg', 'iata': 'NUE'},
    {'city': 'Paderborn/Lippstadt', 'name': 'Flughafen Paderborn/Lippstadt', 'iata': 'PAD'},
    {'city': 'Rostock', 'name': 'Flughafen Rostock-Laage', 'iata': 'RLG'},
    {'city': 'Saarbrücken', 'name': 'Flughafen Saarbrücken', 'iata': 'SCN'},
    {'city': 'Stuttgart', 'name': 'Flughafen Stuttgart', 'iata': 'STR'},
    {'city': 'Weeze', 'name': 'Airport Weeze', 'iata': 'NRN'}
]

# List of selectable destination airports
DESTINATION_AIRPORTS = [
    # Separator for visual grouping in the dropdown
    {'iata': '---', 'name': 'Schengen-Raum'},
    {'city': 'Wien', 'name': 'Flughafen Wien-Schwechat', 'iata': 'VIE'},
    {'city': 'Paris', 'name': 'Flughafen Paris-Charles-de-Gaulle', 'iata': 'CDG'},
    {'city': 'Madrid', 'name': 'Flughafen Adolfo Suárez Madrid-Barajas', 'iata': 'MAD'},
    {'iata': '---', 'name': 'Nicht-Schengen-Raum'},
    {'city': 'Tiflis', 'name': 'Internationaler Flughafen Tiflis', 'iata': 'TBS'},
    {'city': 'Skopje', 'name': 'Internationaler Flughafen Skopje', 'iata': 'SKP'},
    {'city': 'Tirana', 'name': 'Flughafen Tirana Nënë Tereza', 'iata': 'TIA'},
    {'city': 'Belgrad', 'name': 'Flughafen Belgrad Nikola Tesla', 'iata': 'BEG'},
    {'city': 'Pristina', 'name': 'Flughafen Pristina', 'iata': 'PRN'},
    {'city': 'Bălți', 'name': 'Internationaler Flughafen Bălți-Leadoveni', 'iata': 'RMO'},
    {'city': 'Sarajevo', 'name': 'Flughafen Sarajevo', 'iata': 'SJJ'},
    {'city': 'Jerewan', 'name': 'Internationaler Flughafen Swartnoz', 'iata': 'EVN'},
    {'city': 'Sofia', 'name': 'Flughafen Sofia', 'iata': 'SOF'},
    {'city': 'Moskau', 'name': 'Sheremetyevo International Airport ', 'iata': 'SVO'},
    {'city': 'Podgorica', 'name': 'Flughafen Podgorica', 'iata': 'TGD'}
]

# Mapping for common airline IATA codes to names
AIRLINE_CODES = {
    'LH': 'Lufthansa',
    'EW': 'Eurowings',
    'DE': 'Condor',
    'FR': 'Ryanair',
    'U2': 'EasyJet',
    'A3': 'Aegean Airlines',
    'AF': 'Air France',
    'OS': 'Austrian Airlines',
    'IB': 'Iberia',
    'KL': 'KLM Royal Dutch Airlines',
    'LX': 'Swiss International Air Lines',
    'SN': 'Brussels Airlines',
    'TP': 'TAP Air Portugal',
    'TK': 'Turkish Airlines',
    'W6': 'Wizz Air',
    'JU': 'Air Serbia',
    'A9': 'Georgian Airways',
    'SU': 'Aeroflot' # For SVO
}

# --- API-FUNKTIONEN ---

def get_amadeus_token():
    """
    Fetches an OAuth2 Access Token from the Amadeus API, using a simple cache
    to avoid requesting a new token on every search.
    """
    # Check if a valid token exists in the cache (with a 60-second buffer for safety)
    if amadeus_token_cache.get('token') and time.time() < amadeus_token_cache.get('expires_at', 0) - 60:
        print("Using cached Amadeus API token.")
        return amadeus_token_cache['token']

    # If no valid token, get a new one
    print("No valid token in cache, requesting a new one.")
    if not API_KEY or not API_SECRET:
        print("!!! ERROR: Environment variables AMADEUS_API_KEY and AMADEUS_API_SECRET not found.")
        return None
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials', 'client_id': API_KEY, 'client_secret': API_SECRET}

    try:
        response = requests.post(AMADEUS_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Cache the new token and its expiration time
        access_token = token_data['access_token']
        # Amadeus tokens usually last 1799 seconds (just under 30 mins)
        expires_in = token_data.get('expires_in', 1799)
        amadeus_token_cache['token'] = access_token
        amadeus_token_cache['expires_at'] = time.time() + expires_in
        
        print(f"Successfully obtained and cached a new Amadeus API token, expires in {expires_in} seconds.")
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Error getting Amadeus token: {e}")
        return None

def find_flights(token, origin, destination, departure_date):
    """Searches for flights and returns the found offers."""
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'adults': 1,
        'nonStop': 'true',
    }
    found_flights = []
    try:
        response = requests.get(AMADEUS_SEARCH_URL, headers=headers, params=params)
        if response.status_code == 400: # API returns 400 if no offers are found
            return found_flights
        response.raise_for_status()
        flight_offers = response.json().get('data', [])

        for offer in flight_offers:
            segment = offer['itineraries'][0]['segments'][0]
            flight_info = {
                'date': departure_date,
                'departure_time': segment['departure']['at'].split('T')[1],
                'arrival_time': segment['arrival']['at'].split('T')[1],
                'from': origin,
                'to': destination,
                'duration': segment.get('duration', '').replace('PT', '').replace('H', 'h ').replace('M', 'm').strip(),
                'flight': f"{segment['carrierCode']} {segment['number']}",
                'seats': segment.get('numberOfBookableSeats', 99),
                'price': f"{offer['price']['total']} {offer['price']['currency']}"
            }
            found_flights.append(flight_info)
    except requests.exceptions.RequestException as e:
        print(f"API request failed for {origin}->{destination} on {departure_date}: {e}")
    return found_flights

# --- FLASK ROUTEN ---

@app.route('/')
def index():
    """Displays the home page with the search form."""
    error = request.args.get('error')

    today_str = date.today().strftime('%Y-%m-%d')

    # Read search parameters from the URL to pre-fill the form
    # Default to today's date if not provided
    search_params = {
        'origin': request.args.get('origin', ''),
        'destination': request.args.get('destination', ''),
        'start_date': request.args.get('start_date', today_str),
        'end_date': request.args.get('end_date', today_str),
        'max_seats': request.args.get('max_seats', '')
    }

    return render_template(
        'index.html', 
        error=error, 
        airports=GERMAN_AIRPORTS, 
        destination_airports=DESTINATION_AIRPORTS, 
        search=search_params)

@app.route('/search', methods=['POST'])
def search():
    """Processes the form data, searches for flights, and displays the results."""
    origin = request.form.get('origin').upper().strip() # type: ignore
    destination = request.form.get('destination').upper().strip() # type: ignore
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    max_seats_str = request.form.get('max_seats')

    if not all([origin, destination, start_date_str, end_date_str]):
        return redirect(url_for('index', error="Bitte alle Felder ausfüllen."))
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() # type: ignore
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() # type: ignore
    except ValueError:
        return redirect(url_for('index', error="Invalid date format."))

    if end_date < start_date:
        return redirect(url_for('index', error="The end date cannot be before the start date."))

    delta = end_date - start_date
    if delta.days > 6:
        return redirect(url_for('index', error="The date range cannot exceed 7 days."))

    token = get_amadeus_token()
    if not token:
        return redirect(url_for('index', error="Could not get API token. Check your credentials and server logs."))

    all_found_flights = []
    for day_offset in range(delta.days + 1):
        current_date = start_date + timedelta(days=day_offset)
        current_date_str = current_date.strftime("%Y-%m-%d")
        
        print(f"Searching: {origin} -> {destination} on {current_date_str}")
        flights = find_flights(token, origin, destination, current_date_str)
        all_found_flights.extend(flights)
        time.sleep(REQUEST_DELAY_SECONDS)
    
    # Filter flights based on the optional seat limit
    max_seats = None
    if max_seats_str and max_seats_str.isdigit():
        max_seats = int(max_seats_str)
        all_found_flights = [flight for flight in all_found_flights if flight['seats'] < max_seats]
    
    # Create a lookup dictionary for full airport names
    airports_map = {airport['iata']: f"{airport['city']} – {airport['name']}" for airport in GERMAN_AIRPORTS + DESTINATION_AIRPORTS if 'city' in airport}

    # Enrich flight data with full airport and airline names
    for flight in all_found_flights:
        flight['from_full'] = airports_map.get(flight['from'], flight['from'])
        flight['to_full'] = airports_map.get(flight['to'], flight['to'])
        carrier_code = flight['flight'].split(' ')[0]
        flight['airline_name'] = AIRLINE_CODES.get(carrier_code, f"Unbekannte Airline ({carrier_code})")

    # Get full names for the results page header
    origin_full = airports_map.get(origin, origin)
    destination_full = airports_map.get(destination, destination)
    all_found_flights.sort(key=lambda x: (x['date'], x['departure_time']))

    return render_template(
        'results.html', 
        flights=all_found_flights,
        origin=origin, # Keep IATA for the "new search" link
        destination=destination, # Keep IATA for the "new search" link
        origin_full=origin_full,
        destination_full=destination_full,
        start_date=start_date_str,
        end_date=end_date_str,
        max_seats=max_seats_str
    )

@app.route('/impressum')
def impressum():
    """Displays the legal notice page."""
    return render_template('impressum.html')

# --- START APPLICATION ---
if __name__ == '__main__':
    if not API_KEY or not API_SECRET:
        print("!!! ERROR: Please set the environment variables AMADEUS_API_KEY and AMADEUS_API_SECRET.")
    else:
        app.run(debug=True, host='0.0.0.0', port=7000)
