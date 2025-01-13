# app/models.py
from django.db import models
import uuid

class User(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    password = models.CharField(max_length=128 , blank=True)  # Note: In a real app, always hash passwords
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
