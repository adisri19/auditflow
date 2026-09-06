from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from apps.emissions.models import ActivityRecord

class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Emissions dashboard summary",
        description="Retrieve high-level emissions KPIs, status counts, scope distributions, and weekly approval rates.",
        parameters=[
            OpenApiParameter(name='date_from', type=str, description='Filter from date YYYY-MM-DD'),
            OpenApiParameter(name='date_to', type=str, description='Filter to date YYYY-MM-DD'),
        ],
        responses={
            200: OpenApiResponse(description="Summary KPI statistics"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request):
        records = ActivityRecord.objects.filter(tenant=request.tenant)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            records = records.filter(activity_date__gte=date_from)
        if date_to:
            records = records.filter(activity_date__lte=date_to)

        status_counts = {item['status']: item['count'] for item in records.values('status').annotate(count=Count('id'))}
        for s in ['PENDING', 'APPROVED', 'FLAGGED', 'REJECTED', 'LOCKED']:
            if s not in status_counts:
                status_counts[s] = 0

        scope_counts = {f"scope_{item['scope']}": item['count'] for item in records.values('scope').annotate(count=Count('id'))}
        for sc in ['scope_1', 'scope_2', 'scope_3']:
            if sc not in scope_counts:
                scope_counts[sc] = 0

        source_counts = {item['batch__source_type']: item['count'] for item in records.values('batch__source_type').annotate(count=Count('id'))}
        for st in ['SAP_FUEL_PROC', 'UTILITY_ELEC', 'CORP_TRAVEL']:
            if st not in source_counts:
                source_counts[st] = 0

        one_week_ago = timezone.now() - timedelta(days=7)
        approved_this_week = records.filter(
            status__in=['APPROVED', 'LOCKED'],
            reviewed_at__gte=one_week_ago
        ).count()

        total_co2e_kg = records.filter(status__in=['APPROVED', 'LOCKED']).aggregate(total=Sum('co2e_kg'))['total'] or 0
        total_tco2e = float(total_co2e_kg) / 1000.0

        return Response({
            'status_counts': status_counts,
            'scope_counts': scope_counts,
            'source_counts': source_counts,
            'approved_this_week': approved_this_week,
            'total_tco2e_approved': round(total_tco2e, 2),
            'total_records': records.count()
        })


class DashboardTimelineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Emissions monthly timeline",
        description="Retrieve aggregated emissions grouped by month and scope using database aggregation.",
        responses={
            200: OpenApiResponse(description="List of monthly emissions totals by scope in tCO2e"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request):
        timeline = (
            ActivityRecord.objects.filter(tenant=request.tenant)
            .annotate(month=TruncMonth('activity_date'))
            .values('month', 'scope')
            .annotate(total_co2e=Sum('co2e_kg'))
            .order_by('month')
        )

        monthly_data = {}
        for entry in timeline:
            m_val = entry['month']
            if not m_val:
                continue
            month_key = m_val.strftime('%Y-%m') if hasattr(m_val, 'strftime') else str(m_val)[:7]
            if month_key not in monthly_data:
                monthly_data[month_key] = {'month': month_key, 'scope1': 0.0, 'scope2': 0.0, 'scope3': 0.0}

            co2_val = float(entry['total_co2e'] or 0) / 1000.0
            scope = entry.get('scope')
            if scope == 1:
                monthly_data[month_key]['scope1'] += co2_val
            elif scope == 2:
                monthly_data[month_key]['scope2'] += co2_val
            elif scope == 3:
                monthly_data[month_key]['scope3'] += co2_val

        sorted_timeline = sorted(monthly_data.values(), key=lambda x: x['month'])
        return Response(sorted_timeline)
