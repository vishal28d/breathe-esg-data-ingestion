"""
Ingestion logic for all three source types.

Design notes:
- Each parser returns a list of (raw_dict, normalized_fields) tuples.
- Normalization is kept separate from parsing so errors in one don't corrupt the other.
- We store the raw_dict before anything else so we always have a source-of-truth.
"""
import csv
import io
import json
import math
import re
import decimal
from datetime import date, datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Unit conversion helpers
# ---------------------------------------------------------------------------

LITRES_PER_UNIT = {
    'l': 1.0, 'litre': 1.0, 'litres': 1.0, 'liter': 1.0, 'liters': 1.0,
    'l_fuel': 1.0,
    'gal': 3.78541, 'gallon': 3.78541, 'gallons': 3.78541,
    'gal_us': 3.78541,
    'm3': 1000.0, 'cubic_meter': 1000.0,
}

KWH_PER_UNIT = {
    'kwh': 1.0, 'kWh': 1.0,
    'mwh': 1000.0, 'MWh': 1000.0,
    'gj': 277.778, 'GJ': 277.778,
    'mj': 0.277778, 'MJ': 0.277778,
}

KM_PER_UNIT = {
    'km': 1.0, 'kms': 1.0,
    'mi': 1.60934, 'mile': 1.60934, 'miles': 1.60934,
}

# Airport coordinate lookup (subset for demo — a real deployment would use a full IATA DB)
AIRPORT_COORDS = {
    'LHR': (51.4775, -0.4614),   # London Heathrow
    'JFK': (40.6413, -73.7781),  # New York JFK
    'DEL': (28.5562, 77.1000),   # Delhi
    'BOM': (19.0896, 72.8656),   # Mumbai
    'SIN': (1.3644, 103.9915),   # Singapore Changi
    'DXB': (25.2532, 55.3657),   # Dubai
    'CDG': (49.0097, 2.5479),    # Paris CDG
    'FRA': (50.0379, 8.5622),    # Frankfurt
    'HKG': (22.3080, 113.9185),  # Hong Kong
    'SYD': (-33.9399, 151.1753), # Sydney
    'ORD': (41.9742, -87.9073),  # Chicago O'Hare
    'LAX': (33.9425, -118.4081), # Los Angeles
    'BLR': (13.1979, 77.7063),   # Bengaluru
    'HYD': (17.2403, 78.4294),   # Hyderabad
    'MAA': (12.9941, 80.1709),   # Chennai
    'CCU': (22.6547, 88.4467),   # Kolkata
    'AMD': (23.0773, 72.6347),   # Ahmedabad
    'GOI': (15.3808, 73.8314),   # Goa
}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def flight_distance_km(origin: str, dest: str) -> Optional[float]:
    origin, dest = origin.upper().strip(), dest.upper().strip()
    if origin in AIRPORT_COORDS and dest in AIRPORT_COORDS:
        lat1, lon1 = AIRPORT_COORDS[origin]
        lat2, lon2 = AIRPORT_COORDS[dest]
        return haversine_km(lat1, lon1, lat2, lon2)
    return None


def parse_date_flexible(date_str: str) -> Optional[date]:
    """
    Handle multiple date formats seen in SAP and utility exports:
    DD.MM.YYYY (SAP German), YYYY-MM-DD (ISO), MM/DD/YYYY, DD-MM-YYYY
    """
    date_str = date_str.strip()
    for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y',
                '%Y/%m/%d', '%d/%m/%Y', '%Y%m%d']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def safe_decimal(val_str: str) -> Optional[decimal.Decimal]:
    """Parse a number that may use comma as decimal separator (SAP German locale)."""
    if not val_str or not val_str.strip():
        return None
    cleaned = val_str.strip().replace(' ', '')
    # Detect European format: 1.234,56 -> 1234.56
    if re.match(r'^\d{1,3}(\.\d{3})*(,\d+)?$', cleaned):
        cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
        cleaned = cleaned.replace(',', '')
    try:
        return decimal.Decimal(cleaned)
    except decimal.InvalidOperation:
        return None


