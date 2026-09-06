import uuid
from django.db import models
from django.conf import settings
from apps.tenants.models import Tenant
from apps.emissions.models import ActivityRecord

class AuditLog(models.Model):
    objects = models.Manager()
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant         = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    activity_record= models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name="audit_logs")
    actor          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action         = models.CharField(max_length=50)      # APPROVED, FLAGGED, EDITED, LOCKED, etc.
    before_state   = models.JSONField(null=True, blank=True)
    after_state    = models.JSONField(null=True, blank=True)
    timestamp      = models.DateTimeField(auto_now_add=True)
    ip_address     = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"AuditLog {self.action} on {self.activity_record_id} at {self.timestamp}"
