# Design decisions — BREATHE ESG

## SAP: flat file, not OData or IDoc XML

**Choice:** Tab-delimited `.txt`, semicolon `.csv`, or `.xlsx` exports from SAP ALV / SE16-style downloads.

**Why:** OData requires SAP Gateway configuration, client certificates, and version-specific service metadata. IDoc XML is batch-integration infrastructure, not what sustainability analysts receive during onboarding. Flat files are what finance/procurement teams email today.

**Column mapping:** German SAP headers (`WERKS`, `BLDAT`, `MENGE`, `MEINS`) plus English ALV aliases. Dates accept `YYYYMMDD` and `DD.MM.YYYY`.

**Scope from material numbers:** Prefix lists (`DIESEL`, `LPG` → Scope 1; `STEEL`, `PAPER` → Scope 3). Invalid units (e.g. `PCS` for pieces) fail normalisation with a `parse_error` on the `RawRow`.

## Utility: CSV portal export, not PDF or utility API

**Choice:** UK-style (meter ID + period start/end + kWh) and US-style (billing period string + usage, optional MWh).

**Why:** PDF bill parsing breaks on layout changes. Utility APIs need per-vendor OAuth (PG&E ≠ National Grid ≠ Enel). CSV export is the universal admin fallback.

**Billing periods spanning months:** Stored as `period_start` / `period_end` on each split `ActivityRecord`; quantity and cost allocated by day count. We do **not** force a single `activity_date` to represent a straddling bill.

**Demand charges (kW):** Logged as a non-fatal warning on `RawRow.parse_error`; not converted to kWh.

**Units:** MWh × 1000 → kWh; therms × 29.3 → kWh (EPA-style approximation, commented in parser).

## Travel: Navan/Concur CSV export, not live API

**Choice:** Admin bulk-export CSV with segment type, IATA codes, optional distance and carbon column.

**Why:** Concur API needs SAP partnership credentials; Navan API is limited/beta. CSV is available to any travel admin.

**Missing distance:** Haversine great-circle km from embedded IATA coordinate table (~50 airports). Unknown IATA (`XYZ`) → parse failure with clear `parse_error`.

**Emission factors (prototype):** FLIGHT class factors (kg CO₂e / passenger-km), hotel nights × 31.2 kg, ground CAR/RAIL per km — documented constants, not a full DEFRA library.

## API & auth

Session + JWT (`djangorestframework-simplejwt`) for SPA login. Tenant scoping via user FK, not a separate tenant header in the prototype.

## Questions for product (PM)

1. Which SAP `WERKS` plant codes map to which legal entity / facility name in client reports?
2. Should we apply client-supplied emission factors or Breathe's default library?
3. Should `LOCKED` records export as auditor CSV/Excel bundles?
4. Is proportional utility split per month sufficient, or do clients need calendar-month reporting only?
