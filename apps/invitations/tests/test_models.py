from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User
from apps.boards.models import Board, Membership
from apps.invitations.models import Invitation
from .base import BaseModelTestCase
from custom_tools.logger import custom_logger, info, success, error

class InvitationModelTest(BaseModelTestCase):
    """
    Tests for the Invitation model, covering creation, constraints, and custom methods.
    """
    
    @classmethod
    def setUpTestData(cls):
        # Create users and a board to be used as context for invitations
        cls.inviter = User.objects.create_user(username='inviter', password='p')
        cls.existing_member = User.objects.create_user(username='existing_member', email='member@test.com', password='p')
        cls.board = Board.objects.create(owner=cls.inviter, title='Test Board')
        Membership.objects.create(user=cls.existing_member, board=cls.board)

    def test_invitation_creation_and_defaults(self):
        """TDD: Test basic creation of an invitation and its default values."""
        invitation = Invitation.objects.create(
            email='new.user@example.com',
            board=self.board,
            inviter=self.inviter
        )
        
        self.assertIsNotNone(invitation.token)
        self.assertEqual(invitation.status, Invitation.STATUS_SENT)
        self.assertIsNone(invitation.accepted_at)
        self.assertTrue(invitation.is_active()) # A new helper method we'll create

    def test_unique_together_constraint_email_and_board(self):
        """
        TDD (Edge Case): Test that the same email cannot be invited to the same board twice
        if the first invitation is still active.
        """
        # Create the first invitation
        Invitation.objects.create(
            email='duplicate.email@example.com',
            board=self.board,
            inviter=self.inviter
        )
        
        # Attempt to create the exact same invitation again
        with self.assertRaises(IntegrityError):
            Invitation.objects.create(
                email='duplicate.email@example.com',
                board=self.board,
                inviter=self.inviter
            )

    def test_string_representation(self):
        """TDD: Test the __str__ method for a readable representation."""
        invitation = Invitation.objects.create(
            email='str.repesentation@example.com',
            board=self.board,
            inviter=self.inviter
        )
        expected_str = f"Invitation for str.repesentation@example.com to board 'Test Board'"
        self.assertEqual(str(invitation), expected_str)

    def test_is_active_helper_method_for_expired_invitation(self):
        """
        TDD (Edge Case): Test that an expired invitation is not considered active.
        """
        # Create invitation normally (auto_now_add will set created_at)
        invitation = Invitation.objects.create(
            email='expired@example.com',
            board=self.board,
            inviter=self.inviter
        )

        # Manually set created_at to be in the past to simulate an expired invitation
        past_date = timezone.now() - timedelta(days=Invitation.EXPIRATION_DAYS + 1)
        invitation.created_at = past_date
        invitation.save()  # Save again to persist the manually set created_at

        self.assertFalse(invitation.is_active())

    def test_accept_method_changes_status_and_creates_membership(self):
        """
        TDD: Test the 'accept' method. It should change the invitation status
        and create a new Membership for the accepted user.
        """
        # The user who is accepting the invitation
        accepted_user = User.objects.create_user(username='accepted_user', email='accepted@example.com', password='p')
        
        invitation = Invitation.objects.create(
            email=accepted_user.email, # Invite the user's email
            board=self.board,
            inviter=self.inviter
        )
        
        # Verify that the user is NOT a member before accepting
        self.assertFalse(Membership.objects.filter(user=accepted_user, board=self.board).exists())
        
        # Act: Accept the invitation
        membership = invitation.accept(accepted_user)
        
        # Assert:
        # 1. The invitation status is now 'accepted'.
        self.assertEqual(invitation.status, Invitation.STATUS_ACCEPTED)
        
        # 2. A new membership was created and returned.
        self.assertIsNotNone(membership)
        self.assertEqual(membership.user, accepted_user)
        self.assertEqual(membership.board, self.board)
        self.assertEqual(membership.role, Membership.ROLE_MEMBER) # Should default to Member
        
        # 3. The user is now a member of the board.
        self.assertTrue(Membership.objects.filter(user=accepted_user, board=self.board).exists())
