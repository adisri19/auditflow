# AuditFlow Platform Refactoring: Implementation Report

## 1. Executive Summary & Verification Metrics

All 10 tasks from the master implementation plan and all 4 pre-implementation safety checks have been applied and verified.

- **Automated Tests**: 11 passed in 0.075s (`python manage.py test apps.tenants apps.ingestion apps.emissions apps.audit`).
- **Syntax & Compilation**: 0 errors across all Python modules.
- **OpenAPI 3.0 / Swagger**: Validated via `drf-spectacular` at `/api/schema/` and `/api/docs/`.
- **Database Concurrency**: Tested parallel atomic transitions with row-level locking (`select_for_update`) across multi-threaded workloads without integrity errors.

---

## 2. Pre-Implementation Safety Checks

| Safety Check | Master Prompt Requirement | Implementation & Resolution |
| :--- | :--- | :--- |
| **`select_related` Model Integrity** | Only include fields genuinely existing on `ActivityRecord`. Do not include non-existent fields. | Inspected `ActivityRecord`. Only genuine ForeignKeys (`batch` and `reviewed_by`) were chained into `.select_related('batch', 'reviewed_by')`. |
| **`IngestionBatch` Status Choices** | Do not add duplicate `COMPLETE` if `DONE` already exists; maintain consistency across models, migrations, frontend, and tasks. | Verified existing model choices had `("DONE", "Done")`, and the frontend actively checks against `DONE`. Preserved `DONE` consistently across model, Celery task, parsers, and test assertions. |
| **`RecordExportView` CSV Streaming** | Use `StreamingHttpResponse` with an `Echo` pseudo-buffer class and generator pattern. | Implemented `Echo.write(value)` returning `value` directly, chunked through `queryset.iterator(chunk_size=200)` into `StreamingHttpResponse(..., content_type='text/csv')`. |
| **Celery Retry Backoff** | Use exact retry syntax: `self.retry(exc=exc, countdown=2 ** self.request.retries, max_retries=2)`. | Implemented verbatim inside the `except Exception as exc:` block in `apps/ingestion/tasks.py`. |

---

## 3. Detailed Task Implementation

### TASK 1: Split `backend/apps/emissions/views.py` into a Package
- **Removed**: Deleted the monolithic `backend/apps/emissions/views.py`.
- **Created Package**: `backend/apps/emissions/views/`:
  - `records.py`: `RecordListCreateView`, `RecordDetailView`, `RecordBulkApproveView`, `RecordHistoryView`, `RecordExportView`.
  - `workflow.py`: `RecordApproveView`, `RecordFlagView`, `RecordRejectView`, `RecordLockView`.
  - `dashboard.py`: `DashboardSummaryView`, `DashboardTimelineView`.
  - `__init__.py`: Re-exports all views from `records`, `workflow`, and `dashboard` so existing URL routes remain unbroken.
- **Updated URLs**: Synchronized import bindings in `backend/breathe/urls.py`.

### TASK 2: Extract `_transition_record` and Rewrite Workflow Views
- **Shared Function**: `_transition_record(request, pk, new_status, action_label, valid_from_statuses=None)` in `workflow.py`:
  - Uses `ActivityRecord.objects.select_for_update().get(pk=pk, tenant=request.tenant)` inside `transaction.atomic()`.
  - Returns HTTP 404 if the record is not found for `request.tenant`.
  - Returns HTTP 400 if the record is `LOCKED` unless the target status is `LOCKED`.
  - Returns HTTP 400 if `valid_from_statuses` is provided and the current status is not in the list.
  - Returns HTTP 400 with `'co2e_kg must be set and greater than zero before locking'` if target status is `LOCKED` and `co2e_kg` is null or `<= 0`.
  - Saves `review_notes` from `request.data` if provided, updates `reviewed_by` and `reviewed_at`.
  - Invokes `log_action(request, record, action_label, before_state, after_state)` and returns serialized record data.
