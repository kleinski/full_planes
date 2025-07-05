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
ORIGIN_AIRPORTS = ['FRA','MUC', 'DUS', 'BER', 'HAJ']
# Add your desired destinations here
DESTINATION_AIRPORTS = ['VIE', 'CDG', 'MAD', 'TBS', 'SKP', 'TIA', 'BEG', 'PRN', 'RMO', 'SJJ', 'EVN', 'SOF', 'SOV', 'TGD'] 
# Number of days to search into the future
DAYS_TO_SEARCH = 5
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

            # Extract departure and arrival times from the ISO 8601 timestamp (e.g., "2024-09-01T10:00:00")
            departure_time = segment['departure']['at'].split('T')[1]
            arrival_time = segment['arrival']['at'].split('T')[1]

            # Extract and format the duration from ISO 8601 format (e.g., "PT8H30M")
            duration_iso = segment.get('duration', '')
            duration_formatted = duration_iso.replace('PT', '').replace('H', 'h ').replace('M', 'm').strip()


            flight_info = {
                'date': departure_date,
                'departure_time': departure_time,
                'arrival_time': arrival_time,
                'from': origin,
                'to': destination,
                'duration': duration_formatted,
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
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; white-space: nowrap; }
            thead { background-color: #007bff; color: white; position: sticky; top: 0; }
            thead th { cursor: pointer; user-select: none; }
            thead th:hover { background-color: #0056b3; }
            tbody tr:nth-child(even) { background-color: #f2f2f2; }
            tbody tr:hover { background-color: #ddd; }
            .th-sort-asc::after, .th-sort-desc::after { content: ''; display: inline-block; margin-left: 0.5em; border: 4px solid transparent; }
            .th-sort-asc::after { border-bottom-color: white; }
            .th-sort-desc::after { border-top-color: white; }
        </style>
    </head>
    <body>
        <h1>Flight Availability Report</h1>
        <p>All flights found for the selected criteria.</p>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Departure</th>
                    <th>Arrival</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Duration</th>
                    <th>Flight No.</th>
                    <th>Available Seats</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
    """
    
    if not flights_data:
        html_content += '<tr><td colspan="9" style="text-align:center;">No flights found for the specified criteria.</td></tr>'
    else:
        for flight in flights_data:
            html_content += f"""
                <tr>
                    <td>{flight['date']}</td>
                    <td>{flight['departure_time']}</td>
                    <td>{flight['arrival_time']}</td>
                    <td>{flight['from']}</td>
                    <td>{flight['to']}</td>
                    <td>{flight['duration']}</td>
                    <td>{flight['flight']}</td>
                    <td>{flight['seats']}</td>
                    <td>{flight['price']}</td>
                </tr>
            """

    html_content += """
            </tbody>
        </table>
        <script>
            /**
             * Sorts an HTML table.
             *
             * @param {HTMLTableElement} table The table to sort
             * @param {number} column The index of the column to sort
             * @param {boolean} asc Determines if the sorting will be in ascending
             */
            function sortTableByColumn(table, column, asc = true) {
                const dirModifier = asc ? 1 : -1;
                const tBody = table.tBodies[0];
                const rows = Array.from(tBody.querySelectorAll("tr"));

                // Sort each row
                const sortedRows = rows.sort((a, b) => {
                    const aColText = a.querySelector(`td:nth-child(${ column + 1 })`).textContent.trim();
                    const bColText = b.querySelector(`td:nth-child(${ column + 1 })`).textContent.trim();

                    // For numeric sorting (handles integers, floats, and prices like "123.45 EUR")
                    const aNum = parseFloat(aColText.replace(/[^0-9.-]+/g, ""));
                    const bNum = parseFloat(bColText.replace(/[^0-9.-]+/g, ""));

                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        return (aNum - bNum) * dirModifier;
                    }

                    // Fallback to alphabetical sort
                    return aColText.localeCompare(bColText) * dirModifier;
                });

                // Remove all existing TRs from the table
                tBody.innerHTML = "";

                // Re-add the newly sorted rows
                tBody.append(...sortedRows);

                // Remember how the column is currently sorted
                table.querySelectorAll("th").forEach(th => th.classList.remove("th-sort-asc", "th-sort-desc"));
                table.querySelector(`th:nth-child(${ column + 1})`).classList.toggle("th-sort-asc", asc);
                table.querySelector(`th:nth-child(${ column + 1})`).classList.toggle("th-sort-desc", !asc);
            }

            document.querySelectorAll("table thead th").forEach(headerCell => {
                headerCell.addEventListener("click", () => {
                    const tableElement = headerCell.closest("table");
                    const headerIndex = Array.from(headerCell.parentElement.children).indexOf(headerCell);
                    const currentIsAscending = headerCell.classList.contains("th-sort-asc");
                    sortTableByColumn(tableElement, headerIndex, !currentIsAscending);
                });
            });
        </script>
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

            # Generate the HTML report with the collected data
            if all_found_flights:
                generate_html_report(all_found_flights)
            else:
                print("\nNo flights found for the given criteria across the entire search period.")
            