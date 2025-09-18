from django.db import models
from django.conf import settings


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

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_boards")
    color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class List(models.Model):
    title = models.CharField(max_length=255)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="lists")
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.board.title}"


class Card(models.Model):
    PRIORITY_TOP = 10
    PRIORITY_IMPORTANT_AND_URGENT = 20
    PRIORITY_IMPORTANT = 30
    PRIORITY_URGENT = 40
    PRIORITY_HIGH = 50
    PRIORITY_MEDIUM = 60
    PRIORITY_LOW = 70
    PRIORITY_NOT_IMPORTANT = 80

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_TOP, 'Top'),
        (PRIORITY_IMPORTANT, 'Important'),
        (PRIORITY_IMPORTANT_AND_URGENT, 'Important and Urgent'),
        (PRIORITY_URGENT, 'Urgent'),
        (PRIORITY_NOT_IMPORTANT, 'Not Important'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        help_text="Users assigned to this card."
    )

    list = models.ForeignKey('List', on_delete=models.CASCADE, related_name="cards")
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    order = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=0)

    class Meta:
        ordering = ['priority', 'order']

    def move_to(self, new_list):
        """
        Move the card to a different list.
        """
        self.list = new_list
        self.save(update_fields=["list", "updated_at"])


class Membership(models.Model):
    """
    Represents a user's membership on a Board.

    - Each user can have at most one Membership per Board (unique constraint).
    - Roles are defined as integer constants so ordering and checks are easy.
    - `is_active` can be used to soft-remove a member without deleting history.
    - `invited_by` and `invited_at` support invitation flows.
    - Add other flags (can_edit, can_comment, ...) or compute from role.
    """

    # Role constants (lower value = higher privilege)
    ROLE_OWNER = 10
    ROLE_ADMIN = 20
    ROLE_MEMBER = 30
    ROLE_VIEWER = 40

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
        (ROLE_VIEWER, "Viewer"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.PositiveSmallIntegerField(
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
        help_text="Role of the user on the board. Lower value => more privileges.",
    )

    # Invitation flow / status fields (optional)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
        help_text="User who invited this member (if any).",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Soft-delete / active flag
    is_active = models.BooleanField(default=True)

    # Optional per-member permissions (can override role-based defaults)
    can_edit = models.BooleanField(default=True)
    can_comment = models.BooleanField(default=True)
    can_invite = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "board")
        indexes = [
            models.Index(fields=["board", "role"]),
            models.Index(fields=["user"]),
        ]
        ordering = ["role", "created_at"]
        verbose_name = "Board membership"
        verbose_name_plural = "Board memberships"

    def __str__(self):
        return f"{self.user} on {self.board} ({self.get_role_display()})"

    # Helper methods
    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def is_admin(self):
        return self.role in {self.ROLE_OWNER, self.ROLE_ADMIN}

    def promote(self, new_role):
        """
        Promote or change role. Validate allowed transitions here if needed.
        """
        if new_role not in dict(self.ROLE_CHOICES):
            raise ValueError("Invalid role value")
        self.role = new_role
        self.save(update_fields=["role", "updated_at"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def activate(self):
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])
