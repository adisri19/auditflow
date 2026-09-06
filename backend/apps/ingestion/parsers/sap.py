import io
import csv
import openpyxl
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from django.utils.dateparse import parse_date
from apps.ingestion.models import RawRow
from apps.emissions.models import ActivityRecord

SAP_COLUMN_MAP = {
    "werks": "facility_code",
    "bldat": "raw_date",
    "menge": "raw_quantity",
    "meins": "raw_unit",
    "bktxt": "description",
    "matnr": "material_number",
    "netwr": "net_value",
    "waers": "currency",
    "plant": "facility_code",
    "posting date": "raw_date",
    "quantity": "raw_quantity",
    "unit": "raw_unit",
    "text": "description",
    "material": "material_number",
}

SAP_UNIT_MAP = {
    "L":    ("L",   "litre", Decimal("1.0")),
    "GAL":  ("L",   "gallon→litre", Decimal("3.78541")),
    "KG":   ("kg",  "kilogram", Decimal("1.0")),
    "G":    ("kg",  "gram→kg", Decimal("0.001")),
    "T":    ("t",   "metric tonne", Decimal("1.0")),
    "M3":   ("m3",  "cubic metre", Decimal("1.0")),
    "KWH":  ("kWh", "kilowatt-hour", Decimal("1.0")),
    "MWH":  ("kWh", "megawatt-hour", Decimal("1000.0")),
}

# Standard factors for demonstration
SAP_EF_MAP = {
    "DIESEL": (Decimal("2.68"), "kgCO2e/L"),
    "PETROL": (Decimal("2.31"), "kgCO2e/L"),
    "LPG":    (Decimal("1.51"), "kgCO2e/L"),
    "NATGAS": (Decimal("1.91"), "kgCO2e/m3"),
    "FUELOIL":(Decimal("2.98"), "kgCO2e/L"),
    "KEROSENE":(Decimal("2.54"), "kgCO2e/L"),
    "STEEL":  (Decimal("1.85"), "kgCO2e/kg"),
    "ALUM":   (Decimal("8.10"), "kgCO2e/kg"),
    "PLAST":  (Decimal("2.00"), "kgCO2e/kg"),
    "CHEM":   (Decimal("3.00"), "kgCO2e/kg"),
    "PAPER":  (Decimal("0.92"), "kgCO2e/kg"),
}

FUEL_MATERIAL_PREFIXES = ["DIESEL", "PETROL", "LPG", "NATGAS", "FUELOIL", "KEROSENE"]
PROCUREMENT_MATERIAL_PREFIXES = ["STEEL", "ALUM", "PLAST", "CHEM", "PAPER"]

