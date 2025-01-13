# accounts/serializers.py
from rest_framework import serializers
from .models import *

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'timestamp', 'description', 'status']
        read_only_fields = ['id', 'timestamp', 'status']

class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ['balance', 'last_transaction_time']
        read_only_fields = ['last_transaction_time']



from rest_framework import serializers

class RedeemCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)

class RedeemCodeResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedeemCode
        fields = ['code', 'amount', 'is_unlimited', 'valid_days', 'created_at']
