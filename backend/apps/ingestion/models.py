import uuid
from django.db import models
from django.conf import settings
from apps.tenants.models import Tenant

class IngestionBatch(models.Model):
    objects = models.Manager()
    DoesNotExist: type[Exception]
    SOURCE_TYPES = [
        ("SAP_FUEL_PROC", "SAP Fuel & Procurement"),
        ("UTILITY_ELEC",  "Utility Electricity"),
        ("CORP_TRAVEL",   "Corporate Travel"),
    ]
    STATUS = [
        ("PENDING",    "Pending"),
        ("PROCESSING", "Processing"),
        ("DONE",       "Done"),
        ("FAILED",     "Failed"),
    ]
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant       = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source_type  = models.CharField(max_length=30, choices=SOURCE_TYPES)
    status       = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    raw_file     = models.FileField(upload_to="raw/", null=True, blank=True)
    ingested_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ingested_at  = models.DateTimeField(auto_now_add=True)
    row_count    = models.IntegerField(default=0)
    error_count  = models.IntegerField(default=0)
    notes        = models.TextField(blank=True)
    error_message= models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.source_type} Batch ({self.id}) - {self.status}"

class RawRow(models.Model):
    objects = models.Manager()
    DoesNotExist: type[Exception]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch      = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="raw_rows")
    tenant     = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    row_index  = models.IntegerField()               # position in source file
    raw_data   = models.JSONField()                  # verbatim parsed row
    parse_error= models.TextField(blank=True)        # non-empty = failed to normalise
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RawRow {self.row_index} for Batch {self.batch_id}"
