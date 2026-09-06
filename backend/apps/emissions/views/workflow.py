from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from apps.emissions.models import ActivityRecord
from apps.emissions.serializers import ActivityRecordSerializer
from apps.audit.utils import log_action

def _transition_record(request, pk, new_status, action_label, valid_from_statuses=None):
    try:
        with transaction.atomic():
            record = ActivityRecord.objects.select_for_update().get(pk=pk, tenant=request.tenant)

            # Return 400 if record is LOCKED unless target status is LOCKED
            if record.status == 'LOCKED' and new_status != 'LOCKED':
                return Response({'detail': 'Record is locked.'}, status=status.HTTP_400_BAD_REQUEST)

            # Return 400 if valid_from_statuses is provided and current status is not in the list
            if valid_from_statuses is not None and record.status not in valid_from_statuses:
                return Response(
                    {'detail': f'Cannot transition record from status {record.status} to {new_status}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Return 400 with message "co2e_kg must be set and greater than zero before locking" if new_status is LOCKED and co2e_kg is null or <= 0
            if new_status == 'LOCKED' and (record.co2e_kg is None or record.co2e_kg <= 0):
                return Response(
                    {'detail': 'co2e_kg must be set and greater than zero before locking'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            before = {"status": record.status}
            record.status = new_status
            record.reviewed_by = request.user
            record.reviewed_at = timezone.now()

            notes = request.data.get('review_notes')
            if notes is not None:
                record.review_notes = str(notes)

            record.save()

            after = {"status": record.status, "review_notes": record.review_notes}
            log_action(request, record, action_label, before_state=before, after_state=after)

            return Response(ActivityRecordSerializer(record).data)

    except ActivityRecord.DoesNotExist:
        return Response({'detail': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)


class RecordApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Approve activity record",
        description="Transition an activity record to APPROVED status and record review details in the audit trail.",
        request=inline_serializer(
            name="RecordApproveRequest",
            fields={"review_notes": serializers.CharField(required=False, allow_blank=True)}
        ),
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Record is locked or invalid status transition"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def post(self, request, pk):
        return _transition_record(request, pk, 'APPROVED', 'APPROVED')


class RecordFlagView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Flag activity record",
        description="Transition an activity record to FLAGGED status for further investigation.",
        request=inline_serializer(
            name="RecordFlagRequest",
            fields={"review_notes": serializers.CharField(required=False, allow_blank=True)}
        ),
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Record is locked or invalid status transition"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def post(self, request, pk):
        return _transition_record(request, pk, 'FLAGGED', 'FLAGGED')


class RecordRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Reject activity record",
        description="Transition an activity record to REJECTED status.",
        request=inline_serializer(
            name="RecordRejectRequest",
            fields={"review_notes": serializers.CharField(required=False, allow_blank=True)}
        ),
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Record is locked or invalid status transition"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def post(self, request, pk):
        return _transition_record(request, pk, 'REJECTED', 'REJECTED')


class RecordLockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Lock activity record",
        description="Lock an approved activity record for audit immutability. Requires co2e_kg > 0.",
        request=inline_serializer(
            name="RecordLockRequest",
            fields={"review_notes": serializers.CharField(required=False, allow_blank=True)}
        ),
        responses={
            200: ActivityRecordSerializer,
            400: OpenApiResponse(description="Record not approved or co2e_kg not set and greater than zero"),
            404: OpenApiResponse(description="Record not found"),
        }
    )
    def post(self, request, pk):
        return _transition_record(request, pk, 'LOCKED', 'LOCKED', valid_from_statuses=['APPROVED'])