- **Rewritten Views**: `RecordApproveView`, `RecordFlagView`, `RecordRejectView`, and `RecordLockView` all invoke `_transition_record`.

### TASK 3: Add `select_related` to `RecordListCreateView`
- Updated `RecordListCreateView.get()` to execute:
  ```python
  queryset = (
      ActivityRecord.objects.filter(tenant=request.tenant)
      .order_by('-activity_date')
      .select_related('batch', 'reviewed_by')
  )
  ```
- Eliminates $N+1$ query overhead when serializing nested user and batch data.

### TASK 4: Custom DRF Pagination (`RecordPagination`)
- **Created**: `backend/apps/emissions/pagination.py`:
  - Extends `PageNumberPagination`.
  - Configured `page_size = 20`, `page_size_query_param = 'page_size'`, `max_page_size = 100`.
  - Returns pagination contract: `results`, `count`, `num_pages`, `current_page`, `has_next`, `has_previous`.
- **Integrated**: Replaced manual `django.core.paginator.Paginator` logic in `RecordListCreateView` with `pagination_class = RecordPagination`.

### TASK 5: High-Performance Emissions Timeline Query
- Refactored `DashboardTimelineView` in `dashboard.py`:
  - Replaced the Python row iteration loop with a single database aggregation:
    ```python
    timeline = (
        ActivityRecord.objects.filter(tenant=request.tenant)
        .annotate(month=TruncMonth('activity_date'))
        .values('month', 'scope')
        .annotate(total_co2e=Sum('co2e_kg'))
        .order_by('month')
    )
    ```
  - Reshapes data into `[{'month': 'YYYY-MM', 'scope1': float, 'scope2': float, 'scope3': float}, ...]` in metric tonnes (`tCO2e = total_co2e / 1000.0`).

### TASK 6: Comprehensive Automated Test Suite
- Updated `backend/apps/emissions/tests.py` with all 6 required test scenarios:
  1. `test_unknown_iata_code_sets_parse_error`: Unknown airport codes trigger Haversine fallback errors saved to `RawRow.parse_error`.
  2. `test_sap_invalid_unit_sets_parse_error`: Invalid units in SAP flat files flag `RawRow.parse_error = "Unsupported unit: ..."`.
  3. `test_billing_period_proration_splits_correctly`: Cross-month utility bills split quantities and costs proportionally by day count.
  4. `test_duplicate_source_hash_not_double_ingested`: Re-uploading identical rows skips duplicate `ActivityRecord` creation.
  5. `test_lock_rejected_without_co2e`: Locking an approved record with `co2e_kg=None` returns HTTP 400 with expected error message.
  6. `test_concurrent_approve_race_condition`: Parallel approval requests via `threading.Thread` execute without raising database integrity errors.

### TASK 7: Asynchronous Celery Ingestion Pipeline
- **Celery Config**: Created `backend/breathe/celery.py` and updated `backend/breathe/__init__.py` to expose `celery_app`.
- **Worker Task**: Created `backend/apps/ingestion/tasks.py` containing `parse_ingestion_batch(batch_id)`:
  - Sets batch status `PROCESSING` on start.
  - Sets batch status `DONE` on success.
  - Sets batch status `FAILED` and persists `error_message` on unhandled exception.
  - Implements exponential backoff: `self.retry(exc=exc, countdown=2 ** self.request.retries, max_retries=2)`.
