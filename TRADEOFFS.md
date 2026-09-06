# Tradeoffs — deliberate non-builds

## 1. Real-time SAP OData pull

**Not built:** Scheduled or on-demand OData ingestion from SAP S/4 or ECC.

**Reason:** Requires SAP Basis to activate OData services, issue credentials, and maintain entity sets that differ by SAP version and customising. For a four-day onboarding prototype, file upload covers the typical analyst workflow (monthly SE16 extract).

**Cost:** Data is stale until someone uploads. Acceptable for MVP; production would add OData behind a feature flag per tenant.

## 2. Emission factor library

**Not built:** Versioned DEFRA / EPA / IPCC lookup tables with automatic EF selection by geography and year.

**Reason:** EF choice is a product and legal decision (market-based vs location-based grid factors, biogenic carbon, GWP version). The model stores `emission_factor`, `emission_factor_unit`, and `co2e_kg` per row so clients can supply their own factors later.

**Cost:** Parsers use simple default constants for travel and a flat grid factor for utility demo data. Analysts can override on PATCH.

## 3. Multi-user concurrent review locking

**Not built:** Optimistic locking (version field) or row-level locks when two analysts approve the same record.

**Reason:** Celery + `select_for_update` or HTMX polling adds operational complexity (Redis, worker processes) beyond prototype scope.

**Cost:** Last write wins on concurrent PATCH; rare in small audit teams but must be addressed before enterprise rollout.

---

### Additional minor tradeoffs

| Area | Choice | Sacrifice |
|------|--------|-----------|
| PDF utility bills | Listed in requirements, not implemented | Manual CSV step for analysts |
| Celery async parsing | Dependency present, sync parse in request | Large files block upload request |
| `pint` | In requirements, manual `Decimal` conversions in parsers | Less extensible unit grammar |
