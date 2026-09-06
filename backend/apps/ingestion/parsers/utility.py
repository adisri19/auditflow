import csv
import io
from datetime import datetime, date, timedelta
from decimal import Decimal
import hashlib
import json
import calendar
from apps.ingestion.models import RawRow
from apps.emissions.models import ActivityRecord

# Standard emission factor for grid electricity (Scope 2)
# Average US/UK grid emission factor: ~0.35 kg CO2e / kWh
UTILITY_EF = Decimal("0.35")
UTILITY_EF_UNIT = "kgCO2e/kWh"

def parse_util_date(date_str):
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")

def parse_billing_period(period_str):
    """Parse a period range like '01/15/2024 - 02/14/2024' or 'Jan 15, 2024 to Feb 14, 2024'."""
    period_str = str(period_str).strip()
    for sep in (" - ", " to ", " -", "- ", " to", "to "):
        if sep in period_str:
            parts = period_str.split(sep)
            if len(parts) == 2:
                try:
                    start = parse_util_date(parts[0])
                    end = parse_util_date(parts[1])
                    return start, end
                except Exception:
                    pass
    # If not split, treat as single date
    dt = parse_util_date(period_str)
    return dt, dt

def detect_utility_format(headers) -> str:
    headers_lower = [h.lower().strip() for h in headers]
    if any("meter id" in h or "account number" in h or "peak kwh" in h for h in headers_lower):
        return "UK"
    return "US"

def split_billing_period(start_date, end_date, total_qty, total_cost):
    """
    Splits billing periods crossing month boundaries proportionally by day count.
    Returns a list of dicts: {"start": date, "end": date, "qty": Decimal, "cost": Decimal, "days": int}
    """
    if start_date >= end_date:
        return [{"start": start_date, "end": end_date, "qty": total_qty, "cost": total_cost, "days": 1}]
    
    total_days = (end_date - start_date).days + 1
    splits = []
    curr_date = start_date
    
    while curr_date <= end_date:
        _, last_day_of_month = calendar.monthrange(curr_date.year, curr_date.month)
        month_end = date(curr_date.year, curr_date.month, last_day_of_month)
        split_end = min(month_end, end_date)
        
        days_in_split = (split_end - curr_date).days + 1
        proportion = Decimal(days_in_split) / Decimal(total_days)
        
        splits.append({
            "start": curr_date,
            "end": split_end,
            "qty": total_qty * proportion,
            "cost": total_cost * proportion if total_cost is not None else None,
            "days": days_in_split
        })
        curr_date = split_end + timedelta(days=1)
        
    return splits

