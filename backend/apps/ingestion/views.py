from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from .models import IngestionBatch, RawRow
from .serializers import IngestionBatchSerializer, RawRowSerializer
from .tasks import parse_ingestion_batch

class BatchListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List ingestion batches",
        description="Retrieve all ingestion batches for the current tenant ordered by ingestion date descending.",
        responses={
            200: IngestionBatchSerializer(many=True),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Tenant not found"),
        }
    )
    def get(self, request):
        batches = IngestionBatch.objects.filter(tenant=request.tenant).order_by('-ingested_at')
        return Response(IngestionBatchSerializer(batches, many=True).data)

    @extend_schema(
        summary="Create ingestion batch",
        description="Upload a source file (SAP, Utility, or Travel) to create a new ingestion batch and dispatch asynchronous Celery parsing.",
        request=inline_serializer(
            name="BatchCreateRequest",
            fields={
                "source_type": serializers.ChoiceField(choices=IngestionBatch.SOURCE_TYPES),
                "raw_file": serializers.FileField(),
                "notes": serializers.CharField(required=False, allow_blank=True),
            }
        ),
        responses={
            201: IngestionBatchSerializer,
            400: OpenApiResponse(description="Validation error or missing required fields"),
            404: OpenApiResponse(description="Tenant not found"),
        }
    )
    def post(self, request):
        source_type = request.data.get('source_type')
        notes = request.data.get('notes', '')
        file_obj = request.FILES.get('raw_file')

        if not source_type or not file_obj:
            return Response(
                {'detail': 'source_type and raw_file are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch = IngestionBatch.objects.create(
            tenant=request.tenant,
            source_type=source_type,
            status="PENDING",
            ingested_by=request.user,
            raw_file=file_obj,
            notes=notes
        )

        parse_ingestion_batch.delay(str(batch.id))  # type: ignore

        return Response(IngestionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class BatchDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Retrieve ingestion batch detail",
        description="Retrieve status, metadata, row counts, and error metrics for a specific ingestion batch.",
        responses={
            200: IngestionBatchSerializer,
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Batch not found"),
        }
    )
    def get(self, request, pk):
        try:
            batch = IngestionBatch.objects.get(pk=pk, tenant=request.tenant)
        except IngestionBatch.DoesNotExist:
            return Response({'detail': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(IngestionBatchSerializer(batch).data)


class BatchRawRowsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List raw rows for batch",
        description="Retrieve verbatim raw parsed rows and normalization errors for a specific ingestion batch.",
        responses={
            200: RawRowSerializer(many=True),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Batch not found"),
        }
    )
    def get(self, request, pk):
        try:
            batch = IngestionBatch.objects.get(pk=pk, tenant=request.tenant)
        except IngestionBatch.DoesNotExist:
            return Response({'detail': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

        rows = RawRow.objects.filter(batch=batch, tenant=request.tenant).order_by('row_index')
        return Response(RawRowSerializer(rows, many=True).data)
