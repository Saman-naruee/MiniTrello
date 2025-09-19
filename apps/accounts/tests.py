from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import User
from allauth.account.models import EmailAddress
from django.core import mail

class AccountAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('account_signup')
        self.login_url = reverse('account_login')
        self.test_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        
    def test_signup_with_username_only(self):
        """Test user can register with just username and password"""
        data = {
            'username': 'usernameonly',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Successful redirect
        self.assertTrue(User.objects.filter(username='usernameonly').exists())
        user = User.objects.get(username='usernameonly')
        self.assertFalse(user.email)  # Email should be empty

    def test_signup_with_email(self):
        """Test user can register with email and it triggers verification"""
        response = self.client.post(self.signup_url, self.test_user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
        self.assertEqual(len(mail.outbox), 1)  # Verification email sent
        
    def test_existing_email_redirect(self):
        """Test that trying to register with existing email redirects to login"""
        # Create user first
        User.objects.create_user(
            username='existing',
            email='test@example.com',
            password='testpass123'
        )
        
        # Try to register with same email
        response = self.client.post(self.signup_url, self.test_user_data)
        self.assertRedirects(response, self.login_url)

    def test_login_with_username_no_email(self):
        """Test user can login with username even without verified email"""
        user = User.objects.create_user(
            username='logintest',
            password='testpass123'
        )
        
        response = self.client.post(self.login_url, {
            'login': 'logintest',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Successful redirect
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_email_verification_flow(self):
        """Test email verification process"""
        # Create unverified user
        user = User.objects.create_user(**self.test_user_data)
        email = EmailAddress.objects.create(
            user=user,
            email=self.test_user_data['email'],
            primary=True,
            verified=False
        )
        
        # Get verification email
        self.assertEqual(len(mail.outbox), 0)
        email.send_confirmation()
        self.assertEqual(len(mail.outbox), 1)
        
        # Extract confirmation key from email
        email_lines = mail.outbox[0].body.split('\n')
        confirmation_link = [l for l in email_lines if 'confirm-email' in l][0]
        key = confirmation_link.split('/')[-2]
        
        # Verify email
        confirm_url = reverse('account_confirm_email', args=[key])
        response = self.client.post(confirm_url)
        email.refresh_from_db()
        self.assertTrue(email.verified)

    def test_unique_username_generation(self):
        """Test unique username generation when duplicate exists"""
        # Create first user
        User.objects.create_user(username='testuser', password='testpass123')
        
        # Try to create another user with same username
        data = self.test_user_data.copy()
        response = self.client.post(self.signup_url, data)
        
        # Check that a new user was created with modified username
        self.assertTrue(User.objects.filter(username__startswith='testuser').count() == 2)
        
    def test_ajax_authentication(self):
        """Test AJAX authentication responses"""
        # Create user
        User.objects.create_user(**self.test_user_data)
        
        # Test AJAX login
        response = self.client.post(
            self.login_url,
            {'login': 'testuser', 'password': 'testpass123'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('redirect' in response.json())

class UserModelTests(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            preferred_language='en'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.preferred_language, 'en')
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.is_active)

    def test_user_str_representation(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.assertEqual(str(user), 'testuser')

class CustomAdapterTests(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_inactive_user_ajax_response(self):
        """Test AJAX response for inactive user"""
        user = User.objects.create_user(
            username='inactive',
            password='testpass123',
            is_active=False
        )
        
        response = self.client.post(
            reverse('account_login'),
            {'login': 'inactive', 'password': 'testpass123'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.json())
        self.assertIn('errors', response.json()['form'])
