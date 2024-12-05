from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import RegexValidator

class User(AbstractUser):
    phone_regex = RegexValidator(
        regex=r'^\+?7?\d{10,14}$', 
        message="Номер телефона должен быть в формате: '+7XXXXXXXXXX'."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        unique=True, 
        blank=True, 
        null=True
    )
    is_verified = models.BooleanField(default=False)
    telegram_user_id = models.BigIntegerField(unique=True, null=True, blank=True)

    groups = models.ManyToManyField(
        Group, 
        related_name='tele_app_users',  # Unique related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission, 
        related_name='tele_app_users',  # Unique related_name
        blank=True
    )

    def __str__(self):
        return self.username or self.email

class Car(models.Model):
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = models.ImageField(upload_to='cars/', null=True, blank=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cart = models.ManyToManyField(Car, blank=True, related_name='user_carts')

    def __str__(self):
        return f"Profile for {self.user.username}"