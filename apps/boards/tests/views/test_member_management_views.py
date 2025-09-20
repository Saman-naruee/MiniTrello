from django.urls import reverse
from apps.boards.tests.base_test import BoardTestCase
from apps.boards.models import Membership



class TestMemberManagementView(BoardTestCase):
    """
    Tests for the Member Management features.
    This follows a TDD approach: writing failing tests before implementation.
    """

    def setUp(self):
        # We'll need the membership object for the 'member' user for some tests
        self.member_membership = Membership.objects.get(user=self.member, board=self.board)

    # =================================================================
    # 1. Tests for Viewing the Members List
    # URL (to be created): /boards/<board_id>/members/
    # =================================================================

    def test_owner_can_view_members_list(self):
        """TDD: An owner should be able to see the list of members for their board."""
        self.client.login(username='board_owner', password='p')
        # This URL does not exist yet -> will fail with NoReverseMatch
        url = reverse('boards:member_list', kwargs={'board_id': self.board.id})
        response = self.client.get(url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.owner.username)
        self.assertContains(response, self.member.username)

    def test_member_can_view_members_list(self):
        """TDD: A regular member should also be able to see who else is on the board."""
        self.client.login(username='board_member', password='p')
        url = reverse('boards:member_list', kwargs={'board_id': self.board.id})
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)

    def test_non_member_cannot_view_members_list(self):
        """TDD: A non-member should get a 404 error."""
        self.client.login(username='non_member', password='p')
        url = reverse('boards:member_list', kwargs={'board_id': self.board.id})
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 404)

    # =================================================================
    # 2. Tests for Removing a Member
    # URL (to be created): /boards/<board_id>/memberships/<membership_id>/delete/
    # =================================================================
    
    def test_owner_can_remove_a_member(self):
        """TDD: The board owner should be able to remove another member."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:remove_member', kwargs={'board_id': self.board.id, 'membership_id': self.member_membership.id})
        
        response = self.client.delete(url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 200) # Assuming success response
        self.assertFalse(Membership.objects.filter(id=self.member_membership.id).exists())

    def test_member_cannot_remove_another_member(self):
        """TDD: A regular member should NOT be able to remove another member."""
        self.client.login(username='board_member', password='p')
        # Create another member to be removed
        another_member_user = self.another_user
        another_membership = Membership.objects.create(user=another_member_user, board=self.board)
        url = reverse('boards:remove_member', kwargs={'board_id': self.board.id, 'membership_id': another_membership.id})

        response = self.client.delete(url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 403) # Forbidden
        self.assertTrue(Membership.objects.filter(id=another_membership.id).exists())

    def test_cannot_remove_the_owner(self):
        """TDD: No one, not even the owner, should be able to remove the owner's membership."""
        self.client.login(username='board_owner', password='p')
        owner_membership = Membership.objects.get(user=self.owner, board=self.board)
        url = reverse('boards:remove_member', kwargs={'board_id': self.board.id, 'membership_id': owner_membership.id})

        response = self.client.delete(url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 400) # Bad Request, as this action is invalid
        self.assertTrue(Membership.objects.filter(id=owner_membership.id).exists())
        
    # =================================================================
    # 3. Tests for Changing a Member's Role
    # URL (to be created): /boards/<board_id>/memberships/<membership_id>/update_role/
    # =================================================================
    
    def test_owner_can_change_member_role(self):
        """TDD: The board owner should be able to change a member's role (e.g., to Admin)."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:update_member_role', kwargs={'board_id': self.board.id, 'membership_id': self.member_membership.id})
        post_data = {'role': Membership.ROLE_ADMIN}
        
        response = self.client.post(url, post_data, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.member_membership.refresh_from_db()
        self.assertEqual(self.member_membership.role, Membership.ROLE_ADMIN)

    def test_member_cannot_change_role(self):
        """TDD: A regular member should not be able to change anyone's role."""
        self.client.login(username='board_member', password='p')
        owner_membership = Membership.objects.get(user=self.owner, board=self.board)
        url = reverse('boards:update_member_role', kwargs={'board_id': self.board.id, 'membership_id': owner_membership.id})
        post_data = {'role': Membership.ROLE_MEMBER}

        response = self.client.post(url, post_data, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 403)
        owner_membership.refresh_from_db()
        self.assertEqual(owner_membership.role, Membership.ROLE_OWNER) # Role should not have changed
