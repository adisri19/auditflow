from rest_framework import serializers
from apps.emissions.models import ActivityRecord
from apps.tenants.serializers import UserSerializer
from apps.ingestion.serializers import IngestionBatchSerializer

class ActivityRecordSerializer(serializers.ModelSerializer):
    reviewed_by = UserSerializer(read_only=True)
    batch = IngestionBatchSerializer(read_only=True)

    class Meta:
        model = ActivityRecord
        fields = '__all__'
        read_only_fields = [
            'id', 'tenant', 'raw_row', 'batch', 'scope', 'category', 'description',
            'activity_date', 'period_start', 'period_end', 'facility_code', 'location',
            'source_system', 'source_row_id', 'source_hash', 'status', 'reviewed_by',
            'reviewed_at', 'created_at', 'updated_at', 'is_edited'
        ]
