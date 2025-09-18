from django.test import TestCase, Client
from django.urls import reverse
import random
from .base_test import BoardTestCase
from django.conf import settings

from apps.accounts.models import User
from apps.boards.models import Board, List, Card, Membership


"""
In this tests we test 5 approaches:
    1. test model list objects
        a. testing for application itself settings like max_member_per_user... .
        b. testing for members (include owner itself) right access to CRUD operations.
        c. testing for right permissions on object(s) like an anonymous user can access other users data?
    2. testmodelt detail of an object
        a. testing for application itself settings like max_member_per_user... .
        b. testing for members (include owner itself) right access to CRUD operations.
        c. testing for right permissions on object(s) like an anonymous user can access other users data?
    3. test model creation object
        a. testing for application itself settings like max_member_per_user... .
        b. testing for members (include owner itself) right access to CRUD operations.
        c. testing for right permissions on object(s) like an anonymous user can access other users data?
    4. test model update object
        a. testing for application itself settings like max_member_per_user... .
        b. testing for members (include owner itself) right access to CRUD operations.
        c. testing for right permissions on object(s) like an anonymous user can access other users data?
    5. test model delete object
        a. testing for application itself settings like max_member_per_user... .
        b. testing for members (include owner itself) right access to CRUD operations.
        c. testing for right permissions on object(s) like an anonymous user can access other users data?
"""


#### test board list view for each user and test it for each settings and permissions.
class TestBoardListView(BoardTestCase):
    """
    Tests for the BoardListView (the main page listing a user's boards).
    URL: /boards/
    """
    
    def setUp(self):
        """
        This method is run before each individual test.
        We define the URL here for convenience.
        """
        self.url = reverse('boards:boards_list')

    # =================================================================
    # Approach 1: Test Application Settings (max_board_per_user is tested in creation)
    # =================================================================
    # Note: Settings like MAX_MEMBERS_PER_BOARD are not directly applicable to the list view itself,
    # but rather to the actions of adding members, which will be tested in its own view test.
    # We will test MAX_BOARDS_PER_USER in the TestBoardCreateView class.

    # =================================================================
    # Approach 2: Test Access for Authorized Users (Members/Owners)
    # =================================================================

    def test_owner_can_see_their_boards(self):
        """
        Tests if a logged-in user (who is an owner) can see their boards.
        """
        # Arrange: Log in as the board owner.
        self.client.login(username='board_owner', password='p')
        
        # Act: Request the board list page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. The correct template is used.
        self.assertTemplateUsed(response, 'boards/list.html')
        
        # 3. The primary board title is present in the response content.
        self.assertContains(response, self.board.title)
        
        # 4. A board owned by another user is NOT present.
        self.assertNotContains(response, self.other_board.title)

    def test_member_can_see_boards_they_are_a_member_of(self):
        """
        Tests if a logged-in user (who is a member, but not an owner) can see boards
        they have been added to.
        """
        # Arrange: Log in as the member user.
        self.client.login(username='board_member', password='p')

        # Act: Request the board list page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. The board they are a member of is visible.
        self.assertContains(response, self.board.title)
        
        # 3. Boards they are not a member of are not visible.
        self.assertNotContains(response, self.other_board.title)
        
    def test_board_list_context_contains_correct_boards(self):
        """
        Verifies the queryset in the view's context.
        Ensures only the correct boards are passed to the template.
        """
        # Arrange: Log in as the owner.
        self.client.login(username='board_owner', password='p')

        # Act: Request the board list page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The 'boards' context variable exists.
        self.assertTrue('boards' in response.context)
        
        # 2. Check the number of boards in the context. It should be the one main board plus
        # the extra boards we created for the limit test.
        total_owner_boards = 1 + len(self.owner_extra_boards)
        self.assertEqual(len(response.context['boards']), total_owner_boards)
        
        # 3. The primary board is in the queryset.
        self.assertIn(self.board, response.context['boards'])
        
        # 4. The secondary board (owned by another user) is NOT in the queryset.
        self.assertNotIn(self.other_board, response.context['boards'])

    # =================================================================
    # Approach 3: Test Permissions for Unauthorized/Anonymous Users
    # =================================================================

    def test_anonymous_user_is_redirected_to_login(self):
        """
        Tests that an unauthenticated (anonymous) user is redirected to the login page.
        """
        # Act: Request the board list page without logging in.
        response = self.client.get(self.url)

        # Assert:
        # 1. The user is redirected (status code 302).
        self.assertEqual(response.status_code, 302)
        
        # 2. The redirect URL is the login page.
        self.assertIn(reverse('account_login'), response.url)
        
    def test_non_member_sees_empty_list_or_their_own_boards(self):
        """
        Tests that a user who is not a member of any boards sees an empty page,
        or only the boards they themselves own (if any).
        """
        # Arrange: Log in as a user who is not a member of our main test board.
        self.client.login(username='non_member', password='p')

        # Act: Request the board list page.
        response = self.client.get(self.url)
        
        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. The primary test board is NOT in the response content.
        self.assertNotContains(response, self.board.title)
        
        # 3. A message indicating no boards are available might be present.
        # This depends on your template's implementation for an empty state.
        # e.g., self.assertContains(response, "You don't have any boards yet.")



    #### test board delete view for each user and test it for each settings and permissions.



    #### test board update view for each user and test it for each settings and permissions.
