import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# Import models needed for creating memberships
from apps.boards.models import Board, Membership

class Invitation(models.Model):
    # --- Status constants for clarity and to avoid magic strings ---
    STATUS_SENT = 'sent'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # --- Expiration constant for the is_active method ---
    EXPIRATION_DAYS = 7 # Invitations will be valid for 7 days

    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    board = models.ForeignKey(
        Board, # Changed from string 'boards.Board' for better practice
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_board_invitations'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SENT)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True) # Field for when it was accepted

    class Meta:
        unique_together = ('email', 'board')
        verbose_name_plural = 'Invitations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation for {self.email} to board '{self.board.title}'"

    # --- Custom Helper Methods ---
    
    def is_active(self):
        """
        Checks if the invitation is still valid (not expired and still pending).
        """
        if self.status != self.STATUS_SENT:
            return False

        expiration_date = self.created_at + timedelta(days=self.EXPIRATION_DAYS)
        return timezone.now() < expiration_date

    def accept(self, user):
        """
        Accepts the invitation for a given user.
        - Changes the invitation status.
        - Creates a new board membership for the user.
        - Returns the newly created membership.
        """
        if not self.is_active():
            # We might want to raise an exception here in a real application
            return None 

        # Update invitation status
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = timezone.now()
        self.save()

        # Create the board membership
        membership, created = Membership.objects.get_or_create(
            user=user,
            board=self.board,
            defaults={
                'role': Membership.ROLE_MEMBER,
                'invited_by': self.inviter,
            }
        )
        return membership