def parse_utility_csv(file_obj, batch) -> list:
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig', errors='ignore')

    # Detect delimiter
    delimiter = ','
    if ';' in content and content.count(';') > content.count(','):
        delimiter = ';'
    elif '\t' in content and content.count('\t') > content.count(','):
        delimiter = '\t'

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows_data = list(reader)
    if not rows_data:
        return []

    headers = [h.strip() for h in rows_data[0] if h is not None]
    raw_rows_list = rows_data[1:]
    fmt = detect_utility_format(headers)

    created_records = []
    row_count = 0
    error_count = 0

    headers_lower = [h.lower() for h in headers]

    for idx, row in enumerate(raw_rows_list, 1):
        if not any(row):
            continue
        row_count += 1
        raw_dict = {}
        for col_idx, val in enumerate(row):
            if col_idx < len(headers):
                raw_dict[headers[col_idx]] = val

        raw_row = RawRow.objects.create(
            batch=batch,
            tenant=batch.tenant,
            row_index=idx,
            raw_data=raw_dict
        )

        try:
            # Standardize column lookup
            def get_val(keys):
                for k in keys:
                    if k in headers_lower:
                        idx = headers_lower.index(k)
                        if idx < len(row):
                            return row[idx].strip()
                return None

            period_start = None
            period_end = None
            quantity = Decimal("0")
            unit = "kWh"
            cost = None
            meter_id = ""
            facility = ""
            warning_msg = ""

            if fmt == "UK":
                # Account Number, Meter ID, Period Start, Period End, kWh Consumed, Peak kWh, Off-Peak kWh, Tariff, Cost (GBP)
                start_str = get_val(["period start", "start date"])
                end_str = get_val(["period end", "end date"])
                if not start_str or not end_str:
                    raise ValueError("UK format requires 'Period Start' and 'Period End' dates.")
                period_start = parse_util_date(start_str)
                period_end = parse_util_date(end_str)

                # Total usage can be kWh Consumed, or sum of Peak + Off-Peak
                consumed_str = get_val(["kwh consumed", "consumed", "usage", "kwh"])
                peak_str = get_val(["peak kwh", "peak"])
                offpeak_str = get_val(["off-peak kwh", "off-peak", "offpeak"])

                if consumed_str:
                    quantity = Decimal(consumed_str.replace(',', ''))
                elif peak_str and offpeak_str:
                    quantity = Decimal(peak_str.replace(',', '')) + Decimal(offpeak_str.replace(',', ''))
                else:
                    raise ValueError("Cannot parse energy consumption from UK bill row.")

                cost_str = get_val(["cost", "cost (gbp)", "amount due"])
                if cost_str:
                    cost = Decimal(cost_str.replace('£', '').replace('$', '').replace(',', '').strip())

                meter_id = get_val(["meter id", "meter_id", "account number"]) or ""
                facility = get_val(["service address", "address", "meter id"]) or "UK Facility"

            else:
                # Format B (US-style): Service Address, Billing Period, Usage (kWh), Demand (kW), Rate Schedule, Amount Due ($)
                period_str = get_val(["billing period", "period", "date"])
                if not period_str:
                    raise ValueError("US format requires 'Billing Period' or 'Period'.")
                period_start, period_end = parse_billing_period(period_str)

                usage_str = get_val(["usage (kwh)", "usage", "kwh", "usage (mwh)"])
                if not usage_str:
                    raise ValueError("Usage column missing.")
                quantity = Decimal(usage_str.replace(',', ''))

                # Handle unit conversions
                unit_col = [h for h in headers if "usage" in h.lower()]
                if unit_col and "mwh" in unit_col[0].lower():
                    quantity = quantity * Decimal("1000.0")
                    unit = "kWh"
                elif unit_col and "therms" in unit_col[0].lower():
                    quantity = quantity * Decimal("29.3")
                    unit = "kWh"

                # Detect demand charges warning
                demand_str = get_val(["demand (kw)", "demand", "kw"])
                if demand_str and Decimal(demand_str.replace(',', '')) > 0:
                    warning_msg = f"Demand charges of {demand_str} kW were found and skipped as they do not represent energy consumption."

                cost_str = get_val(["amount due", "cost", "amount due ($)", "cost ($)"])
                if cost_str:
                    cost = Decimal(cost_str.replace('$', '').replace(',', '').strip())

                meter_id = get_val(["account number", "meter id"]) or ""
                facility = get_val(["service address", "address", "facility"]) or "US Facility"

            # 4. Proportional Split Logic
            splits = split_billing_period(period_start, period_end, quantity, cost)

            raw_str = json.dumps(raw_dict, sort_keys=True)
            source_hash = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

            if ActivityRecord.objects.filter(tenant=batch.tenant, source_hash=source_hash).exists():
                continue

            # Store warning message as a non-fatal parse_error warning
            if warning_msg:
                raw_row.parse_error = warning_msg
                raw_row.save()

            for s_idx, split in enumerate(splits):
                # OneToOne: only the first split links to raw_row; further splits share provenance via batch/hash
                record = ActivityRecord.objects.create(
                    tenant=batch.tenant,
                    raw_row=raw_row if s_idx == 0 else None,
                    batch=batch,
                    scope=2,
                    category="ELECTRICITY",
                    description=f"Electricity bill for meter {meter_id} at {facility} (split {split['start'].strftime('%b %Y')})",
                    activity_date=split["end"], # Use last day of split
                    period_start=split["start"],
                    period_end=split["end"],
                    facility_code=facility,
                    location=facility,
                    quantity=split["qty"].quantize(Decimal("0.000001")),
                    unit="kWh",
                    emission_factor=UTILITY_EF,
                    emission_factor_unit=UTILITY_EF_UNIT,
                    co2e_kg=(split["qty"] * UTILITY_EF).quantize(Decimal("0.0000")),
                    source_system="UTILITY_PORTAL_CSV",
                    source_row_id=f"{meter_id}_{period_start}_{s_idx}",
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
