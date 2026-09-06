import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.tenant = None
        
        # 1. Try to get tenant from authenticated user (if session-auth was run already)
        if hasattr(request, 'user') and request.user.is_authenticated and getattr(request.user, 'tenant', None):
            request.tenant = request.user.tenant
            return

        # 2. Try to get tenant from JWT claim
        auth_header = request.headers.get('Authorization')
        if auth_header and (auth_header.startswith('Bearer ') or auth_header.startswith('JWT ')):
            try:
                token = auth_header.split(' ')[1]
                # Decode using settings.SECRET_KEY
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                
                # Check for tenant_id directly in JWT
                tenant_id = payload.get('tenant_id')
                if tenant_id:
                    request.tenant = Tenant.objects.filter(id=tenant_id).first()
                else:
                    # Fallback to user_id
                    user_id = payload.get('user_id')
                    if user_id:
                        User = get_user_model()
                        user = User.objects.filter(id=user_id).first()
                        if user and user.tenant:
                            request.tenant = user.tenant
            except Exception:
                pass

        # 3. Try to get tenant from HTTP header (fallback)
        if not request.tenant:
            tenant_slug = request.headers.get('X-Tenant-Slug')
            if tenant_slug:
                request.tenant = Tenant.objects.filter(slug=tenant_slug).first()

        # 4. Debug/development fallback (binds the first tenant if available)
        if not request.tenant:
            try:
                request.tenant = Tenant.objects.first()
            except Exception:
                pass
