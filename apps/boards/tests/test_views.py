from django.test import TestCase, Client
from django.urls import reverse
import random
from .base_test import BoardTestCase
from django.conf import settings

from apps.accounts.models import User
from apps.boards.models import Board, List, Card, Membership

from colorama import Fore

from custom_tools.logger import custom_logger


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


#### test board detail as the same but test the board's lists and lists' cards
class TestBoardDetailView(BoardTestCase):
    """
    Tests for the BoardDetailView (the page displaying a single board with its lists and cards).
    URL: /boards/<board_id>/
    """
    
    def setUp(self):
        """
        This method is run before each individual test.
        We define the URL for the primary board's detail page.
        """
        self.url = reverse('boards:board_detail', kwargs={'board_id': self.board.id})

    # =================================================================
    # Approach 1: Test Application Settings
    # =================================================================
    # Note: Application-wide settings are generally not tested at the detail view level.
    # They are more relevant to actions like creation or adding members.

    # =================================================================
    # Approach 2: Test Access for Authorized Users (Members/Owners)
    # =================================================================

    def test_owner_can_view_board_details(self):
        """
        Tests if the owner of a board can successfully view its detail page.
        """
        # Arrange: Log in as the owner of self.board.
        self.client.login(username='board_owner', password='p')

        # Act: Request the detail page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. The correct template is used.
        self.assertTemplateUsed(response, 'boards/detail.html')
        
        # 3. The response contains the board's title, its lists, and its cards.
        self.assertContains(response, self.board.title)
        self.assertContains(response, self.list1.title) # Checks if list is rendered
        self.assertContains(response, self.card1.title) # Checks if card is rendered

    def test_member_can_view_board_details(self):
        """
        Tests if a regular member of a board can successfully view its detail page.
        """
        # Arrange: Log in as a member of self.board.
        self.client.login(username='board_member', password='p')

        # Act: Request the detail page.
        response = self.client.get(self.url)

        # Assert: The experience should be the same as the owner for viewing.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.board.title)
        self.assertContains(response, self.card1.title)

    def test_board_detail_context_is_correct(self):
        """
        Verifies that the context passed to the template is accurate.
        This tests the get_context_data method of the DetailView more directly.
        """
        # Arrange: Log in as the owner.
        self.client.login(username='board_owner', password='p')

        # Act: Request the detail page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The 'board' object in the context is the correct one.
        self.assertEqual(response.context['board'], self.board)
        
        # 2. The 'lists' queryset in the context contains all lists of this board.
        self.assertIn(self.list1, response.context['lists'])
        self.assertIn(self.list2, response.context['lists'])
        self.assertEqual(len(response.context['lists']), 2)
        
        # 3. Check the prefetched cards within a list object from the context.
        # This confirms that our view optimization (prefetch_related) is working.
        list_from_context = response.context['lists'].get(id=self.list1.id)
        # Note: The prefetched data is stored in 'prefetched_cards' attribute from our view
        self.assertIn(self.card1, list_from_context.prefetched_cards)
        self.assertIn(self.card2, list_from_context.prefetched_cards)

    # =================================================================
    # Approach 3: Test Permissions for Unauthorized/Anonymous Users
    # =================================================================

    def test_anonymous_user_is_redirected(self):
        """
        Tests that an unauthenticated user is redirected to the login page.
        """
        # Act: Request the detail page without logging in.
        response = self.client.get(self.url)
        
        # Assert: Redirect (302) to the login URL.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)
    
    def test_non_member_gets_403_forbidden(self):
        """
        Tests that a logged-in user who is NOT a member of the board receives a 403 Forbidden error,
        as if the board does not exist for them. This is crucial for privacy.
        """
        # Arrange: Log in as a user who is not a member of self.board.
        self.client.login(username='non_member', password='p')

        # Act: Request the detail page of a board they don't have access to.
        response = self.client.get(self.url)

        # Assert: The server should respond with a 403 Forbidden.
        self.assertEqual(response.status_code, 403)


