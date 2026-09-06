# Data model — BREATHE ESG

## UUID primary keys

Every entity uses a UUID primary key rather than sequential integers. This avoids cross-tenant enumeration attacks (guessing `/records/42` on another client) and makes merging data from multiple ingestion batches safe when records are created in parallel workers.

## Multi-tenancy

`Tenant` is the isolation boundary. Every operational table (`IngestionBatch`, `RawRow`, `ActivityRecord`, `AuditLog`) carries a `tenant` foreign key.

The custom `User` model also references `Tenant`. `TenantMiddleware` reads the authenticated user's tenant and scopes queryset filtering in API views so analysts never see another client's data.

Production can extend this with a JWT `tenant_id` claim; session auth in the prototype binds tenant to the logged-in user.

## Ingestion → normalisation pipeline

```
Upload file → IngestionBatch → RawRow (verbatim JSON) → ActivityRecord (canonical)
```

- **IngestionBatch** — one upload event, tracks `source_type`, `status`, `row_count`, `error_count`.
- **RawRow** — immutable capture of the source row. `parse_error` is set when normalisation fails; the row is never discarded.
- **ActivityRecord** — what auditors review: scope, category, normalised quantity/unit, optional `co2e_kg`, review status.

`ActivityRecord.raw_row` is a optional `OneToOne` to the originating `RawRow`. When a utility bill is split across calendar months, only the first split retains the `raw_row` link; siblings share `batch` and `source_hash` provenance.

## Scope 1 / 2 / 3 assignment

| Source | Logic |
|--------|--------|
| SAP | Material prefix → fuel (`DIESEL`, `LPG`, …) = Scope 1 `FUEL_COMBUSTION`; procurement prefixes (`STEEL`, `PAPER`, …) = Scope 3 `PROCUREMENT` |
| Utility | Always Scope 2 `ELECTRICITY` |
| Travel | `FLIGHT` / `HOTEL` / `CAR`/`RAIL` → Scope 3 travel categories |

Parsers assign scope at ingest time. Analysts may flag rows where categorisation looks wrong; they do not re-assign scope in the prototype PATCH API.

## Source-of-truth & deduplication

- `source_system` — e.g. `SAP`, `UTILITY_PORTAL_CSV`, `NAVAN_CSV`
- `source_row_id` — vendor reference (trip ID, meter + period, SAP material line)
- `source_hash` — SHA-256 of sorted `raw_data` JSON for duplicate detection
- `is_edited` — set `True` when an analyst PATCHes quantity, unit, or emission fields

## Unit normalisation

Canonical units: **kWh** (energy), **L** / **kg** / **t** (mass/volume), **km** (distance).

SAP and utility parsers apply explicit conversion factors (documented in code comments, e.g. 1 US gallon = 3.78541 L, 1 MWh = 1000 kWh, 1 therm ≈ 29.3 kWh). Travel uses Haversine distance when the CSV omits km.

`pint` is listed in `requirements.txt` for future EF/unit work; current parsers use `Decimal` arithmetic to avoid float drift.

## Review workflow states

```
PENDING → APPROVED | FLAGGED | REJECTED
APPROVED → LOCKED (audit-ready, immutable)
```

- **PATCH** allowed fields: `quantity`, `unit`, `review_notes`, `emission_factor`, `co2e_kg` — writes an `AuditLog` with action `EDITED`.
- **approve / flag / reject** — dedicated POST endpoints; each appends `AuditLog`.
- **lock** — only from `APPROVED`.

## Audit trail

`AuditLog` is append-only: no updates, no deletes in application code. Each entry stores `actor`, `action`, `before_state`, `after_state`, `timestamp`, optional `ip_address`.

## LOCKED immutability

`ActivityRecord.save()` compares all fields against the DB copy when `status == LOCKED` and raises `ValidationError` on any change. API views return 400 for PATCH and workflow actions on locked rows. The UI disables edit controls when `LOCKED`.
