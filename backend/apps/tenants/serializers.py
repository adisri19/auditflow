from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant

User = get_user_model()

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'tenant']
