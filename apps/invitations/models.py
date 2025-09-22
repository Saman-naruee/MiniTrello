from django.db import models
from django.conf import settings
import uuid

class Invitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    board = models.ForeignKey(
        'boards.Board',
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_board_invitations'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('email', 'board')
        verbose_name_plural = 'Invitations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation to {self.email} for {self.board.title} by {self.inviter.username}"
