# tests/serializers.py
from rest_framework import serializers
from .models import Test

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['uuid', 'title', 'description', 'focus_to', 'pdf_file', 
                 'number_of_pages', 'created_at']
        read_only_fields = ['uuid', 'created_at']