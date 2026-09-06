from rest_framework import serializers
from apps.audit.models import AuditLog
from apps.tenants.serializers import UserSerializer

class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'tenant', 'activity_record', 'actor', 'action', 'before_state', 'after_state', 'timestamp', 'ip_address']
