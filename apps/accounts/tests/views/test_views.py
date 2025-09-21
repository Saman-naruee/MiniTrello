from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileUpdateViewTest(TestCase):
    """
    Tests for the user profile update functionality.
    This follows a TDD approach.
    """
    
    @classmethod
    def setUpTestData(cls):
        # Create a user to be used in the tests
        cls.user = User.objects.create_user(
            username='profileuser', 
            email='profile@test.com', 
            password='p',
            first_name='OriginalFirst',
            last_name='OriginalLast'
        )

    def setUp(self):
        # Log the user in before each test
        self.client.login(username='profileuser', password='p')
        
        # This URL does not exist yet. This will be the first failure.
        self.url = reverse('accounts:profile_update')

    def test_profile_update_page_exists_and_uses_correct_template(self):
        """
        TDD: Tests that the profile update page can be accessed via a GET request.
        """
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        # We can test for behavior: does the form contain the user's current info?
        self.assertContains(response, self.user.first_name)
        self.assertContains(response, 'Update Your Profile')  # Fixed: Match template <h2>

    def test_successful_profile_update(self):
        """
        TDD: Tests that a user can successfully update their profile information via POST.
        """
        post_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'username': self.user.username  # Fixed: Include required username (unchanged)
        }
        
        response = self.client.post(self.url, post_data)
        
        # On a successful update, we expect a redirect to the main profile page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:profile'))
        
        # Refresh the user object from the database to check if the data was saved
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.last_name, 'UpdatedLast')
        self.assertEqual(self.user.username, 'profileuser')  # Unchanged, but verify

    def test_profile_update_fails_with_invalid_data(self):
        """
        TDD: Tests that submitting invalid data (e.g., empty required field if any)
        returns the form with errors.
        """
        # Let's assume username cannot be blank in the future
        post_data = {
            'username': '',
            'first_name': 'FirstName' 
        }
        
        response = self.client.post(self.url, post_data)
        
        # The page should re-render with a 200 OK and show form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.') # Example error message

    def test_unauthenticated_user_cannot_access_update_page(self):
        """
        TDD: Tests that a logged-out user is redirected to the login page.
        """
        self.client.logout()
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)
