from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.db import OperationalError
from rest_framework import status
from rest_framework.test import APIClient
from apps.tenants.models import Tenant, User
from apps.tenants.views import HealthCheckView, LoginView
from breathe.middleware import DatabaseHealthMiddleware

class HealthAndAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        self.user = User.objects.create_user(
            username="admin@demo.com",
            email="admin@demo.com",
            password="breathe2024",
            tenant=self.tenant
        )

    def test_health_check_endpoint_success(self):
        """Health check returns 200 when database is healthy."""
        response = self.client.get(reverse('api-health-check'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'ok')
        self.assertEqual(response.data.get('database'), 'connected')

    def test_health_check_endpoint_db_failure(self):
        """Health check returns 503 when database query fails."""
        with patch('django.db.connection.cursor', side_effect=OperationalError('Connection refused')):
            response = self.client.get(reverse('api-health-check'))
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(response.data.get('status'), 'degraded')
            self.assertEqual(response.data.get('database'), 'disconnected')

    def test_login_success(self):
        """Valid credentials return JWT access and refresh tokens."""
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'admin@demo.com', 'password': 'breathe2024'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'admin@demo.com')

    def test_login_invalid_credentials(self):
        """Invalid credentials return 400 Bad Request."""
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'admin@demo.com', 'password': 'wrongpassword'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('detail'), 'Invalid credentials')

    def test_login_db_operational_error_returns_503(self):
        """Database connection error during login returns HTTP 503."""
        with patch('apps.tenants.views.authenticate', side_effect=OperationalError('Supabase pooler offline')):
            response = self.client.post(
                reverse('auth-login'),
                {'username': 'admin@demo.com', 'password': 'breathe2024'},
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertIn('detail', response.data)

    def test_database_health_middleware_catches_operational_error(self):
        """DatabaseHealthMiddleware intercepts OperationalError and returns 503 JSON."""
        factory = RequestFactory()
        request = factory.get('/any-path/')

        def raising_view(req):
            raise OperationalError("Pooler tenant not found")

        middleware = DatabaseHealthMiddleware(raising_view)
        response = middleware(request)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Database temporarily unavailable please retry", response.content)
