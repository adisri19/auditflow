from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db import connection, OperationalError, DatabaseError
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.tenants.models import Tenant
from apps.tenants.serializers import UserSerializer, TenantSerializer

User = get_user_model()

class HealthCheckView(APIView):
    """
    Lightweight health check endpoint that performs a database query (SELECT 1).
    Used by uptime checkers and scheduled cron jobs to keep the database active
    and verify platform health.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Service Health Check",
        description="Performs an active database ping to verify connectivity and keep database awake.",
        responses={
            200: OpenApiResponse(description="Healthy"),
            503: OpenApiResponse(description="Database unavailable")
        }
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return Response(
                {
                    'status': 'ok',
                    'database': 'connected'
                },
                status=status.HTTP_200_OK
            )
        except (OperationalError, DatabaseError, Exception) as exc:
            return Response(
                {
                    'status': 'degraded',
                    'database': 'disconnected',
                    'detail': 'Database temporarily unavailable or paused. Please restore database in provider dashboard.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        try:
            user = authenticate(request, username=username, password=password)
        except (OperationalError, DatabaseError):
            return Response(
                {'detail': 'Database temporarily unavailable please retry'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if user is not None:
            # Generate JWT
            refresh = RefreshToken.for_user(user)
            # Add custom tenant claim
            if user.tenant:
                refresh['tenant_id'] = str(user.tenant.id)
            
            # Optionally login for session cookies (conforming to CSRF if needed)
            login(request, user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

class TenantListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        tenants = Tenant.objects.all()
        return Response(TenantSerializer(tenants, many=True).data)

