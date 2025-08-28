from django.db import models
from MiniTrello.settings import AUTH_USER_MODEL


class Board(models.Model):
    COLOR_CHOICES = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('pink', 'Pink'),
    ]

    owner = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    color = models.ChoiceField(choices=COLOR_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class List(models.Model):
    title = models.CharField(max_length=255)
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Card(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('top', 'Top'),
        ('important', 'Important'),
        ('important_and_urgent', 'Important and Urgent'),
        ('urgent', 'Urgent'),
        ('not_important', 'Not Important'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    list = models.ForeignKey(List, on_delete=models.CASCADE)
    priority = models.ChoiceField(choices=PRIORITY_CHOICES)
    due_date = models.DateField(null=True, blank=True)
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
