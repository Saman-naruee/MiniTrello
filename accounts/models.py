from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('fa', 'Persian'),
    ]
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    preferred_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='en')

    # Django Auth Fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Resolve reverse accessor clashes by providing unique related_name values
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='accounts_user_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='accounts_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

