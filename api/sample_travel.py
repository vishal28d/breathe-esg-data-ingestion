"""
Sample travel data simulating a Navan API /v1/bookings response.

Design rationale:
- Flights use real IATA codes (LHR, DEL, JFK, SIN, FRA) so distance calc is testable.
- One flight has an unknown destination (XYZ) to trigger the 'unknown IATA' warning path.
- Mix of cabin classes (economy, business, premium_economy) to test emission factor lookup.
- Hotel entries have varying country codes.
- Ground transport entry with known distance.
- Dates are in ISO format as Navan returns them; some edge cases included.
"""

SAMPLE_TRAVEL_DATA = [
    # --- Flights ---
    {
        "type": "flight",
        "trip_id": "TRIP-2024-001",
        "traveler_name": "Priya Sharma",
        "origin_iata": "DEL",
        "destination_iata": "LHR",
        "cabin_class": "economy",
        "departure_date": "2024-01-08",
        "arrival_date": "2024-01-09",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-001",
        "traveler_name": "Priya Sharma",
        "origin_iata": "LHR",
        "destination_iata": "DEL",
        "cabin_class": "economy",
        "departure_date": "2024-01-15",
        "arrival_date": "2024-01-16",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-002",
        "traveler_name": "Rohan Mehta",
        "origin_iata": "BOM",
        "destination_iata": "JFK",
        "cabin_class": "business",
        "departure_date": "2024-02-05",
        "arrival_date": "2024-02-06",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-002",
        "traveler_name": "Rohan Mehta",
        "origin_iata": "JFK",
        "destination_iata": "BOM",
        "cabin_class": "business",
        "departure_date": "2024-02-12",
        "arrival_date": "2024-02-13",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-003",
        "traveler_name": "Ananya Patel",
        "origin_iata": "DEL",
        "destination_iata": "SIN",
        "cabin_class": "economy",
        "departure_date": "2024-02-20",
        "arrival_date": "2024-02-20",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-004",
        "traveler_name": "Vikram Nair",
        "origin_iata": "BLR",
        "destination_iata": "FRA",
        "cabin_class": "premium_economy",
        "departure_date": "2024-03-10",
        "arrival_date": "2024-03-11",
    },
    {
        # This entry has an unknown airport code to test the warning path
        "type": "flight",
        "trip_id": "TRIP-2024-005",
        "traveler_name": "Sneha Gupta",
        "origin_iata": "DEL",
        "destination_iata": "XYZ",   # unknown code — no coords available
        "cabin_class": "economy",
        "departure_date": "2024-03-22",
        "arrival_date": "2024-03-22",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-006",
        "traveler_name": "Arjun Kapoor",
        "origin_iata": "DEL",
        "destination_iata": "DXB",
        "cabin_class": "economy",
        "departure_date": "2024-04-01",
        "arrival_date": "2024-04-01",
    },
    {
        "type": "flight",
        "trip_id": "TRIP-2024-007",
        "traveler_name": "Kavya Reddy",
        "origin_iata": "MAA",
        "destination_iata": "SIN",
        "cabin_class": "business",
        "departure_date": "2024-04-15",
        "arrival_date": "2024-04-15",
        # Explicitly provided distance (from travel tool, which knows the actual routing)
        "distance_km": 2891,
    },
    # --- Hotels ---
    {
        "type": "hotel",
        "trip_id": "TRIP-2024-001",
        "traveler_name": "Priya Sharma",
        "hotel_name": "The Strand Palace Hotel",
        "check_in_date": "2024-01-09",
        "check_out_date": "2024-01-15",
        "nights": 6,
        "country": "GB",
    },
    {
        "type": "hotel",
        "trip_id": "TRIP-2024-002",
        "traveler_name": "Rohan Mehta",
        "hotel_name": "Marriott Midtown Manhattan",
        "check_in_date": "2024-02-06",
        "check_out_date": "2024-02-12",
        "nights": 6,
        "country": "US",
    },
    {
        "type": "hotel",
        "trip_id": "TRIP-2024-004",
        "traveler_name": "Vikram Nair",
        "hotel_name": "Radisson Blu Frankfurt",
        "check_in_date": "2024-03-11",
        "check_out_date": "2024-03-14",
        "nights": 3,
        "country": "DE",
    },
    # --- Ground Transport ---
    {
        "type": "ground",
        "sub_type": "taxi",
        "trip_id": "TRIP-2024-001",
        "traveler_name": "Priya Sharma",
        "date": "2024-01-08",
        "distance_km": 62,   # approx DEL airport to city
        "description": "Airport transfer",
    },
    {
        "type": "ground",
        "sub_type": "train",
        "trip_id": "TRIP-2024-002",
        "traveler_name": "Rohan Mehta",
        "date": "2024-02-07",
        "distance_km": 28,
        "description": "JFK to Penn Station via AirTrain + NJ Transit",
    },
    {
        "type": "ground",
        "sub_type": "car_rental",
        "trip_id": "TRIP-2024-004",
        "traveler_name": "Vikram Nair",
        "date": "2024-03-11",
        # No distance provided — triggers warning
        "description": "Sixt rental, 3 days Frankfurt area",
    },
]