# ---------------------------------------------------------------------------
# SAP Flat File Parser
# ---------------------------------------------------------------------------
# SAP IS-Oil flat file export via ABAP report / BAPI call.
# Headers are semi-standard; clients often configure their own field names.
# We support a known set of column aliases (including German names).
# Ingestion: file upload.
# Scope: 1 (direct fuel purchase by company-owned facilities).

SAP_COLUMN_ALIASES = {
    # Document date
    'BLDAT': 'doc_date', 'BUDAT': 'doc_date', 'posting_date': 'doc_date',
    'Posting Date': 'doc_date', 'Document Date': 'doc_date',
    # Material / description
    'MATNR': 'material', 'Material': 'material', 'Material Number': 'material',
    'TXZ01': 'description', 'Short Text': 'description', 'Description': 'description',
    # Quantity
    'MENGE': 'quantity', 'Quantity': 'quantity', 'Menge': 'quantity',
    'Qty': 'quantity',
    # Unit of measure
    'MEINS': 'unit', 'Base Unit': 'unit', 'UoM': 'unit', 'Unit': 'unit',
    'Einheit': 'unit',
    # Plant code
    'WERKS': 'plant', 'Plant': 'plant', 'Werk': 'plant',
    # Vendor
    'LIFNR': 'vendor', 'Vendor': 'vendor',
    # Cost / amount (optional)
    'NETWR': 'net_value', 'Net Value': 'net_value', 'Amount': 'net_value',
    # Currency
    'WAERS': 'currency', 'Currency': 'currency',
}

# Map material codes / descriptions to ESG category
SAP_MATERIAL_MAP = {
    'diesel': 'diesel',
    'petrol': 'petrol', 'gasoline': 'petrol',
    'lhv': 'diesel',  # low-heat-value diesel codes in some IS-Oil configs
    'natural gas': 'natural_gas', 'gas': 'natural_gas',
    'lpg': 'lpg',
    'hfo': 'hfo',  # heavy fuel oil
    'kerosene': 'kerosene',
}


def _classify_sap_material(material: str, description: str) -> str:
    combined = (material + ' ' + description).lower()
    for keyword, category in SAP_MATERIAL_MAP.items():
        if keyword in combined:
            return category
    return 'unknown_fuel'


def parse_sap_csv(file_bytes: bytes):
    """
    Parse a SAP flat file CSV export.
    Returns list of (raw_dict, normalized_fields_dict, warnings_list) tuples.
    """
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = file_bytes.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text), delimiter=',')
    # Access fieldnames now to trigger lazy header read without consuming the iterator
    _ = reader.fieldnames
    if not reader.fieldnames:
        # Bug 2 fix: create a *fresh* StringIO so the header row is not lost
        reader = csv.DictReader(io.StringIO(text), delimiter=';')

    results = []
    for row_i, row in enumerate(reader):
        raw = dict(row)
        # Map column names to canonical names
        normalized_row = {}
        for k, v in raw.items():
            canonical = SAP_COLUMN_ALIASES.get(k.strip(), k.strip().lower().replace(' ', '_'))
            normalized_row[canonical] = v.strip() if v else ''

        warnings = []

        # Parse date
        doc_date = None
        for date_field in ['doc_date', 'bldat', 'budat']:
            raw_date = normalized_row.get(date_field, '')
            if raw_date:
                doc_date = parse_date_flexible(raw_date)
                if doc_date:
                    break
        if not doc_date:
            warnings.append('Could not parse date from row')

        # Parse quantity
        qty_str = normalized_row.get('quantity', '')
        qty = safe_decimal(qty_str)
        if qty is None:
            warnings.append(f'Could not parse quantity: {qty_str!r}')

        # Parse unit
        unit_raw = normalized_row.get('unit', '').lower().strip()
        if unit_raw in LITRES_PER_UNIT:
            unit_norm = 'litres'
            # Bug 3 fix: always assign qty_norm explicitly in both branches
            qty_norm = qty * decimal.Decimal(str(LITRES_PER_UNIT[unit_raw])) if qty is not None else None
        else:
            unit_norm = unit_raw or 'unknown'
            qty_norm = qty  # no conversion — stored as-is
            if unit_raw:
                # Bug 4 note: 'GAL' is treated as US gallons (3.785 L). A value like '5.000'
                # in a German-locale file means 5000, not 5.0. The safe_decimal function
                # disambiguates this via the thousands-separator regex.
                warnings.append(f'Unknown unit {unit_raw!r} — stored as-is without conversion')

        # Classify material
        material = normalized_row.get('material', '')
        description = normalized_row.get('description', '')
        category = _classify_sap_material(material, description)
        if category == 'unknown_fuel':
            warnings.append(f'Could not classify material: {material!r} / {description!r}')

        plant = normalized_row.get('plant', '')

        normalized_fields = {
            'scope': 1,
            'category': category,
            'sub_category': '',
            'activity_date_start': doc_date,
            'activity_date_end': doc_date,
            'original_value': qty,
            'original_unit': unit_raw,
            'normalized_value': qty_norm,
            'normalized_unit': unit_norm,
            'description': f"{description} | Plant: {plant} | Vendor: {normalized_row.get('vendor', '')}",
            'plant_code': plant,
        }

        status = 'ERROR' if (doc_date is None or qty is None) else (
            'FLAGGED' if warnings else 'PENDING'
        )

        results.append((raw, normalized_fields, warnings, status))

    return results