#### test board create view for each user and test it for each settings and permissions.
class TestBoardCreateView(BoardTestCase):
    """
    Tests for the HTMXBoardCreateView.
    URL: /boards/create/
    """

    def setUp(self):
        """Set up the URL for the board creation endpoint."""
        self.url = reverse('boards:create_board')

    # =================================================================
    # Approach 1: Test Application Settings
    # =================================================================
    
    def test_user_cannot_create_board_when_at_limit(self):
        """
        Tests if a user who has reached the MAX_BOARDS_PER_USER limit is blocked from creating a new board.
        This directly tests the application setting.
        """
        # Arrange: Log in as the owner, who already has the maximum number of boards
        # created for them in the base_test.py setup.
        is_logged = self.client.login(username='board_owner', password='p')
        custom_logger(f"is logged?: {is_logged}", Fore.YELLOW)
        # self.client.get(self.url, HTTP_HX_REQUEST='true')  # Send HX-Request header
        
        # Verify that the user is indeed at the limit
        boards_count = Board.objects.filter(owner=self.owner).count()
        custom_logger(f"User {self.owner.email} has {boards_count} boards", Fore.YELLOW)
        self.assertEqual(boards_count, self.max_board_per_user)

        # Act: Attempt to create one more board.
        post_data = {'title': 'One Board Too Many', 'color': 'pink'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Assert:
        # 1. The server should return a 400 Bad Request because the form is invalid.
        self.assertEqual(response.status_code, 400)
        
        # 2. No new board should have been created.
        self.assertFalse(Board.objects.filter(title='One Board Too Many').exists())
        

    # =================================================================
    # Approach 2: Test Access for Authorized Users
    # =================================================================
    
    def test_logged_in_user_can_create_board(self):
        """
        Tests the successful creation of a board by an authenticated user who is below the limit.
        """
        # Arrange: Log in as a user who has no boards yet.
        self.client.login(username='board_member', password='p')
        # self.client.get(self.url, HTTP_HX_REQUEST='true')  # Send HX-Request header
        
        # Act: Send a valid POST request to create a new board.
        post_data = {'title': 'Member-Created Board', 'description': 'A new board.', 'color': 'purple'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Assert:
        # 1. The request is successful (200 OK).
        self.assertEqual(response.status_code, 200)
        
        # 2. A new board now exists in the database with the correct owner.
        self.assertTrue(Board.objects.filter(title='Member-Created Board', owner=self.member).exists())
        
        # 3. A membership for the owner was automatically created.
        new_board = Board.objects.get(title='Member-Created Board')
        self.assertTrue(Membership.objects.filter(board=new_board, user=self.member, role=Membership.ROLE_OWNER).exists())
        
        # 4. The response contains the HTML for the new board card and triggers an HTMX event.
        self.assertContains(response, 'Member-Created Board')
        self.assertIn('boardCreated', response.headers.get('HX-Trigger', ''))

    def test_create_board_with_invalid_data(self):
        """
        Tests that submitting the form with invalid data (e.g., a short title) fails correctly.
        """
        # Arrange: Log in a user.
        self.client.login(username='board_member', password='p')
        # response = self.client.get(self.url, HTTP_HX_REQUEST='true') 
        
        # Act: Send a POST request with an invalid title.
        post_data = {'title': 'a', 'color': 'blue'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')
        
        # Assert:
        # 1. The server returns a 400 Bad Request.
        self.assertEqual(response.status_code, 400)
        
        # 2. No board was created.
        self.assertFalse(Board.objects.filter(title='a').exists())
        
        # 3. The response contains the form again, showing the validation error.
        # self.assertContains(response, 'Title must be at least 4 characters long')

    # =================================================================
    # Approach 3: Test Permissions for Unauthorized Users
    # =================================================================

    def test_anonymous_user_cannot_access_create_form(self):
        """
        Tests that an unauthenticated user cannot even view the create form (GET request).
        """
        # Act: Attempt to get the create form page.
        response = self.client.get(self.url)

        # Assert: User is redirected to login.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)
        
    def test_anonymous_user_cannot_create_board(self):
        """
        Tests that an unauthenticated user cannot create a board via a POST request.
        """
        # Act: Attempt to post data to the create URL.
        post_data = {'title': 'Anonymous Board', 'color': 'red'}
        response = self.client.post(self.url, post_data)

        # Assert: User is redirected to login and no board is created.
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Board.objects.filter(title='Anonymous Board').exists())
    



#### test board update view for each user and test it for each settings and permissions.
class TestBoardUpdateView(BoardTestCase):
    """
    Tests for the HTMXBoardUpdateView.
    URL: /boards/<board_id>/update/
    """
    
    def setUp(self):
        """Set up the URL for the board update endpoint."""
        self.url = reverse('boards:update_board', kwargs={'board_id': self.board.id})

    # =================================================================
    # Approach 1: Test Application Settings
    # =================================================================
    # Note: Settings are not directly applicable to the update view.
    # Logic like member limits would be in an "add member" view, not here.

    # =================================================================
    # Approach 2: Test Access for Authorized Users
    # =================================================================
    
    def test_owner_can_get_update_form(self):
        """
        Tests if the board owner can successfully retrieve the update form.
        """
        # Arrange: Log in as the owner.
        self.client.login(username='board_owner', password='p')

        # Act: Request the update form via a GET request.
        response = self.client.get(self.url, HTTP_HX_REQUEST='true')

        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. The form in the response contains the current board's title.
        self.assertContains(response, self.board.title)

    def test_owner_can_update_board(self):
        """
        Tests if the board owner can successfully update the board's details.
        """
        # Arrange: Log in as the owner.
        self.client.login(username='board_owner', password='p')
        
        # Act: Send a POST request with new data.
        post_data = {'title': 'Title Updated by Owner', 'description': 'New desc.', 'color': 'yellow'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Assert:
        # 1. The request is successful.
        self.assertEqual(response.status_code, 200)
        
        # 2. Refresh the board object from the database to check if the data was saved.
        self.board.refresh_from_db()
        self.assertEqual(self.board.title, 'Title Updated by Owner')
        self.assertEqual(self.board.color, 'yellow')
        
        # 3. The response contains the updated content and triggers the correct event.
        self.assertContains(response, 'Title Updated by Owner')
        self.assertIn('boardUpdated', response.headers.get('HX-Trigger', ''))

    # =================================================================
    # Approach 3: Test Permissions for Unauthorized/Anonymous/Insufficient Role Users
    # =================================================================

    def test_anonymous_user_cannot_update_board(self):
        """
        Tests that an unauthenticated user is redirected when trying to access the update view.
        """
        # Act: Attempt GET and POST requests without logging in.
        response_get = self.client.get(self.url)
        response_post = self.client.post(self.url, {'title': 'test'})

        # Assert: Both should redirect to the login page.
        self.assertEqual(response_get.status_code, 302)
        self.assertIn(reverse('account_login'), response_get.url)
        self.assertEqual(response_post.status_code, 302)

    def test_non_member_cannot_update_board(self):
        """
        Tests that an authenticated user who is not a member of the board gets a 404 error.
        """
        # Arrange: Log in as a user who is not part of the board.
        self.client.login(username='non_member', password='p')

        # Act: Attempt GET and POST requests.
        response_get = self.client.get(self.url)
        response_post = self.client.post(self.url, {'title': 'test'})
        custom_logger(f"Get response status code : {response_get.status_code}", Fore.YELLOW)
        custom_logger(f"Post response status code : {response_post.status_code}", Fore.YELLOW)

        # Assert: Both should result in a 404 Not Found.
        self.assertEqual(response_get.status_code, 404)
        self.assertEqual(response_post.status_code, 404)

    def test_member_with_insufficient_permissions_cannot_update_board(self):
        """
        Tests that a regular member (non-owner/admin) CANNOT update the board's main details.
        This enforces our business rule that only owners/admins can edit the board.
        """
        # Arrange: Log in as a regular member.
        self.client.login(username='board_member', password='p')
        original_title = self.board.title

        # Act: Attempt to update the board.
        post_data = {'title': 'Title Updated by Member', 'color': 'pink'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Assert:
        # 1. The server should forbid the action. We expect a 404 because the get_user_board
        # helper function will likely fail if we add an ownership check.
        # If you were to implement a custom mixin, you might return a 403 Forbidden instead.
        self.assertEqual(response.status_code, 404)
        
        # 2. The board's title should NOT have changed in the database.
        self.board.refresh_from_db()
        self.assertEqual(self.board.title, original_title)



#### test board delete view for each user and test it for each settings and permissions.
class TestBoardDeleteView(BoardTestCase):
    """
    Tests for the HTMXBoardDeleteView.
    URL: /boards/<board_id>/delete/
    """

    def setUp(self):
        # self.owner.login() # Assuming you have a helper login method on your User model, or use self.client.login
        self.client.login(username='board_owner', password='p')
        self.board_to_delete = Board.objects.create(owner=self.owner, title='Board to be Deleted')
        Membership.objects.create(user=self.owner, board=self.board_to_delete, role=Membership.ROLE_OWNER)
        self.url = reverse('boards:delete_board', kwargs={'board_id': self.board_to_delete.id})

    # =================================================================
    # Approach 1: Test Application Settings
    # =================================================================
    # Note: No application settings are directly relevant to the delete action itself.

    # =================================================================
    # Approach 2: Test Access for Authorized Users
    # =================================================================

    def test_owner_can_get_delete_confirmation_page(self): # Test name changed for clarity
        """
        Tests if the board owner can successfully retrieve the full delete confirmation page.
        """
        response = self.client.get(self.url) # No HTMX header for a full page load
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Are you sure you want to permanently delete this board?')
        self.assertContains(response, self.board_to_delete.title)
        
    def test_owner_can_delete_board_with_htmx(self):
        """
        Tests if the board owner can successfully delete the board via an HTMX POST request.
        """
        board_id = self.board_to_delete.id
        self.assertTrue(Board.objects.filter(id=board_id).exists())

        # ❗❗❗ CORE FIX: Simulate an HTMX POST request
        response = self.client.post(self.url, HTTP_HX_REQUEST='true')

        # Assert: The response for a successful HTMX delete should be 204 No Content.
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Board.objects.filter(id=board_id).exists())

    def test_owner_can_delete_board_with_regular_form_post(self):
        """
        Tests the fallback for non-JavaScript users.
        The deletion should work and redirect to the success_url.
        """
        board_id = self.board_to_delete.id
        
        # Act: Send a regular POST request (no HTMX header)
        response = self.client.post(self.url)

        # Assert: The user should be redirected to the board list page.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('boards:boards_list'), response.url)
        self.assertFalse(Board.objects.filter(id=board_id).exists())
    
    # =================================================================
    # Approach 3: Test Permissions for Unauthorized/Anonymous/Insufficient Role Users
    # =================================================================
    
    def test_anonymous_user_cannot_delete_board(self):
        """
        Tests that an unauthenticated user is redirected when trying to delete a board.
        """
        # Act: Attempt GET (for form) and POST (for action) requests.
        self.client.logout()
        response_get = self.client.get(self.url)
        response_post = self.client.post(self.url)

        # Assert: Both should now correctly redirect to the login page.
        self.assertEqual(response_get.status_code, 302)
        self.assertIn(reverse('account_login'), response_get.url)

        self.assertEqual(response_post.status_code, 302)
        self.assertIn(reverse('account_login'), response_post.url)
        
        # Verify the board was NOT deleted
        self.assertTrue(Board.objects.filter(id=self.board_to_delete.id).exists())

    def test_non_member_cannot_delete_board(self):
        """
        Tests that a non-member gets a 404 error when trying to delete a board.
        """
        # Arrange: Log in as a non-member.
        self.client.login(username='non_member', password='p')

        # Act & Assert for both GET and POST
        response_get = self.client.get(self.url)
        self.assertEqual(response_get.status_code, 404)
        
        response_post = self.client.post(self.url)
        self.assertEqual(response_post.status_code, 404)
        
        # Verify the board was not deleted.
        self.assertTrue(Board.objects.filter(id=self.board_to_delete.id).exists())

    def test_member_cannot_delete_board(self):
        """
        Tests that a regular member (non-owner) CANNOT delete the board.
        This is a critical permission check.
        """
        # Arrange:
        # 1. Add our 'member' user to the board we are about to delete.
        Membership.objects.create(user=self.member, board=self.board_to_delete, role=Membership.ROLE_MEMBER)
        # 2. Log in as that member.
        self.client.login(username='board_member', password='p')
        
        # Act & Assert for both GET and POST attempts
        response_get = self.client.get(self.url)
        self.assertEqual(response_get.status_code, 404)
        
        response_post = self.client.post(self.url)
        self.assertEqual(response_post.status_code, 404)
        
        # Assert: Crucially, verify the board still exists.
        self.assertTrue(Board.objects.filter(id=self.board_to_delete.id).exists())