- **Model & Migration**: Added `error_message = models.TextField(blank=True, default='')` to `IngestionBatch` and applied migration `0003_ingestionbatch_error_message.py`.
- **Async Dispatch**: Updated `BatchListCreateView.post()` to call `parse_ingestion_batch.delay(str(batch.id))`.
- **Deduplication Check**: Added `if ActivityRecord.objects.filter(tenant=batch.tenant, source_hash=source_hash).exists(): continue` across `sap.py`, `travel.py`, and `utility.py`.
- **Docker Compose**: Added `redis:7-alpine` and `celery` worker service definitions to `docker-compose.yml`.
- **Environment Settings**: Added `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to `base.py`.

### TASK 8: Audit CSV Streaming Engine (`RecordExportView`)
- Added `RecordExportView` to `backend/apps/emissions/views/records.py`:
  - Implements `Echo` buffer with generator streaming chunks of 200 records.
  - Accepts all filters (`status`, `scope`, `source_type`, `batch_id`, `date_from`, `date_to`, `search`).
  - Defaults `status` filter to `LOCKED` when omitted.
  - Sets header `Content-Disposition: attachment; filename="auditflow_export_{timestamp}.csv"`.
  - Outputs all 18 columns in order: `id`, `activity_date`, `scope`, `category`, `description`, `quantity`, `unit`, `co2e_kg`, `emission_factor`, `source_system`, `source_row_id`, `facility_code`, `location`, `review_status`, `reviewed_by`, `reviewed_at`, `batch_id`, `is_edited`.
- Routed in `backend/breathe/urls.py` at `records/export/` before `records/<uuid:pk>/`.

### TASK 9: OpenAPI Schema & Swagger UI via `drf-spectacular`
- Added `drf-spectacular` to `backend/requirements.txt`.
- Added `'drf_spectacular'` to `INSTALLED_APPS` and set `'DEFAULT_SCHEMA_CLASS'` in `base.py`.
- Configured `SPECTACULAR_SETTINGS` with platform metadata.
- Annotated every endpoint across `records.py`, `workflow.py`, `dashboard.py`, and `ingestion/views.py` using `@extend_schema` documenting parameters, request bodies, and responses (200/201, 400, 404).
- Added `/api/schema/` and `/api/docs/` to `backend/breathe/urls.py`.

### TASK 10: Production Database Reliability & Middleware
- **Settings**: Updated `backend/breathe/settings/production.py`:
  - Set `CONN_MAX_AGE = 0` on `DATABASES['default']` to prevent idle connection termination issues with serverless PostgreSQL poolers.
  - Added `OPTIONS` with `connect_timeout: 10` and `-c statement_timeout=30000`.
- **Middleware**: Created `backend/breathe/middleware.py` with `DatabaseHealthMiddleware`:
  - Intercepts `django.db.OperationalError`.
  - Logs errors via `logger.error(..., exc_info=True)`.
  - Returns HTTP 503 JSON: `{"detail": "Database temporarily unavailable please retry"}`.
- **Registration**: Registered `DatabaseHealthMiddleware` in `MIDDLEWARE` in `production.py` directly before `django.middleware.common.CommonMiddleware`.

---

## 4. File Index

```
backend/
├── apps/
│   ├── emissions/
│   │   ├── pagination.py                            [NEW]
│   │   ├── tests.py                                 [UPDATED]
│   │   └── views/                                   [NEW PACKAGE]
│   │       ├── __init__.py                          [NEW]
│   │       ├── dashboard.py                         [NEW]
│   │       ├── records.py                           [NEW]
│   │       └── workflow.py                          [NEW]
│   └── ingestion/
│       ├── migrations/
│       │   └── 0003_ingestionbatch_error_message.py [NEW]
│       ├── models.py                                [UPDATED]
│       ├── parsers/
│       │   ├── sap.py                               [UPDATED]
│       │   ├── travel.py                            [UPDATED]
│       │   └── utility.py                           [UPDATED]
│       ├── tasks.py                                 [NEW]
│       └── views.py                                 [UPDATED]
├── breathe/
│   ├── __init__.py                                  [UPDATED]
│   ├── celery.py                                    [NEW]
│   ├── middleware.py                                [NEW]
│   ├── settings/
│   │   ├── base.py                                  [UPDATED]
│   │   └── production.py                            [UPDATED]
│   └── urls.py                                      [UPDATED]
├── docker-compose.yml                               [UPDATED]
└── requirements.txt                                 [UPDATED]
```
