from django.urls import reverse
from apps.boards.tests.base_test import BaseBoardTestCase
from apps.invitations.models import Invitation
from apps.boards.models import Membership

class InvitationCreateViewTest(BaseBoardTestCase):
    """
    TDD: Tests for the view that sends board invitations.
    """
    def setUp(self):
        # This is the URL for the "invite" action on our main test board
        # This URL does not exist yet and will fail.
        self.url = reverse('invitations:send_invitation', kwargs={'board_id': self.board.id})

    # --- Approach 2: Authorized Access (Who CAN invite?) ---

    def test_owner_can_get_invite_form(self):
        """TDD: The board owner should be able to see the invitation form."""
        self.client.login(username='board_owner', password='p')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invite a new member')

    def test_owner_can_send_invitation_successfully(self):
        """TDD: The board owner should be able to successfully send an invitation."""
        self.client.login(username='board_owner', password='p')
        
        post_data = {'email': 'new.invitee@example.com'}
        
        # We check the count of invitations before the action
        invitation_count_before = Invitation.objects.count()
        response = self.client.post(self.url, post_data)
        
        # On success, it should probably redirect back to the board
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('boards:board_detail', kwargs={'board_id': self.board.id}))
        
        # An invitation object should have been created
        self.assertEqual(Invitation.objects.count(), invitation_count_before + 1)
        self.assertTrue(Invitation.objects.filter(email='new.invitee@example.com', board=self.board).exists())

    # --- Approach 3: Unauthorized / Invalid Access ---
    
    def test_member_cannot_send_invitation(self):
        """
        TDD (Business Rule): A regular member should NOT be able to send invitations.
        This requires admin-level access.
        """
        self.client.login(username='board_member', password='p')
        post_data = {'email': 'member.invite@example.com'}
        response = self.client.post(self.url, post_data)

        # We expect a 403 Forbidden because this is a permission issue
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Invitation.objects.filter(email='member.invite@example.com').exists())

    def test_cannot_invite_an_existing_member(self):
        """
        TDD (Edge Case): The form should return an error if you try to invite someone
        who is already a member of the board.
        """
        self.client.login(username='board_owner', password='p')
        
        # self.member is already a member of self.board
        post_data = {'email': self.member.email}
        response = self.client.post(self.url, post_data)

        # It should re-render the form with an error message
        self.assertEqual(response.status_code, 200) # Re-renders the form
        self.assertContains(response, 'This user is already a member of this board.')
        
    def test_unauthenticated_user_is_redirected(self):
        """TDD: An anonymous user should be redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)


class InvitationAcceptViewTest(BaseBoardTestCase):
    """
    TDD: Tests for the view that handles accepting an invitation.
    URL: /accept/<uuid:token>/
    """

    def setUp(self):
        # Create a valid invitation for our tests
        self.invitation = Invitation.objects.create(
            email='new.user.to.accept@example.com',
            board=self.board,
            inviter=self.owner
        )
        self.accept_url = reverse('invitations:accept_invitation', kwargs={'token': self.invitation.token})

    # --- Scenario 1: A brand new user accepts the invitation ---
    def test_new_user_accepts_invitation_is_redirected_to_signup(self):
        """
        TDD: A new user (not registered) clicking the link should be redirected
        to the signup page, with their email pre-filled.
        """
        response = self.client.get(self.accept_url)
        
        # We expect a redirect to the signup page
        self.assertEqual(response.status_code, 302)
        
        # The signup URL should contain the invited email as a query parameter
        signup_url = reverse('account_signup')
        self.assertTrue(signup_url in response.url)
        self.assertIn(f"email={self.invitation.email}", response.url)

        # The invitation token should be stored in the session to be used after signup
        self.assertEqual(self.client.session.get('invitation_token'), str(self.invitation.token))

    # --- Scenario 2: An existing, logged-in user accepts the invitation ---
    def test_existing_logged_in_user_accepts_and_becomes_member(self):
        """
        TDD: An existing user who is already logged in should be immediately added
        to the board and redirected to it.
        """
        # Log in the user who is being invited
        self.client.login(username='non_member', password='p')
        
        # Create an invitation specifically for this logged-in user
        invitation = Invitation.objects.create(
            email=self.non_member.email,
            board=self.board,
            inviter=self.owner
        )
        accept_url = reverse('invitations:accept_invitation', kwargs={'token': invitation.token})

        # The user should not be a member before accepting
        self.assertFalse(Membership.objects.filter(user=self.non_member, board=self.board).exists())

        # Act: The logged-in user visits the accept URL
        response = self.client.get(accept_url)

        # Assert:
        # 1. They are redirected to the board's detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('boards:board_detail', kwargs={'board_id': self.board.id}))
        
        # 2. They are now a member of the board
        self.assertTrue(Membership.objects.filter(user=self.non_member, board=self.board).exists())
        
        # 3. The invitation status is updated to 'accepted'
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, Invitation.STATUS_ACCEPTED)

    # --- Edge Cases ---
    def test_accepting_with_invalid_token_returns_404(self):
        """TDD (Edge Case): An invalid or non-existent token should result in a 404 error."""
        import uuid
        invalid_token_url = reverse('invitations:accept_invitation', kwargs={'token': uuid.uuid4()})
        response = self.client.get(invalid_token_url)
        self.assertEqual(response.status_code, 404)

    def test_cannot_accept_an_expired_invitation(self):
        """TDD (Edge Case): A user cannot accept an invitation that has expired."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Manually set the creation date to be in the past to make it expired
        self.invitation.created_at = timezone.now() - timedelta(days=Invitation.EXPIRATION_DAYS + 1)
        self.invitation.save()
        
        response = self.client.get(self.accept_url)
        
        # Should show an error page, a redirect to an "invalid invitation" page is a good UX.
        # For simplicity, we can expect a 404 or a specific error template.
        self.assertEqual(response.status_code, 404) # Or a custom status/template