# ---------------------------------------------------------------------------
# Utility Portal CSV Parser
# ---------------------------------------------------------------------------
# Format: Green Button / standard utility portal CSV.
# Billing periods often span non-calendar-month intervals (e.g. 14th to 13th).
# Units: kWh most common; some exports give MWh or GJ.
# Ingestion: file upload.
# Scope: 2 (purchased electricity).

UTILITY_COLUMN_ALIASES = {
    'start date': 'period_start', 'Start Date': 'period_start', 'From': 'period_start',
    'From Date': 'period_start', 'Bill Period Start': 'period_start', 'period_start': 'period_start',
    'end date': 'period_end', 'End Date': 'period_end', 'To': 'period_end',
    'To Date': 'period_end', 'Bill Period End': 'period_end', 'period_end': 'period_end',
    'consumption': 'consumption', 'Consumption': 'consumption', 'Usage': 'consumption',
    'Energy Used': 'consumption', 'kWh': 'consumption', 'usage': 'consumption',
    'unit': 'unit', 'Unit': 'unit', 'Units': 'unit',
    'meter_id': 'meter_id', 'Meter ID': 'meter_id', 'Meter': 'meter_id',
    'Account': 'account', 'account': 'account', 'Account Number': 'account',
    'facility': 'facility_name', 'Facility': 'facility_name', 'Site': 'facility_name',
    'tariff': 'tariff', 'Tariff': 'tariff', 'Rate': 'tariff',
    'cost': 'cost', 'Cost': 'cost', 'Amount': 'cost', 'Bill Amount': 'cost',
}


