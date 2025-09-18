import json
from django.urls import reverse
from .base_test import BoardTestCase # Import our rich base test case

from apps.boards.models import List, Card

class TestListCreateView(BoardTestCase):
    """
    Tests for the HTMXListCreateView.
    URL: /boards/<board_id>/lists/create/
    """
    def setUp(self):
        self.url = reverse('boards:create_list', kwargs={'board_id': self.board.id})

    # --- Approach 1: Application Settings ---
    # Note: Currently no specific settings like MAX_LISTS_PER_BOARD are implemented.
    # If such a setting is added, a test similar to the max boards test would go here.

    # --- Approach 2: Authorized Access ---
    def test_member_can_get_create_list_form(self):
        """Tests if an authorized member can retrieve the create list form."""
        self.client.login(username='board_member', password='p')
        response = self.client.get(self.url, HTTP_HX_REQUEST='true')
        
        # Behavior check: The request should succeed and contain form elements.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form')
        self.assertContains(response, 'name="title"')

    def test_member_can_create_a_list(self):
        """Tests successful list creation by an authorized member."""
        self.client.login(username='board_member', password='p')
        list_count_before = List.objects.filter(board=self.board).count()
        post_data = {'title': 'QA Testing'}

        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        list_count_after = List.objects.filter(board=self.board).count()

        # Behavior check:
        # 1. The request was successful.
        self.assertEqual(response.status_code, 200)
        # 2. A new list was created in the database.
        self.assertEqual(list_count_after, list_count_before + 1)
        self.assertTrue(List.objects.filter(title='QA Testing', board=self.board).exists())
        # 3. The HTMX response contains the correct trigger.
        self.assertIn('listCreated', response.headers.get('HX-Trigger', ''))

    def test_list_creation_fails_with_invalid_data(self):
        """Tests that creating a list with an invalid (empty) title fails."""
        self.client.login(username='board_owner', password='p')
        post_data = {'title': ''} # Invalid data

        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Behavior check:
        # 1. The server returns a Bad Request status code.
        self.assertEqual(response.status_code, 400)
        # 2. No new list was created.
        self.assertFalse(List.objects.filter(title='', board=self.board).exists())

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_is_forbidden_to_create_list(self): # Test name updated for clarity
        """
        Tests that a non-member of the board receives a 403 Forbidden error.
        This confirms our custom permission logic is working.
        """
        self.client.login(username='non_member', password='p')
        post_data = {'title': 'Should Not Be Created'}
        
        # The URL points to a board the non_member does not have access to.
        url = reverse('boards:create_list', kwargs={'board_id': self.board.id})
        
        response_get = self.client.get(url, HTTP_HX_REQUEST='true')
        response_post = self.client.post(url, post_data, HTTP_HX_REQUEST='true')

        # Your new permission helpers will raise PermissionDenied, resulting in a 403.
        self.assertEqual(response_get.status_code, 403)
        self.assertEqual(response_post.status_code, 403)
        
        # Verify no list was created
        self.assertFalse(List.objects.filter(title='Should Not Be Created').exists())
    

    def test_anonymous_user_cannot_create_list(self):
        """Tests that an unauthenticated user is redirected."""
        post_data = {'title': 'Anonymous List'}
        response = self.client.post(self.url, post_data)

        # Behavior check: Redirect to login page.
        self.assertEqual(response.status_code, 403)


class TestListUpdateView(BoardTestCase):
    """
    Tests for the HTMXListUpdateView.
    URL: /boards/<board_id>/lists/<list_id>/update/
    """
    def setUp(self):
        self.url = reverse('boards:update_list', kwargs={'board_id': self.board.id, 'list_id': self.list1.id})
    
    # --- Approach 2: Authorized Access ---
    def test_member_can_update_list_title(self):
        """Tests successful list title update by an authorized member."""
        self.client.login(username='board_member', password='p')
        updated_title = 'Updated To Do'
        post_data = {'title': updated_title}
        
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        self.list1.refresh_from_db() # Refresh object from DB to get the latest data

        # Behavior check:
        # 1. The request was successful.
        self.assertEqual(response.status_code, 200)
        # 2. The title was updated in the database.
        self.assertEqual(self.list1.title, updated_title)
        # 3. The HTMX response has the correct trigger.
        self.assertIn('listUpdated', response.headers.get('HX-Trigger', ''))

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_cannot_update_list(self):
        """Tests that a non-member cannot update a list in a board they don't belong to."""
        self.client.login(username='non_member', password='p')
        post_data = {'title': 'Should Not Update'}
        
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')

        # Behavior check: Should be denied access with a 403.
        self.assertEqual(response.status_code, 403)


