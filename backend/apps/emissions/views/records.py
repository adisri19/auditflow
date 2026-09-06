import csv
from decimal import Decimal
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, inline_serializer

from apps.emissions.models import ActivityRecord
from apps.emissions.serializers import ActivityRecordSerializer
from apps.emissions.pagination import RecordPagination
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.audit.utils import log_action

class Echo:
    """An object that implements just the write method of the file-like interface."""
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value

class RecordListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RecordPagination

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    @extend_schema(
        summary="List activity records",
        description="Retrieve a paginated list of emissions activity records for the current tenant with optional filtering by status, scope, source type, batch, date range, or search query.",
        parameters=[
            OpenApiParameter(name='status', type=str, description='Filter by review status (PENDING, APPROVED, FLAGGED, REJECTED, LOCKED)'),
            OpenApiParameter(name='scope', type=int, description='Filter by GHG scope (1, 2, 3)'),
            OpenApiParameter(name='source_type', type=str, description='Filter by batch source type'),
            OpenApiParameter(name='batch_id', type=str, description='Filter by batch UUID'),
            OpenApiParameter(name='date_from', type=str, description='Filter by activity date >= YYYY-MM-DD'),
            OpenApiParameter(name='date_to', type=str, description='Filter by activity date <= YYYY-MM-DD'),
            OpenApiParameter(name='search', type=str, description='Search across description, facility code, location, or source row ID'),
            OpenApiParameter(name='page', type=int, description='Page number'),
            OpenApiParameter(name='page_size', type=int, description='Number of records per page (default 20, max 100)'),
        ],
        responses={
            200: ActivityRecordSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter or pagination parameters"),
            404: OpenApiResponse(description="Tenant or resource not found"),
        }
    )
    def get(self, request):
        queryset = (
            ActivityRecord.objects.filter(tenant=request.tenant)
            .order_by('-activity_date')
            .select_related('batch', 'reviewed_by')
        )

        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        scope_param = request.query_params.get('scope')
        if scope_param:
            queryset = queryset.filter(scope=scope_param)

        source_type_param = request.query_params.get('source_type')
        if source_type_param:
            queryset = queryset.filter(batch__source_type=source_type_param)

        batch_id = request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(activity_date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(activity_date__lte=date_to)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(facility_code__icontains=search) |
                Q(location__icontains=search) |
                Q(source_row_id__icontains=search)
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ActivityRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ActivityRecordSerializer(queryset, many=True)
        return Response(serializer.data)


class RecordDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Retrieve activity record detail",
        description="Retrieve full details of a specific activity record belonging to the authenticated tenant.",
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def get(self, request, pk):
        try:
            record = ActivityRecord.objects.select_related('batch', 'reviewed_by').get(pk=pk, tenant=request.tenant)
        except ActivityRecord.DoesNotExist:
            return Response({'detail': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(ActivityRecordSerializer(record).data)

    @extend_schema(
        summary="Edit activity record",
        description="Modify editable fields (quantity, unit, emission factor, co2e, review notes) on an unlocked record.",
        request=inline_serializer(
            name="RecordUpdateRequest",
            fields={
                "quantity": serializers.DecimalField(max_digits=18, decimal_places=6, required=False),
                "unit": serializers.CharField(max_length=30, required=False),
                "emission_factor": serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True),
                "co2e_kg": serializers.DecimalField(max_digits=18, decimal_places=4, required=False, allow_null=True),
                "review_notes": serializers.CharField(required=False, allow_blank=True),
            }
        ),
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Validation error or cannot edit locked record"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def patch(self, request, pk):
        try:
            record = ActivityRecord.objects.get(pk=pk, tenant=request.tenant)
        except ActivityRecord.DoesNotExist:
            return Response({'detail': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

        if record.status == 'LOCKED':
            return Response({'detail': 'Cannot edit a locked record.'}, status=status.HTTP_400_BAD_REQUEST)

        before_state = {
            "quantity": str(record.quantity),
            "unit": record.unit,
            "emission_factor": str(record.emission_factor) if record.emission_factor else None,
            "co2e_kg": str(record.co2e_kg) if record.co2e_kg else None,
            "review_notes": record.review_notes
        }

        quantity = request.data.get('quantity')
        unit = request.data.get('unit')
        ef = request.data.get('emission_factor')
        co2e = request.data.get('co2e_kg')
        review_notes = request.data.get('review_notes')

        modified = False

        if quantity is not None:
            record.quantity = Decimal(str(quantity))
            modified = True
        if unit is not None:
            record.unit = str(unit)
            modified = True
        if ef is not None:
            record.emission_factor = Decimal(str(ef)) if ef != "" else None
            modified = True
        if co2e is not None:
            record.co2e_kg = Decimal(str(co2e)) if co2e != "" else None
            modified = True
        else:
            if modified and record.quantity is not None and record.emission_factor is not None:
                record.co2e_kg = record.quantity * record.emission_factor

        if review_notes is not None:
            record.review_notes = str(review_notes)
            modified = True

        if modified:
            record.is_edited = True
            try:
                record.save()
            except ValidationError as ve:
                return Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

            after_state = {
                "quantity": str(record.quantity),
                "unit": record.unit,
                "emission_factor": str(record.emission_factor) if record.emission_factor else None,
                "co2e_kg": str(record.co2e_kg) if record.co2e_kg else None,
                "review_notes": record.review_notes
            }
            log_action(request, record, "EDITED", before_state=before_state, after_state=after_state)

        return Response(ActivityRecordSerializer(record).data)


class RecordBulkApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Bulk approve activity records",
        description="Approve multiple activity records at once by ID list.",
        request=inline_serializer(
            name="RecordBulkApproveRequest",
            fields={"ids": serializers.ListField(child=serializers.UUIDField())}
        ),
        responses={
            200: OpenApiResponse(description="Success count details"),
            400: OpenApiResponse(description="No record IDs provided or invalid data"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'detail': 'No record IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)

        records = ActivityRecord.objects.filter(id__in=ids, tenant=request.tenant)
        updated_count = 0

        for r in records:
            if r.status not in ('PENDING', 'FLAGGED', 'REJECTED'):
                continue
            before = {"status": r.status}
            r.status = 'APPROVED'
            r.reviewed_by = request.user
            r.reviewed_at = timezone.now()
            r.save()
            log_action(request, r, "APPROVED", before_state=before, after_state={"status": "APPROVED"})
            updated_count += 1

        return Response({'detail': f'Successfully approved {updated_count} records.'})


class RecordHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Activity record audit history",
        description="Retrieve the chronological immutable audit trail entries for a given activity record.",
        responses={
            200: AuditLogSerializer(many=True),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def get(self, request, pk):
        try:
            record = ActivityRecord.objects.get(pk=pk, tenant=request.tenant)
        except ActivityRecord.DoesNotExist:
            return Response({'detail': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)

        history = AuditLog.objects.filter(activity_record=record, tenant=request.tenant).order_by('-timestamp')
        return Response(AuditLogSerializer(history, many=True).data)


class RecordExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Export activity records as CSV",
        description="Stream filtered activity records formatted as CSV. Defaults to status=LOCKED if not specified.",
        parameters=[
            OpenApiParameter(name='status', type=str, description='Filter by review status (defaults to LOCKED)'),
            OpenApiParameter(name='scope', type=int, description='Filter by scope'),
            OpenApiParameter(name='source_type', type=str, description='Filter by batch source type'),
            OpenApiParameter(name='batch_id', type=str, description='Filter by batch UUID'),
            OpenApiParameter(name='date_from', type=str, description='Filter by activity date >= YYYY-MM-DD'),
            OpenApiParameter(name='date_to', type=str, description='Filter by activity date <= YYYY-MM-DD'),
            OpenApiParameter(name='search', type=str, description='Search query across fields'),
        ],
        responses={
            200: OpenApiResponse(description="CSV file stream"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request):
        queryset = (
            ActivityRecord.objects.filter(tenant=request.tenant)
            .order_by('-activity_date')
            .select_related('batch', 'reviewed_by')
        )

        status_param = request.query_params.get('status', 'LOCKED')
        if status_param and status_param != 'ALL':
            queryset = queryset.filter(status=status_param)

        scope_param = request.query_params.get('scope')
        if scope_param:
            queryset = queryset.filter(scope=scope_param)

        source_type_param = request.query_params.get('source_type')
        if source_type_param:
            queryset = queryset.filter(batch__source_type=source_type_param)

        batch_id = request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(activity_date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(activity_date__lte=date_to)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(facility_code__icontains=search) |
                Q(location__icontains=search) |
                Q(source_row_id__icontains=search)
            )

        headers = [
            'id', 'activity_date', 'scope', 'category', 'description',
            'quantity', 'unit', 'co2e_kg', 'emission_factor', 'source_system',
            'source_row_id', 'facility_code', 'location', 'review_status',
            'reviewed_by', 'reviewed_at', 'batch_id', 'is_edited'
        ]

        def stream_csv(records_qs, columns):
            buffer = Echo()
            writer = csv.writer(buffer)
            yield writer.writerow(columns)
            for record in records_qs.iterator(chunk_size=200):
                reviewed_by_email = (
                    record.reviewed_by.email
                    if record.reviewed_by and record.reviewed_by.email
                    else ''
                )
                reviewed_at_str = (
                    record.reviewed_at.isoformat()
                    if record.reviewed_at
                    else ''
                )
                activity_date_str = (
                    record.activity_date.isoformat()
                    if record.activity_date
                    else ''
                )
                yield writer.writerow([
                    str(record.id),
                    activity_date_str,
                    record.scope,
                    record.category,
                    record.description,
                    str(record.quantity),
                    record.unit,
                    str(record.co2e_kg) if record.co2e_kg is not None else '',
                    str(record.emission_factor) if record.emission_factor is not None else '',
                    record.source_system,
                    record.source_row_id,
                    record.facility_code,
                    record.location,
                    record.status,
                    reviewed_by_email,
                    reviewed_at_str,
                    str(record.batch_id) if record.batch_id else '',
                    record.is_edited
                ])

        response = StreamingHttpResponse(stream_csv(queryset, headers), content_type='text/csv')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="auditflow_export_{timestamp}.csv"'
        return response
