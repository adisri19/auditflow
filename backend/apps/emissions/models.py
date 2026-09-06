import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.tenants.models import Tenant
from apps.ingestion.models import RawRow, IngestionBatch

class ActivityRecord(models.Model):
    objects = models.Manager()
    DoesNotExist: type[Exception]
    SCOPE_CHOICES = [
        (1, "Scope 1"),
        (2, "Scope 2"),
        (3, "Scope 3"),
    ]
    STATUS_CHOICES = [
        ("PENDING",   "Pending review"),
        ("APPROVED",  "Approved"),
        ("FLAGGED",   "Flagged"),
        ("REJECTED",  "Rejected"),
        ("LOCKED",    "Locked for audit"),
    ]
    CATEGORY_CHOICES = [
        # Scope 1
        ("FUEL_COMBUSTION",   "Fuel combustion"),
        ("PROCESS_EMISSIONS", "Process emissions"),
        # Scope 2
        ("ELECTRICITY",       "Purchased electricity"),
        # Scope 3
        ("BUSINESS_TRAVEL_FLIGHT",  "Business travel – flight"),
        ("BUSINESS_TRAVEL_HOTEL",   "Business travel – hotel"),
        ("BUSINESS_TRAVEL_GROUND",  "Business travel – ground transport"),
        ("PROCUREMENT",             "Purchased goods & services"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant          = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    raw_row         = models.OneToOneField(RawRow, on_delete=models.SET_NULL, null=True, blank=True)
    batch           = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="activity_records")

    # What it is
    scope           = models.IntegerField(choices=SCOPE_CHOICES)
    category        = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    description     = models.CharField(max_length=500, blank=True)

    # When & where
    activity_date   = models.DateField()
    period_start    = models.DateField(null=True, blank=True)  # for utility bills
    period_end      = models.DateField(null=True, blank=True)
    facility_code   = models.CharField(max_length=100, blank=True)  # SAP plant code
    location        = models.CharField(max_length=255, blank=True)

    # The number (always normalised)
    quantity        = models.DecimalField(max_digits=18, decimal_places=6)
    unit            = models.CharField(max_length=30)   # always SI or agreed canonical (kWh, kg, km)

    # Emission factor (optional, analyst can fill in)
    emission_factor      = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    emission_factor_unit = models.CharField(max_length=50, blank=True)   # e.g. kgCO2e/kWh
    co2e_kg              = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    # Source-of-truth provenance
    source_system   = models.CharField(max_length=100)  # "SAP", "UTILITY_PORTAL_CSV", "NAVAN_API"
    source_row_id   = models.CharField(max_length=255, blank=True)  # original PK/ref from source
    source_hash     = models.CharField(max_length=64, blank=True)   # SHA-256 of raw_data for dedup

    # Review workflow
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    review_notes    = models.TextField(blank=True)
    reviewed_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="reviewed_records")
    reviewed_at     = models.DateTimeField(null=True, blank=True)

    # Audit trail
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    is_edited       = models.BooleanField(default=False)  # True if analyst changed quantity/unit

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "scope"]),
            models.Index(fields=["tenant", "activity_date"]),
            models.Index(fields=["source_hash"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = ActivityRecord.objects.get(pk=self.pk)
                if original.status == 'LOCKED':
                    # Check if any field changed
                    for field in self._meta.fields:
                        if getattr(self, field.attname) != getattr(original, field.attname):
                            raise ValidationError("Cannot modify a locked activity record.")
            except ActivityRecord.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} ({self.quantity} {self.unit}) - {self.status}"
