from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.boards.models import Board, List, Card, Membership

class BoardViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_login(self.user)
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')

    def test_board_list_view(self):
        """
        Test that the board list view is accessible.
        """
        response = self.client.get(reverse('boards:boards_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'boards/list.html')
