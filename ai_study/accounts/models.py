# accounts/models.py
from django.db import models
from app.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
# accounts/models.py
from django.db import models
import uuid
from app.models import User

class UserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_transaction_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Account"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('coin_credited_by_ads', 'Coin Credited by Ads'),
        ('coin_spend', 'Coin Spend'),
        ('coin_credited_by_purchase', 'Coin Credited by Purchase'),
        ('coin_credited_by_redeem', 'Coin Credited by Redeem'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='COMPLETED')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.timestamp}"
    







# accounts/models.py
from django.db import models
import uuid
from app.models import User
from datetime import datetime, timedelta

class RedeemCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_unlimited = models.BooleanField(default=False)
    valid_days = models.IntegerField(null=True, blank=True)  # Number of days code is valid if unlimited

    def is_valid(self):
        if self.is_used:
            return False
        if self.is_unlimited and self.valid_days:
            expiry_date = self.created_at + timedelta(days=self.valid_days)
            return datetime.now().astimezone() <= expiry_date
        return not self.is_used

    def __str__(self):
        status = "Used" if self.is_used else "Available"
        return f"Code: {self.code} - Amount: {self.amount} - Status: {status}"

    class Meta:
        ordering = ['-created_at']



# Signal to create UserAccount automatically when a new User is created
@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        UserAccount.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_account(sender, instance, **kwargs):
    instance.useraccount.save()




