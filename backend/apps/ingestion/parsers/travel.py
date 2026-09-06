import csv
import io
import math
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from apps.ingestion.models import RawRow
from apps.emissions.models import ActivityRecord

HAVERSINE_EARTH_KM = 6371

IATA_TO_COORDS = {
    "JFK": (40.6413, -73.7781),
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "DXB": (25.2532, 55.3657),
    "BOM": (19.0896, 72.8656),
    "DEL": (28.5562, 77.1000),
    "SIN": (1.3644, 103.9915),
    "HKG": (22.3080, 113.9185),
    "SYD": (-33.9461, 151.1772),
    "LAX": (33.9425, -118.4081),
    "ORD": (41.9742, -87.9073),
    "FRA": (50.0379, 8.5622),
    "AMS": (52.3086, 4.7639),
    "SFO": (37.6213, -122.3790),
    "DFW": (32.8998, -97.0403),
    "MIA": (25.7959, -80.2870),
    "BOS": (42.3656, -71.0096),
    "YYZ": (43.6777, -79.6248),
    "NRT": (35.7720, 140.3929),
    "ICN": (37.4602, 126.4407),
    "PEK": (40.0799, 116.6031),
    "PVG": (31.1443, 121.8083),
    "GRU": (-23.4356, -46.4731),
    "JNB": (-26.1367, 28.2411),
    "MEX": (19.4363, -99.0721),
    "MAD": (40.4936, -3.5668),
    "BCN": (41.2971, 2.0785),
    "FCO": (41.8003, 12.2389),
    "MUC": (48.3538, 11.7861),
    "ZUR": (47.4647, 8.5492),
    "CPH": (55.6180, 12.6508),
    "HEL": (60.3172, 24.9633),
    "WAW": (52.1657, 20.9671),
    "IST": (41.2610, 28.7261),
    "DOH": (25.2611, 51.5650),
    "AUH": (24.4330, 54.6511),
    "KUL": (2.7456, 101.7099),
    "BKK": (13.6811, 100.7475),
    "CGK": (-6.1255, 106.6559),
    "MNL": (14.5086, 121.0194),
    "CCU": (22.6549, 88.4467),
    "MAA": (12.9900, 80.1693),
    "BLR": (13.1986, 77.7066),
    "HYD": (17.2313, 78.4298),
    "AMD": (23.0772, 72.6347),
    "COK": (10.1520, 76.4019),
    "IDR": (22.7218, 75.8011),
    "LKO": (26.7606, 80.8893),
    "NAG": (21.0922, 79.0472),
}

def haversine_km(iata_origin: str, iata_dest: str) -> float | None:
    """Return great-circle distance in km, or None if either IATA not in table."""
    origin = str(iata_origin).strip().upper()
    dest = str(iata_dest).strip().upper()
    if origin not in IATA_TO_COORDS or dest not in IATA_TO_COORDS:
        return None
    lat1, lon1 = IATA_TO_COORDS[origin]
    lat2, lon2 = IATA_TO_COORDS[dest]
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return HAVERSINE_EARTH_KM * c

FLIGHT_EF = {  # kg CO2e per passenger-km
    "ECONOMY": Decimal("0.255"),
    "BUSINESS": Decimal("0.614"),
    "FIRST":   Decimal("0.851"),
}
HOTEL_EF_PER_NIGHT = Decimal("31.2")   # kg CO2e per night (global average)
GROUND_EF = {
    "CAR":  Decimal("0.171"),   # kg CO2e per km (average car)
    "RAIL": Decimal("0.041"),   # kg CO2e per km (European average rail)
}

TRAVEL_COLUMN_MAP = {
    "trip id": "trip_id",
    "traveller name": "traveller_name",
    "traveller email": "traveller_email",
    "booking date": "booking_date",
    "travel date": "activity_date",
    "segment type": "segment_type",
    "origin": "origin",
    "destination": "destination",
    "origin iata": "origin_iata",
    "destination iata": "destination_iata",
    "duration": "duration",
    "distance": "distance",
    "class": "travel_class",
    "cost": "cost",
    "currency": "currency",
    "carbon": "carbon_provided"
}

def parse_travel_date(date_str):
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")

