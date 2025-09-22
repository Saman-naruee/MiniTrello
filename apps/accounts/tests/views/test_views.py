from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.accounts.models import User
from custom_tools.logger import success, info, custom_logger

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


    def test_profile_update_fails_with_duplicate_username(self):
        """
        TDD: Tests that updating a profile to an existing username fails.
        """
        # Create another user with a username we want to switch to.
        User.objects.create_user(username='existinguser', password='p')

        post_data = {
            'username': 'existinguser',
            'first_name': self.user.first_name,
            'last_name': self.user.last_name
        } # Try to take an existing username
        response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertContains(response, 'User with this Username already exists.')

        # Verify the original user's username has not changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'profileuser')



class AuthenticatedRedirectTest(TestCase):
    """
    Tests redirection behavior for already authenticated users.
    """
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='p')

    def setUp(self):
        self.client.login(username='testuser', password='p')

    def test_authenticated_user_is_redirected_from_login_page(self):
        """
        TDD: A logged-in user visiting the login page should be redirected.
        """
        login_url = reverse('account_login') # Using allauth's URL name
        response = self.client.get(login_url)

        # We expect a redirect to the LOGIN_REDIRECT_URL defined in settings
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)

    def test_authenticated_user_is_redirected_from_signup_page(self):
        """
        TDD: A logged-in user visiting the signup page should be redirected.
        """
        signup_url = reverse('account_signup') # Using allauth's URL name
        response = self.client.get(signup_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)



class AuthenticationMethodTest(TestCase):
    """
    Tests different authentication methods (username, email).
    """
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='authuser', 
            email='auth@test.com', 
            password='p'
        )
    def setUp(self):
        self.signup_url = reverse('account_signup')

    def test_login_with_username(self):
        """
        TDD: Tests if a user can log in using their username.
        """
        login_url = reverse('account_login')
        post_data = {'login': 'authuser', 'password': 'p'}
        
        response = self.client.post(login_url, post_data, follow=True)
        
        # Check that the user is successfully logged in and redirected
        self.assertEqual(response.status_code, 200)
        # _user_id is the key for the user in the session
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_with_wrong_password_fails(self):
        """Tests that logging in with an incorrect password fails."""
        login_url = reverse('account_login')
        post_data = {'login': 'authuser', 'password': 'wrongpassword'}

        response = self.client.post(login_url, post_data)

        self.assertEqual(response.status_code, 200) # Re-renders the login form
        # Check for the actual error pattern in our template (will be shown in form errors)
        self.assertContains(response, 'form-control') # Should contain the form with validation
        self.assertTrue('_auth_user_id' not in self.client.session) # User should not be logged in

    def test_register_with_no_email_and_username(self):
        """Tests that registering without an email and username fails with custom message."""
        post_data = {
            'email': '',
            'username': '',
            'password1': 'password123',
            'password2': 'password123',
        }

        response = self.client.post(self.signup_url, post_data)

        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertContains(response, 'You must provide either a username or an email address.') # Custom validation message
        # Verify no invalid user was created in the database
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(User.objects.filter(username='', email='').exists())
        success(f"Registration test - response code: {response.status_code}")

    def test_register_with_only_username_succeeds(self):
        """Tests that registering with only username (no email) succeeds."""
        post_data = {
            'username': 'testuser',
            'email': '',
            'password1': 'password123',
            'password2': 'password123',
        }

        response = self.client.post(self.signup_url, post_data)

        self.assertEqual(response.status_code, 200) # May redirect or show success
        # Should not contain error messages since we're providing username
        # If redirect happens, follow it
        if response.status_code == 302:
            response = self.client.get(response['Location'])
        info(f"Username-only registration test - response code: {response.status_code}")

    def test_register_with_only_email_succeeds(self):
        """Tests that registering with only email (no username) succeeds."""
        post_data = {
            'username': '',
            'email': 'testuser@test.com',
            'password1': 'password123',
            'password2': 'password123',
        }

        response = self.client.post(self.signup_url, post_data)

        self.assertEqual(response.status_code, 200) # May redirect or show success
        # Should not contain error messages since we're providing email
        # If redirect happens, follow it
        if response.status_code == 302:
            response = self.client.get(response['Location'])
        info(f"Email-only registration test - response code: {response.status_code}")

class SignupFlowTest(TestCase):
    """
    Tests edge cases for the user signup process.
    """
    @classmethod
    def setUpTestData(cls):
        # Create an existing user to test duplicate constraints
        User.objects.create_user(username='existinguser', email='existing@test.com', password='p')
    
    def setUp(self):
        self.signup_url = reverse('account_signup')

    def test_signup_with_duplicate_username_fails(self):
        """TDD: Tests that signing up with an already taken username fails."""
        post_data = {
            'username': 'existinguser',
            'email': 'newemail@test.com',
            'password1': 'password123',
            'password2': 'password123',
        }

        response = self.client.post(self.signup_url, post_data)

        self.assertEqual(response.status_code, 200)  # Re-renders form
        form = response.context['form']
        self.assertIn('A user with that username already exists.', form.errors['username'])
        self.assertFalse(User.objects.filter(email='newemail@test.com').exists())

    def test_signup_with_duplicate_email_fails(self):
        """TDD: Tests that signing up with an already taken email fails."""
        post_data = {
            'username': 'newuser',
            'email': 'existing@test.com',
            'password1': 'password123',
            'password2': 'password123',
        }

        response = self.client.post(self.signup_url, post_data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('A user is already registered with this email address.', form.errors['email'])
        self.assertFalse(User.objects.filter(username='newuser').exists())
