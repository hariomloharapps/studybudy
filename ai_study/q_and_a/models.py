from django.db import models
import uuid
from django.contrib.auth.models import User

class Test(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('app.User', on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    focus_to = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.email}"

class TestImage(models.Model):
    id = models.AutoField(primary_key=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='test_images/')
    order = models.IntegerField(default=0)  # To maintain image order
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Test Image'
        verbose_name_plural = 'Test Images'

    def __str__(self):
        return f"Image {self.order} for {self.test.title}"

class TestQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    answer_number = models.IntegerField()
    options = models.JSONField()  # Store options as JSON array
    user_answer = models.IntegerField(null=True, blank=True)
    is_asked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question {self.id} for {self.test.title}"

    class Meta:
        ordering = ['created_at']