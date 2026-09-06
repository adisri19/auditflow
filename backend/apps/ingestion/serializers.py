from rest_framework import serializers
from apps.ingestion.models import IngestionBatch, RawRow
from apps.tenants.serializers import UserSerializer

class IngestionBatchSerializer(serializers.ModelSerializer):
    ingested_by = UserSerializer(read_only=True)
    
    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'tenant', 'source_type', 'status', 'raw_file', 
            'ingested_by', 'ingested_at', 'row_count', 'error_count', 'notes'
        ]
        read_only_fields = ['id', 'tenant', 'status', 'ingested_by', 'ingested_at', 'row_count', 'error_count']

class RawRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRow
        fields = ['id', 'batch', 'tenant', 'row_index', 'raw_data', 'parse_error', 'created_at']
