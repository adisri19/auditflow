# Data sources — research & sample rationale

## SAP fuel & procurement

### Real-world format

SAP MM/FI users export movement or purchase data from ALV grids: tab-delimited text or Excel with columns `WERKS` (plant), `BLDAT` (posting date), `MENGE` / `MEINS` (quantity/UoM), `MATNR`, `BKTXT`. German installations often retain German headers.

### Surprising facts

- The same material can appear in **litres** and **US gallons** depending on vendor country; normalisation is mandatory before any tCO₂e rollup.
- `PCS` (pieces) is valid in SAP but meaningless for emissions — good test of per-row failure handling.
- Procurement steel/paper lines are Scope 3 spend-based proxies, not combustion — material number prefix is a crude but practical classifier without a full spend-category mapping table.

### Sample data (`seed_demo_data` / `raw/sap_demo.txt`)

20 rows across plants `IN01` / `IN02`, mixed date formats, gallon rows, one `PCS` failure, diesel/LPG/steel/paper mix.

### What breaks in production

- Custom Z-fields and client-specific column names not in `SAP_COLUMN_MAP`
- Multi-line POs collapsed incorrectly in exports
- OData would be needed for daily automation at scale

---

## Utility electricity

### Real-world format

Facility teams download **CSV** from utility portals (UK: account + meter + period boundaries; US: service address + combined billing period + usage, sometimes **MWh** or demand **kW**).

### Surprising facts

- Billing periods rarely align to calendar months (e.g. 15 Jan – 14 Feb) — reporting tools that only accept `activity_date` mis-state February emissions.
- **Demand (kW)** is a capacity charge, not energy; including it would double-count infrastructure incorrectly.
- Missing meter ID still occurs on consolidated bills — we still ingest with a warning.

### Sample data

UK CSV: 6 monthly rows, straddling periods. US CSV: MWh column, missing service address on one row.

### What breaks in production

- PDF-only utilities without CSV
- Time-of-use tariffs needing separate peak/off-peak EF
- Multiple currencies and VAT lines in cost column

---

## Corporate travel

### Real-world format

Navan / Concur admin exports: trip ID, segment type (`FLIGHT`, `HOTEL`, `CAR`, `RAIL`), IATA codes, optional distance and supplier-provided carbon.

### Surprising facts

- Distance is often blank for flights — IATA Haversine is a fallback, not a substitute for airline-reported great-circle + routing factors.
- Unknown airport codes fail gracefully rather than inventing zero km.
- Hotel stays use **nights** not km; ground rail vs car use different EF per km.

### Sample data

15 rows: BOM→LHR, DEL→JFK, haversine-only rows, `XYZ` failure, hotels and car segments.

### What breaks in production

- Multi-city open-jaw itineraries (single row, complex distance)
- Private aviation and rail outside European EF averages
- Concur API would remove manual export but needs enterprise contract