def parse_utility_csv(file_bytes: bytes):
    """
    Parse a utility portal CSV export.
    Returns list of (raw_dict, normalized_fields_dict, warnings_list, status) tuples.
    """
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = file_bytes.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))
    results = []

    for row_i, row in enumerate(reader):
        raw = dict(row)
        norm_row = {}
        for k, v in raw.items():
            canonical = UTILITY_COLUMN_ALIASES.get(k.strip(), k.strip().lower().replace(' ', '_'))
            norm_row[canonical] = v.strip() if v else ''

        warnings = []

        # Parse billing period
        period_start = parse_date_flexible(norm_row.get('period_start', ''))
        period_end = parse_date_flexible(norm_row.get('period_end', ''))
        if not period_start:
            warnings.append('Could not parse period_start date')
        if not period_end:
            warnings.append('Could not parse period_end date')
        if period_start and period_end and period_end < period_start:
            warnings.append('period_end is before period_start — likely data error')

        # Check for non-calendar-month billing period.
        # Bug 6 fix: this is an informational note, not a suspicious anomaly.
        # Non-calendar periods are common (e.g. UK utilities bill 14th-to-13th).
        # We warn but do NOT automatically flag the row — that would flag all utility rows.
        if period_start and period_end:
            if period_start.day != 1 or period_end.day not in range(28, 32):
                warnings.append(
                    f'Non-calendar billing period: {period_start} to {period_end}. '
                    'Verify no double-counting with adjacent periods. (Informational)'
                )

        # Parse consumption
        consumption_str = norm_row.get('consumption', '')
        consumption = safe_decimal(consumption_str)
        if consumption is None:
            warnings.append(f'Could not parse consumption: {consumption_str!r}')
        elif consumption < 0:
            warnings.append(f'Negative consumption value {consumption} — likely credit/reversal')

        # Normalize unit to kWh
        unit_raw = norm_row.get('unit', 'kwh').lower().strip() or 'kwh'
        factor = KWH_PER_UNIT.get(unit_raw)
        if factor is None:
            warnings.append(f'Unknown unit {unit_raw!r} — treating as kWh')
            factor = 1.0
            unit_norm = unit_raw
        else:
            unit_norm = 'kWh'

        consumption_norm = (
            consumption * decimal.Decimal(str(factor)) if consumption is not None else None
        )

        # Sanity check: very high consumption for a single meter.
        # Bug 9 fix: use abs() so negative credits (e.g. solar net-metering) are also checked.
        if consumption_norm is not None and abs(consumption_norm) > decimal.Decimal('500000'):
            warnings.append(
                f'Very high consumption ({consumption_norm} kWh) — verify this is correct'
            )

        normalized_fields = {
            'scope': 2,
            'category': 'electricity',
            'sub_category': norm_row.get('tariff', ''),
            'activity_date_start': period_start,
            'activity_date_end': period_end,
            'original_value': consumption,
            'original_unit': unit_raw,
            'normalized_value': consumption_norm,
            'normalized_unit': unit_norm,
            'description': (
                f"Meter: {norm_row.get('meter_id', 'N/A')} | "
                f"Account: {norm_row.get('account', 'N/A')} | "
                f"Facility: {norm_row.get('facility_name', 'N/A')}"
            ),
            'facility_name': norm_row.get('facility_name', ''),
        }

        # Bug 6 fix: only flag ERROR or FLAGGED for real parse failures / suspicious values.
        # A non-calendar billing period is informational, not a flag-worthy anomaly.
        # Determine which warnings are "suspicion-level" vs informational.
        suspicion_warnings = [
            w for w in warnings
            if 'Informational' not in w and 'Non-calendar' not in w
        ]
        status = 'ERROR' if (consumption is None or period_start is None) else (
            'FLAGGED' if suspicion_warnings else 'PENDING'
        )

        results.append((raw, normalized_fields, warnings, status))

    return results


# ---------------------------------------------------------------------------
# Corporate Travel Parser (Navan-style JSON)
# ---------------------------------------------------------------------------
# Simulates a pull from Navan's /v1/bookings endpoint.
# Data: JSON array of booking objects.
# Ingestion: triggered via API pull button (no file upload needed).
# Scope: 3 (business travel).
# Key challenge: flights only give IATA codes; we compute great-circle distance.

TRAVEL_CLASS_MAP = {
    'economy': 'flight_economy',
    'economy_plus': 'flight_economy',
    'premium_economy': 'flight_premium_economy',
    'business': 'flight_business',
    'first': 'flight_first',
    'first_class': 'flight_first',
}

HOTEL_NIGHTS_CATEGORY = 'hotel_nights'
GROUND_CATEGORIES = {'taxi': 'taxi', 'car_rental': 'car_rental',
                     'train': 'rail', 'rail': 'rail', 'rideshare': 'taxi'}


