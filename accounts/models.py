from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['username']  
    
    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.username:  # Automatically set a username if not provided
            self.username = self.email.split('@')[0]  # Use email's local part as username
        super().save(*args, **kwargs)
