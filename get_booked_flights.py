#!/usr/bin/env python3

import os
import time
from datetime import date, timedelta

import requests

# --- CONFIGURATION ---
# Enter your Amadeus API Credentials here
# The credentials are loaded from the environment variables AMADEUS_API_KEY and AMADEUS_API_SECRET.
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Define the airports and the search period
# IATA Codes: FRA=Frankfurt, MUC=Munich, BER=Berlin, DUS=Düsseldorf etc.
ORIGIN_AIRPORTS = ['FRA']
# Add your desired destinations here
DESTINATION_AIRPORTS = ['JFK'] 
# Number of days to search into the future
DAYS_TO_SEARCH = 100
# Pause between API requests in seconds to avoid rate limiting (429 Too Many Requests)
REQUEST_DELAY_SECONDS = 1.0 # e.g., 0.2s -> 5 requests/second

# Amadeus API URLs (Test environment)
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def get_amadeus_token():
    """Fetches an OAuth2 Access Token from the Amadeus API."""
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': API_SECRET
    }
    try:
        response = requests.post(AMADEUS_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()  # Raises an error for HTTP error codes
        print("Successfully obtained Amadeus API token.")
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error getting Amadeus token: {e}")
        print(f"Response Body: {response.text}")
        return None

def find_flights(token, origin, destination, departure_date):
    """Searches for flights and returns the found offers."""
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'adults': 1,
        'nonStop': 'true', # Only non-stop flights for simpler analysis
        # 'max': 10 # We only need a few offers to check availability
    }
    
    found_flights = []
    
    try:
        response = requests.get(AMADEUS_SEARCH_URL, headers=headers, params=params)
        
        # API returns 400 if no offers are found, this is not an error
        if response.status_code == 400:
            return found_flights

        response.raise_for_status()
        flight_offers = response.json().get('data', [])

        for offer in flight_offers:
            # We assume the first segment of the first itinerary (for non-stop flights)
            segment = offer['itineraries'][0]['segments'][0]
            number_of_seats = segment.get('numberOfBookableSeats', 99) # 99 as a default if not present

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
    """Creates an HTML file from the flight data."""
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
        <p>All flights found for the selected criteria.</p>
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
        html_content += '<tr><td colspan="6" style="text-align:center;">No flights found for the specified criteria.</td></tr>'
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
        print("!!! ERROR: The environment variables AMADEUS_API_KEY and AMADEUS_API_SECRET were not found.")
        print("Please set them before running the script to protect your credentials.")


    else:
        token = get_amadeus_token()
        if token:
            all_found_flights = []
            start_date = date.today()
            
            print("\nStarting flight search... This may take a while.")
            
            # Loop through all days, origins, and destinations
            for day_offset in range(DAYS_TO_SEARCH):
                current_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                for origin in ORIGIN_AIRPORTS:
                    for destination in DESTINATION_AIRPORTS:
                        print(f"Searching: {origin} -> {destination} on {current_date}")
                        flights = find_flights(token, origin, destination, current_date)
                        all_found_flights.extend(flights)
                        # Short pause to avoid exceeding the API rate limit
                        time.sleep(REQUEST_DELAY_SECONDS)
            
            # Sort the results by date
            all_found_flights.sort(key=lambda x: x['date'])
            