def parse_travel_json(data: list):
    """
    Parse a Navan-style booking JSON array.
    Returns list of (raw_dict, normalized_fields_dict, warnings_list, status) tuples.
    """
    results = []

    for booking in data:
        raw = booking
        warnings = []
        booking_type = booking.get('type', '').lower()  # 'flight', 'hotel', 'ground'

        # Common fields
        traveler = booking.get('traveler_name', '')
        trip_id = booking.get('trip_id', '')

        # Parse booking date
        travel_date_str = booking.get('departure_date') or booking.get('check_in_date') or booking.get('date', '')
        travel_date = parse_date_flexible(travel_date_str) if travel_date_str else None
        if not travel_date:
            warnings.append('Could not parse travel date')

        travel_date_end_str = booking.get('arrival_date') or booking.get('check_out_date') or booking.get('date', '')
        # Bug 7 fix: use `or travel_date` not a ternary on empty string;
        # parse_date_flexible returns None on bad strings, so fall back to travel_date.
        travel_date_end = (parse_date_flexible(travel_date_end_str) if travel_date_end_str else None) or travel_date

        if booking_type == 'flight':
            origin = booking.get('origin_iata', '')
            dest = booking.get('destination_iata', '')
            cabin = booking.get('cabin_class', 'economy').lower()
            category = TRAVEL_CLASS_MAP.get(cabin, 'flight_economy')

            # Prefer provided distance; fall back to haversine
            distance_km = booking.get('distance_km')
            if distance_km:
                distance_km = float(distance_km)
            else:
                distance_km = flight_distance_km(origin, dest)
                if distance_km is None:
                    warnings.append(
                        f'Unknown IATA codes {origin}/{dest} — cannot compute distance'
                    )
                else:
                    # Add uplift factor (10%) for routing inefficiency
                    distance_km = round(distance_km * 1.1, 2)
                    warnings.append(
                        f'Distance estimated via great-circle ({distance_km:.0f} km with 10% uplift). '
                        'Verify against actual routing.'
                    )

            normalized_fields = {
                'scope': 3,
                'category': category,
                'sub_category': cabin,
                'activity_date_start': travel_date,
                'activity_date_end': travel_date_end,
                'original_value': decimal.Decimal(str(distance_km)) if distance_km else None,
                'original_unit': 'km',
                'normalized_value': decimal.Decimal(str(distance_km)) if distance_km else None,
                'normalized_unit': 'km',
                'description': f"Flight: {origin} -> {dest} | Cabin: {cabin} | Traveler: {traveler} | Trip: {trip_id}",
            }
            status = 'ERROR' if (distance_km is None or travel_date is None) else (
                'FLAGGED' if warnings else 'PENDING'
            )

        elif booking_type == 'hotel':
            nights = booking.get('nights', 0)
            try:
                nights = int(nights)
            except (ValueError, TypeError):
                nights = None
                warnings.append('Could not parse number of nights')

            country = booking.get('country', 'unknown')
            normalized_fields = {
                'scope': 3,
                'category': HOTEL_NIGHTS_CATEGORY,
                'sub_category': country,
                'activity_date_start': travel_date,
                'activity_date_end': travel_date_end,
                'original_value': decimal.Decimal(str(nights)) if nights else None,
                'original_unit': 'nights',
                'normalized_value': decimal.Decimal(str(nights)) if nights else None,
                'normalized_unit': 'nights',
                'description': f"Hotel: {booking.get('hotel_name', 'N/A')} | {country} | Nights: {nights} | Traveler: {traveler}",
            }
            status = 'ERROR' if nights is None else ('FLAGGED' if warnings else 'PENDING')

        elif booking_type == 'ground':
            ground_type = booking.get('sub_type', 'taxi').lower()
            category = GROUND_CATEGORIES.get(ground_type, 'taxi')
            distance_km = booking.get('distance_km')
            if distance_km:
                distance_km = float(distance_km)
            else:
                warnings.append('Distance not provided for ground transport — cannot compute emissions')

            normalized_fields = {
                'scope': 3,
                'category': category,
                'sub_category': ground_type,
                'activity_date_start': travel_date,
                'activity_date_end': travel_date,
                'original_value': decimal.Decimal(str(distance_km)) if distance_km else None,
                'original_unit': 'km',
                'normalized_value': decimal.Decimal(str(distance_km)) if distance_km else None,
                'normalized_unit': 'km',
                'description': f"Ground ({ground_type}) | Traveler: {traveler} | Trip: {trip_id}",
            }
            status = 'ERROR' if distance_km is None else ('FLAGGED' if warnings else 'PENDING')

        else:
            warnings.append(f'Unknown booking type: {booking_type!r}')
            normalized_fields = {
                'scope': 3, 'category': 'unknown', 'sub_category': '',
                'activity_date_start': travel_date, 'activity_date_end': travel_date,
                'original_value': None, 'original_unit': '', 'normalized_value': None,
                'normalized_unit': '', 'description': str(booking),
            }
            status = 'ERROR'

        results.append((raw, normalized_fields, warnings, status))

    return results