class TestListDeleteView(BoardTestCase):
    """
    Tests for the HTMXListDeleteView.
    URL: /boards/<board_id>/lists/<list_id>/delete/
    """
    def setUp(self):
        # Create a new, disposable list for each delete test to ensure isolation.
        self.list_to_delete = List.objects.create(board=self.board, title='To Be Deleted', order=99)
        Card.objects.create(list=self.list_to_delete, title='Card in deleted list')
        self.url = reverse('boards:delete_list', kwargs={'board_id': self.board.id, 'list_id': self.list_to_delete.id})
    
    # --- Approach 2: Authorized Access ---
    def test_member_can_delete_list(self):
        """Tests successful list deletion by an authorized member."""
        self.client.login(username='board_member', password='p')
        
        # Verify that the list and its card exist before deletion
        list_id = self.list_to_delete.id
        self.assertTrue(List.objects.filter(id=list_id).exists())
        self.assertTrue(Card.objects.filter(list_id=list_id).exists())
        
        # Act: Send a DELETE request
        response = self.client.delete(self.url, HTTP_HX_REQUEST='true')

        # Behavior check:
        # 1. The request was successful (your view returns a JSON response with status 200).
        self.assertEqual(response.status_code, 200)
        # 2. The list is deleted from the database.
        self.assertFalse(List.objects.filter(id=list_id).exists())
        # 3. Importantly, deleting the list should also delete its cards (due to CASCADE).
        self.assertFalse(Card.objects.filter(list_id=list_id).exists())

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_cannot_delete_list(self):
        """Tests that a non-member cannot delete a list."""
        self.client.login(username='non_member', password='p')
        response = self.client.delete(self.url, HTTP_HX_REQUEST='true')
        
        # Behavior check: Denied with 403.
        self.assertEqual(response.status_code, 403)
        # Verify the list was NOT deleted.
        self.assertTrue(List.objects.filter(id=self.list_to_delete.id).exists())


class TestListDetailView(BoardTestCase):
    """
    Tests for the HTMXListDetailView.
    URL: /boards/<board_id>/lists/<list_id>/
    """
    def setUp(self):
        """Set up the URL for the list detail endpoint."""
        self.url = reverse('boards:list_detail', kwargs={'board_id': self.board.id, 'list_id': self.list1.id})

    # --- Approach 2: Authorized Access ---
    def test_member_can_view_list_details(self):
        """
        Tests if an authorized board member can successfully retrieve the list's detail partial.
        """
        # Arrange: Log in as a member of the board.
        self.client.login(username='board_member', password='p')
        
        # Act: Request the list detail partial via an HTMX request.
        response = self.client.get(self.url, HTTP_HX_REQUEST='true')

        # Behavior check:
        # 1. The request should be successful.
        self.assertEqual(response.status_code, 200)
        

    def test_list_detail_context_is_correct(self):
        """
        Verifies that the context passed to the list detail template is accurate.
        """
        # Arrange: Log in as the owner.
        self.client.login(username='board_owner', password='p')

        # Act: Request the list detail page.
        response = self.client.get(self.url)

        # Assert:
        # 1. The 'list' object in the context is the correct one.
        #    (Note: The context variable name depends on your DetailView's 'context_object_name')
        #    Assuming it defaults to 'list'.
        self.assertTrue('list' in response.context)
        self.assertEqual(response.context['list'], self.list1)

    # --- Approach 3: Unauthorized Access ---
    def test_anonymous_user_is_redirected(self):
        """Tests that an unauthenticated user is redirected."""
        response = self.client.get(self.url)
        
        # Behavior check: Redirect to login.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)

    def test_non_member_gets_403(self):
        """
        Tests that a logged-in user who is not a member of the board receives a 403 error.
        """
        # Arrange: Log in as a non-member.
        self.client.login(username='non_member', password='p')
        
        # Act: Attempt to access the list detail endpoint.
        response = self.client.get(self.url)

        # Behavior check: Denied with 403 Forbidden.
        self.assertEqual(response.status_code, 403)
