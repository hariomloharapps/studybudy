
# app/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('uuid', 'email', 'name', 'mobile', 'password', 'last_login', 'date_joined')
        extra_kwargs = {
            'uuid': {'read_only': True},
            'date_joined': {'read_only': True}
        }
