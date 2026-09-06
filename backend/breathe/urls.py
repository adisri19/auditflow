from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.tenants.views import LoginView, LogoutView, MeView, TenantListView
from apps.ingestion.views import BatchListCreateView, BatchDetailView, BatchRawRowsView
from apps.emissions.views import (
    RecordListCreateView, RecordBulkApproveView, RecordDetailView,
    RecordApproveView, RecordFlagView, RecordRejectView, RecordLockView,
    RecordHistoryView, RecordExportView, DashboardSummaryView, DashboardTimelineView
)

api_urls = [
    # Auth
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),

    # Tenants
    path('tenants/', TenantListView.as_view(), name='tenant-list'),

    # Batches
    path('batches/', BatchListCreateView.as_view(), name='batch-list-create'),
    path('batches/<uuid:pk>/', BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<uuid:pk>/rows/', BatchRawRowsView.as_view(), name='batch-raw-rows'),

    # Records
    path('records/', RecordListCreateView.as_view(), name='record-list'),
    path('records/bulk_approve/', RecordBulkApproveView.as_view(), name='record-bulk-approve'),
    path('records/export/', RecordExportView.as_view(), name='record-export'),
    path('records/<uuid:pk>/', RecordDetailView.as_view(), name='record-detail'),
    path('records/<uuid:pk>/approve/', RecordApproveView.as_view(), name='record-approve'),
    path('records/<uuid:pk>/flag/', RecordFlagView.as_view(), name='record-flag'),
    path('records/<uuid:pk>/reject/', RecordRejectView.as_view(), name='record-reject'),
    path('records/<uuid:pk>/lock/', RecordLockView.as_view(), name='record-lock'),
    path('records/<uuid:pk>/history/', RecordHistoryView.as_view(), name='record-history'),

    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/timeline/', DashboardTimelineView.as_view(), name='dashboard-timeline'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/', include(api_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
