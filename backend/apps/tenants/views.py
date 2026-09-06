from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.tenants.serializers import UserSerializer, TenantSerializer

User = get_user_model()

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(request, username=username, password=password)
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