def parse_sap_date(date_str):
    """Parse date from YYYYMMDD or DD.MM.YYYY or standard ISO date formats."""
    date_str = str(date_str).strip()
    for fmt in ("%Y%m%d", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    parsed = parse_date(date_str)
    if parsed:
        return parsed
    raise ValueError(f"Unknown date format: {date_str}")

def parse_sap_file(file_obj, batch) -> list:
    """
    Reads SAP flat file, creates RawRows, attempts normalization, and saves ActivityRecords.
    """
    raw_rows_data = []
    filename = getattr(file_obj, 'name', '').lower()

    if filename.endswith('.xlsx'):
        # Excel parsing
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        sheet = wb.active
        headers = []
        for i, row in enumerate(sheet.iter_rows(values_only=True), 1):
            if i == 1:
                headers = [str(cell).strip() for cell in row if cell is not None]
                continue
            if not any(row):
                continue
            row_dict = {}
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers):
                    row_dict[headers[col_idx]] = cell
            raw_rows_data.append(row_dict)
    else:
        # Text/CSV parsing
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig', errors='ignore')
        
        # Sniff delimiter: tabs or semicolons or commas
        delimiter = '\t'
        if ';' in content and content.count(';') > content.count('\t'):
            delimiter = ';'
        elif ',' in content and content.count(',') > content.count('\t'):
            delimiter = ','

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        for row in reader:
            raw_rows_data.append({k.strip(): v.strip() for k, v in row.items() if k is not None})

    created_records = []
    row_count = 0
    error_count = 0

    for idx, raw_dict in enumerate(raw_rows_data, 1):
        row_count += 1
        raw_row = RawRow.objects.create(
            batch=batch,
            tenant=batch.tenant,
            row_index=idx,
            raw_data=raw_dict
        )

        try:
            # 1. Map columns using case-insensitive mapping
            mapped_data = {}
            for original_key, val in raw_dict.items():
                if not original_key:
                    continue
                clean_key = original_key.lower().strip()
                if clean_key in SAP_COLUMN_MAP:
                    mapped_data[SAP_COLUMN_MAP[clean_key]] = val
                else:
                    # Keep unmapped fields as-is
                    mapped_data[clean_key] = val

            # Check required fields
            required = ["facility_code", "raw_date", "raw_quantity", "raw_unit"]
            for field in required:
                if field not in mapped_data or mapped_data[field] in (None, ''):
                    raise ValueError(f"Missing required field: {field}")

            # 2. Normalize Quantity and Unit
            raw_unit_str = str(mapped_data["raw_unit"]).strip().upper()
            if raw_unit_str not in SAP_UNIT_MAP:
                raise ValueError(f"Unsupported unit: {raw_unit_str}")

            canonical_unit, desc, conversion_factor = SAP_UNIT_MAP[raw_unit_str]
            try:
                # Handle potential float/string conversions
                qty_val = Decimal(str(mapped_data["raw_quantity"]).replace(',', '.'))
            except Exception:
                raise ValueError(f"Invalid quantity value: {mapped_data['raw_quantity']}")

            normalized_qty = qty_val * conversion_factor

            # 3. Categorize Category and Scope from Material prefix
            material_number = str(mapped_data.get("material_number", "")).upper()
            scope = None
            category = None

            is_fuel = any(material_number.startswith(prefix) for prefix in FUEL_MATERIAL_PREFIXES)
            is_procurement = any(material_number.startswith(prefix) for prefix in PROCUREMENT_MATERIAL_PREFIXES)

            if is_fuel:
                scope = 1
                category = "FUEL_COMBUSTION"
            elif is_procurement:
                scope = 3
                category = "PROCUREMENT"
            else:
                # Let's inspect the description for keywords if material number is generic
                desc_upper = str(mapped_data.get("description", "")).upper()
                if any(prefix in desc_upper for prefix in FUEL_MATERIAL_PREFIXES):
                    scope = 1
                    category = "FUEL_COMBUSTION"
                elif any(prefix in desc_upper for prefix in PROCUREMENT_MATERIAL_PREFIXES):
                    scope = 3
                    category = "PROCUREMENT"
                else:
                    # Default fallback or raise parse error if not identifiable
                    raise ValueError(f"Could not identify scope/category for material '{material_number}'")

            # 4. Parse Date
            activity_date = parse_sap_date(mapped_data["raw_date"])

            # 5. Emission Factor & CO2e Calculation
            ef_val = None
            ef_unit = ""
            co2e = None

            # Attempt to find standard factor
            factor_found = False
            for prefix, (factor, unit_str) in SAP_EF_MAP.items():
                if material_number.startswith(prefix) or prefix in str(mapped_data.get("description", "")).upper():
                    ef_val = factor
                    ef_unit = unit_str
                    factor_found = True
                    break

            if factor_found and ef_val:
                # co2e_kg = quantity * emission_factor
                # Need to verify compatibility of units, but here we assume canonical multiplication
                co2e = normalized_qty * ef_val

            # 6. Generate Source Hash for Dedup
            # Hash the string representation of sorted raw data
            raw_str = json.dumps(raw_dict, sort_keys=True)
            source_hash = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

            if ActivityRecord.objects.filter(tenant=batch.tenant, source_hash=source_hash).exists():
                continue

            # 7. Create ActivityRecord
            record = ActivityRecord.objects.create(
                tenant=batch.tenant,
                raw_row=raw_row,
                batch=batch,
                scope=scope,
                category=category,
                description=mapped_data.get("description", f"SAP Material: {material_number}"),
                activity_date=activity_date,
                facility_code=mapped_data["facility_code"],
                location=mapped_data.get("werks", mapped_data["facility_code"]),
                quantity=normalized_qty,
                unit=canonical_unit,
                emission_factor=ef_val,
                emission_factor_unit=ef_unit,
                co2e_kg=co2e,
                source_system="SAP",
                source_row_id=mapped_data.get("material_number", f"row_{idx}"),
                source_hash=source_hash,
                status="PENDING",
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