def parse_travel_csv(file_obj, batch) -> list:
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig', errors='ignore')

    # Detect delimiter
    delimiter = ','
    if ';' in content and content.count(';') > content.count(','):
        delimiter = ';'
    elif '\t' in content and content.count('\t') > content.count(','):
        delimiter = '\t'

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    created_records = []
    row_count = 0
    error_count = 0

    for idx, row in enumerate(reader, 1):
        # Safely strip keys and values; replace None values with empty string
        raw_dict = {k.strip(): (v.strip() if v is not None else "") for k, v in row.items() if k is not None}
        if not any(raw_dict.values()):
            continue
        row_count += 1

        raw_row = RawRow.objects.create(
            batch=batch,
            tenant=batch.tenant,
            row_index=idx,
            raw_data=raw_dict
        )

        try:
            # Map columns
            mapped_data = {}
            for original_key, val in raw_dict.items():
                clean_key = original_key.lower().strip()
                if clean_key in TRAVEL_COLUMN_MAP:
                    mapped_data[TRAVEL_COLUMN_MAP[clean_key]] = val
                else:
                    mapped_data[clean_key] = val

            segment_type = str(mapped_data.get("segment_type", "")).upper()
            if not segment_type:
                raise ValueError("Missing Segment Type (FLIGHT/HOTEL/CAR/RAIL/GROUND).")

            act_date_str = mapped_data.get("activity_date")
            if not act_date_str:
                raise ValueError("Missing Travel Date.")
            activity_date = parse_travel_date(act_date_str)

            # Resolve Category & Scope
            # FLIGHT -> Scope 3 BUSINESS_TRAVEL_FLIGHT
            # HOTEL  -> Scope 3 BUSINESS_TRAVEL_HOTEL
            # CAR/RAIL/GROUND -> Scope 3 BUSINESS_TRAVEL_GROUND
            scope = 3
            category = ""
            quantity = Decimal("0")
            unit = ""
            ef_val = None
            ef_unit = ""
            co2e = None

            description = mapped_data.get("description", "")
            if not description:
                traveller = mapped_data.get("traveller_name", "Unknown Traveller")
                origin_name = mapped_data.get("origin", "")
                dest_name = mapped_data.get("destination", "")
                description = f"Travel for {traveller}: {origin_name} to {dest_name}"

            if segment_type == "FLIGHT":
                category = "BUSINESS_TRAVEL_FLIGHT"
                unit = "km"
                
                # Check for distance
                dist_str = mapped_data.get("distance")
                if dist_str and dist_str.strip() not in (None, "", "0"):
                    quantity = Decimal(dist_str.replace(',', '').strip())
                else:
                    # Fallback to IATA Haversine
                    origin_iata = mapped_data.get("origin_iata")
                    dest_iata = mapped_data.get("destination_iata")
                    if not origin_iata or not dest_iata:
                        raise ValueError("Distance is missing and IATA airport codes are incomplete for Flight.")
                    calculated_dist = haversine_km(origin_iata, dest_iata)
                    if calculated_dist is None:
                        raise ValueError(f"Could not calculate Haversine distance for airport codes: {origin_iata} -> {dest_iata}")
                    quantity = Decimal(calculated_dist)

                # Fetch emission factor based on class
                travel_class = str(mapped_data.get("travel_class", "ECONOMY")).upper()
                if "BUSINESS" in travel_class:
                    travel_class = "BUSINESS"
                elif "FIRST" in travel_class:
                    travel_class = "FIRST"
                else:
                    travel_class = "ECONOMY"

                ef_val = FLIGHT_EF.get(travel_class, FLIGHT_EF["ECONOMY"])
                ef_unit = "kgCO2e/passenger-km"
                co2e = quantity * ef_val

            elif segment_type == "HOTEL":
                category = "BUSINESS_TRAVEL_HOTEL"
                unit = "night"
                
                duration_str = mapped_data.get("duration")
                if not duration_str:
                    raise ValueError("Hotel segment requires Duration (nights).")
                quantity = Decimal(duration_str.strip())
                
                ef_val = HOTEL_EF_PER_NIGHT
                ef_unit = "kgCO2e/night"
                co2e = quantity * ef_val

            elif segment_type in ("CAR", "RAIL", "GROUND", "CAR_RENTAL"):
                category = "BUSINESS_TRAVEL_GROUND"
                unit = "km"
                
                dist_str = mapped_data.get("distance")
                if not dist_str:
                    raise ValueError("Ground transport segment requires Distance.")
                quantity = Decimal(dist_str.replace(',', '').strip())

                seg_sub = "CAR" if segment_type != "RAIL" else "RAIL"
                ef_val = GROUND_EF.get(seg_sub, GROUND_EF["CAR"])
                ef_unit = "kgCO2e/km"
                co2e = quantity * ef_val

            else:
                raise ValueError(f"Unknown segment type: {segment_type}")

            # Source provenance
            trip_id = mapped_data.get("trip_id") or f"row_{idx}"
            raw_str = json.dumps(raw_dict, sort_keys=True)
            source_hash = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

            if ActivityRecord.objects.filter(tenant=batch.tenant, source_hash=source_hash).exists():
                continue

            record = ActivityRecord.objects.create(
                tenant=batch.tenant,
                raw_row=raw_row,
                batch=batch,
                scope=scope,
                category=category,
                description=description,
                activity_date=activity_date,
                facility_code="Corporate HQ", # Defaults to Corporate HQ for travel
                location=mapped_data.get("destination", "Global"),
                quantity=quantity.quantize(Decimal("0.000001")),
                unit=unit,
                emission_factor=ef_val,
                emission_factor_unit=ef_unit,
                co2e_kg=co2e.quantize(Decimal("0.0000")),
                source_system="NAVAN_API", # or Concur
                source_row_id=trip_id,
                source_hash=source_hash,
                status="PENDING"
            )
            created_records.append(record)

        except Exception as e:
            error_count += 1
            raw_row.parse_error = str(e)
            raw_row.save()

    batch.row_count = row_count
    batch.error_count = error_count
    batch.status = "DONE" if error_count < row_count else "FAILED"
    batch.save()

    return created_records
