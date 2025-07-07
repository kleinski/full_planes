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

import concurrent.futures
import csv
import io
import json
import os
import time
from datetime import date, datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from flask import (Flask, Response, redirect, render_template, request,
                   session, url_for)

load_dotenv()

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__)

# --- CONFIGURATION ---
# Credentials are loaded from environment variables.
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    print("!!! WARNING: FLASK_SECRET_KEY is not set. Sessions are not secure.")
    app.secret_key = 'dev-secret-key-for-testing-only' # Fallback for development

# --- Custom Exceptions ---
class AmadeusApiError(Exception):
    """Custom exception for Amadeus API related errors."""
    pass

# Daily limit for flight search API calls to control costs
DAILY_API_CALL_LIMIT = 1000 
QUOTA_FILE = 'api_quota.json'
quota_lock = Lock()

# Global cache for the Amadeus token
amadeus_token_cache: Dict[str, Any] = {
    'token': None,
    'expires_at': 0
}

# Amadeus API URLs (Test environment)
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

# List of German departure airports for the dropdown menu
GERMAN_AIRPORTS: List[Dict[str, str]] = [
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
DESTINATION_AIRPORTS: List[Dict[str, str]] = [
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
AIRLINE_CODES: Dict[str, str] = {
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

# --- QUOTA MANAGEMENT ---

def check_and_consume_quota(calls_to_make: int) -> bool:
    """
    Checks if the requested number of API calls is within the daily limit.
    If so, it consumes the quota and returns True. Otherwise, returns False.
    This function is thread-safe.
    """
    with quota_lock:
        today_str = date.today().strftime('%Y-%m-%d')
        usage = {'date': today_str, 'count': 0}

        try:
            with open(QUOTA_FILE, 'r') as f:
                usage = json.load(f)
            # Reset count if it's a new day
            if usage.get('date') != today_str:
                print("New day, resetting API call quota.")
                usage = {'date': today_str, 'count': 0}
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is corrupt, create a new one.
            print("Quota file not found or corrupt, creating a new one.")
            pass # usage is already initialized for today

        if usage['count'] + calls_to_make > DAILY_API_CALL_LIMIT:
            print(f"Daily API call limit reached. Current count: {usage['count']}, tried to add: {calls_to_make}")
            return False
        
        # Consume the quota
        usage['count'] += calls_to_make
        
        try:
            with open(QUOTA_FILE, 'w') as f:
                json.dump(usage, f)
            print(f"Consumed {calls_to_make} API calls. New daily count: {usage['count']}")
            return True
        except IOError as e:
            print(f"Error writing to quota file: {e}")
            # If we can't write, we shouldn't proceed.
            return False

def get_remaining_quota() -> int:
    """
    Checks the quota file and returns the number of remaining API calls for the day.
    This function is read-only and does not consume the quota.
    """
    with quota_lock:
        today_str = date.today().strftime('%Y-%m-%d')
        try:
            with open(QUOTA_FILE, 'r') as f:
                usage = json.load(f)
            # If the stored date is not today, the quota is fully available.
            if usage.get('date') != today_str:
                return DAILY_API_CALL_LIMIT
            
            remaining = DAILY_API_CALL_LIMIT - usage.get('count', 0)
            return max(0, remaining) # Ensure it doesn't go below zero
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is corrupt, the full quota is available.
            return DAILY_API_CALL_LIMIT

# --- API-FUNKTIONEN ---

def get_amadeus_token() -> Optional[str]:
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
        print(f"Fatal error getting Amadeus token: {e}")
        raise AmadeusApiError(f"Fehler bei der Authentifizierung mit der Amadeus API. Bitte überprüfen Sie die Server-Logs. Details: {e}")

def find_flights(token: str, origin: str, destination: str, departure_date: str, all_airports: List[Dict[str, str]], airline_codes: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Searches for flights, enriches the data with full names, and returns the found offers.
    """
    # Create a lookup dictionary for full airport names for enrichment
    airports_map = {airport['iata']: f"{airport['city']} – {airport['name']}" for airport in all_airports if 'city' in airport}

    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'adults': 1,
        'nonStop': 'true',
    }

    # Retry logic with exponential backoff for handling rate limits (429 errors)
    for attempt in range(3):
        try:
            response = requests.get(AMADEUS_SEARCH_URL, headers=headers, params=params)

            # If we are being rate-limited, wait and try again.
            if response.status_code == 429:
                if attempt == 2: # Last attempt failed
                    print(f"Giving up on {origin}->{destination} for {departure_date} after 3 failed attempts due to rate limiting.")
                    raise AmadeusApiError("Das API-Ratenlimit wurde auch nach mehreren Versuchen überschritten. Die Suche wurde abgebrochen.")
                wait_time = 1 * (2 ** attempt) # Exponential backoff: 1s, 2s, 4s
                print(f"Rate limit hit for {origin}->{destination} on {departure_date}. Retrying in {wait_time}s... (Attempt {attempt + 1}/3)")
                time.sleep(wait_time)
                continue

            # API returns 400 if no offers are found, this is not an error
            if response.status_code == 400:
                return []

            # For other errors, raise an exception to be caught below.
            response.raise_for_status()

            # If successful, process the data and return
            found_flights = []
            flight_offers = response.json().get('data', [])
            for offer in flight_offers:
                segment = offer['itineraries'][0]['segments'][0]
                carrier_code = segment['carrierCode']
                flight_info = {
                    'date': departure_date,
                    'departure_time': segment['departure']['at'].split('T')[1],
                    'arrival_time': segment['arrival']['at'].split('T')[1],
                    'from': origin, 'to': destination,
                    'from_full': airports_map.get(origin, origin), 'to_full': airports_map.get(destination, destination),
                    'duration': segment.get('duration', '').replace('PT', '').replace('H', 'h ').replace('M', 'm').strip(),
                    'flight': f"{carrier_code} {segment['number']}",
                    'airline_name': airline_codes.get(carrier_code, f"Unbekannte Airline ({carrier_code})"),
                    'seats': segment.get('numberOfBookableSeats', 99),
                    'price': f"{offer['price']['total']} {offer['price']['currency']}"
                }
                found_flights.append(flight_info)
            return found_flights

        except requests.exceptions.RequestException as e:
            # For connection errors, etc., log the error and stop retrying for this request.
            print(f"Fatal API request failed for {origin}->{destination} on {departure_date}: {e}")
            raise AmadeusApiError(f"Die Amadeus API ist aufgrund eines Verbindungsfehlers nicht erreichbar. Details: {e}")

    raise AmadeusApiError(f"Unbekannter Fehler bei der Flugsuche für {origin}->{destination} am {departure_date}.")

# --- FLASK ROUTEN ---

@app.route('/')
def index() -> Any:
    """Displays the home page with the search form."""
    error = request.args.get('error')
    remaining_quota = get_remaining_quota()

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
        search=search_params,
        remaining_quota=remaining_quota)

@app.route('/search', methods=['POST'])
def search() -> Any:
    """Processes the form data, searches for flights, and displays the results."""
    origin_val = request.form.get('origin')
    destination_val = request.form.get('destination')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    max_seats_str = request.form.get('max_seats')

    if not all([origin_val, destination_val, start_date_str, end_date_str]):
        return redirect(url_for('index', error="Bitte alle Felder ausfüllen."))

    # Now we know the values are not None, we can safely process them.
    origin = origin_val.upper().strip()
    destination = destination_val.upper().strip()

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect(url_for('index', error="Invalid date format."))

    if end_date < start_date:
        return redirect(url_for('index', error="The end date cannot be before the start date."))

    delta = end_date - start_date
    if delta.days > 6:
        return redirect(url_for('index', error="The date range cannot exceed 7 days."))

    # --- QUOTA CHECK ---
    # Check if the number of required searches exceeds the daily API call limit.
    num_searches = delta.days + 1
    if not check_and_consume_quota(num_searches):
        return redirect(url_for('index', error=f"Das tägliche API-Limit von {DAILY_API_CALL_LIMIT} Aufrufen wurde erreicht. Bitte versuchen Sie es morgen erneut."))
    # --- END QUOTA CHECK ---

    try:
        token = get_amadeus_token()
        if not token:
            # This case should now be handled by the exception in get_amadeus_token, but as a fallback:
            raise AmadeusApiError("Konnte keinen API-Token erhalten. Überprüfen Sie Ihre Credentials und die Server-Logs.")

        all_airports = GERMAN_AIRPORTS + DESTINATION_AIRPORTS
        
        # Use a ThreadPoolExecutor to run API requests in parallel
        all_found_flights = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_date = {
                executor.submit(find_flights, token, origin, destination, (start_date + timedelta(days=i)).strftime("%Y-%m-%d"), all_airports, AIRLINE_CODES): (start_date + timedelta(days=i))
                for i in range(delta.days + 1)
            }

            for future in concurrent.futures.as_completed(future_to_date):
                try:
                    all_found_flights.extend(future.result())
                except Exception as exc:
                    print(f'A search task generated an exception: {exc}')
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise exc # Re-raise to be caught by the outer try-except

    except AmadeusApiError as e:
        return render_template('error.html', error_message=str(e), is_debug=app.debug)
    except Exception as e:
        print(f"An unexpected error occurred during search: {e}")
        return render_template('error.html', error_message="Ein unerwarteter interner Fehler ist aufgetreten.", is_debug=app.debug)
    
    # Filter flights based on the optional seat limit
    max_seats = None
    if max_seats_str and max_seats_str.isdigit():
        max_seats = int(max_seats_str)
        all_found_flights = [flight for flight in all_found_flights if flight['seats'] < max_seats]
    
    # Get full names for the results page header
    # The map is created here again, which is a small, acceptable redundancy for cleaner code.
    airports_map = {airport['iata']: f"{airport['city']} – {airport['name']}" for airport in all_airports if 'city' in airport}
    origin_full = airports_map.get(origin, origin)
    destination_full = airports_map.get(destination, destination)
    all_found_flights.sort(key=lambda x: (x['date'], x['departure_time']))

    # Store results in session for CSV export
    session['search_results'] = all_found_flights

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
def impressum() -> Any:
    """Displays the legal notice page."""
    return render_template('impressum.html')

@app.route('/warum')
def warum() -> Any:
    """Displays the 'Why?' page."""
    return render_template('warum.html')

@app.route('/export/csv')
def export_csv() -> Response:
    """Exports the flight search results stored in the session to a CSV file."""
    flights = session.get('search_results', [])

    if not flights:
        # Redirect to home if there are no results to export
        return redirect(url_for('index'))

    # Use io.StringIO to build the CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    header = [
        'Datum', 'Abflug', 'Ankunft', 'Von', 'Nach', 'Dauer', 
        'Fluggesellschaft', 'Flugnr.', 'Freie Plaetze'
    ]
    writer.writerow(header)

    # Write data rows
    for flight in flights:
        writer.writerow([
            flight.get('date'),
            flight.get('departure_time'),
            flight.get('arrival_time'),
            flight.get('from_full'),
            flight.get('to_full'),
            flight.get('duration'),
            flight.get('airline_name'),
            flight.get('flight'),
            flight.get('seats')
        ])

    # Create a Flask Response object
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=flug-report.csv"}
    )

# --- START APPLICATION ---
if __name__ == '__main__':
    if not API_KEY or not API_SECRET:
        print("!!! ERROR: Please set the environment variables AMADEUS_API_KEY and AMADEUS_API_SECRET.")
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
