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
