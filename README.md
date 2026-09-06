# AuditFlow

A full-stack emissions data ingestion and audit platform. Ingests activity data from multiple enterprise source systems, normalises it into a unified carbon accounting model, and gives analysts a review workflow before records are locked for audit.

**Live:** https://auditflow-frontend-42gf.onrender.com  
**API:** https://auditflow-backend-fmds.onrender.com  
**Login:** `admin@demo.com` / `breathe2024`

---

## What it does

Enterprise emissions data is messy. SAP exports have German column headers and inconsistent units. Utility bills have billing periods that don't align with calendar months. Travel platforms give you airport codes instead of distances. AuditFlow handles all of it — ingesting raw files from three source types, normalising every row into a canonical model, and routing them through an analyst review workflow before they are locked for audit.

---

## Pipeline

```
Raw File Upload
      │
      ▼
┌─────────────────┐
│  IngestionBatch │  ← one per upload, tracks source type + status
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Parser       │  ← source-specific: SAP / Utility / Travel
│                 │
│  - maps columns │
│  - converts units│
│  - detects scope│
└────────┬────────┘
         │
         ├──── success ────────────────────────┐
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌──────────────────┐
│    RawRow       │                  │  ActivityRecord  │
│  (verbatim,     │                  │  (normalised,    │
│   never lost)   │                  │   scope-tagged,  │
└─────────────────┘                  │   unit-canonical)│
         │                           └────────┬─────────┘
         │ parse_error ≠ ""                    │
         ▼                                     ▼
   Shown in dashboard            ┌─────────────────────────┐
   as "Failed rows"              │   Review Workflow        │
                                 │                          │
                                 │  PENDING                 │
                                 │     │                    │
                                 │  APPROVED / FLAGGED /    │
                                 │  REJECTED                │
                                 │     │                    │
                                 │   LOCKED  ← audit-ready │
                                 └─────────────────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │      AuditLog            │
                                 │  (immutable, append-only)│
                                 │  every status change     │
                                 │  recorded with actor +   │
                                 │  timestamp               │
                                 └─────────────────────────┘
```

**Three ingestion pipelines:**

- **SAP flat file** — tab/semicolon delimited exports from SAP MM/FI modules. Handles German column headers (WERKS, BLDAT, MENGE, MEINS), multiple date formats, unit conversion (GAL→L, MWH→kWh), and material-number-based scope classification (fuel = Scope 1, procurement = Scope 3)
- **Utility electricity CSV** — portal exports from utility providers. Handles billing periods that straddle month boundaries, unit normalisation to kWh, multi-meter accounts, and demand charge detection (kW rows are skipped with a parse note)
- **Corporate travel CSV** — Navan/Concur bulk exports. Handles flights, hotels, and ground transport. Computes great-circle distances via Haversine when not provided, applies ICAO emission factors by cabin class (Economy 0.255, Business 0.614, First 0.851 kgCO2e/km)

---

## Stack

- **Backend** — Django 5, Django REST Framework, PostgreSQL
- **Frontend** — React 18, Vite, Tailwind CSS, TanStack Query
- **Deployment** — Render (static site + web service + managed Postgres)

---

## Local setup

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000, API on http://localhost:8000/api/v1/

### Docker
```bash
cp .env.example .env
docker compose up --build
```

---

## Data model

See [MODEL.md](./MODEL.md) for full schema documentation covering multi-tenancy, Scope 1/2/3 categorisation, source-of-truth provenance tracking, unit normalisation, and audit trail immutability.

---

## Docs

| File | Contents |
|------|----------|
| [MODEL.md](./MODEL.md) | Schema design and rationale |
| [DECISIONS.md](./DECISIONS.md) | Format choices and ambiguity resolutions |
| [TRADEOFFS.md](./TRADEOFFS.md) | Deliberate scope cuts |
| [SOURCES.md](./SOURCES.md) | Real-world format research per source |