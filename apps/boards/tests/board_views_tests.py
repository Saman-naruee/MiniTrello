from django.test import TestCase, Client
from django.urls import reverse
import random
from base_test import BaseTestCase

from apps.accounts.models import User
from apps.boards.models import Board, List, Card, Membership
    
class BoardViewsTests(TestCase): # inherit from BaseTestCase
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email='test@example', username='testuser', password='testpass')
        self.client.force_login(self.user)
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')
        self.user2 = User.objects.create_user(email='test2@example', username='testuser2', password='testpass2')
        self.client.force_login(self.user2)
        self.list_obj = List.objects.create(board=self.board, title='Test List', order=1)
        self.card = Card.objects.create(list=self.list_obj, title='Test Card', order=1)
        self.membership = Membership.objects.create(user=self.user, board=self.board, role=Membership.ROLE_OWNER)

    def test_board_list_view(self):
        """
        Test that the board list view is accessible.
        """
        response = self.client.get(reverse('boards:boards_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'boards/list.html')
    
    def test_board_list_view_for_unregistered_user(self):
        """
        Test that the board list view is accessible for unregistered users.
        """
        self.client.logout()
        response = self.client.get(reverse('boards:boards_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/boards/')

    def test_board_detail_view(self):
        """
        Test that the board detail view is accessible.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse('boards:board_detail', args=[self.board.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'boards/detail.html')

    def test_board_detail_view_for_unregistered_user(self):
        """
        Test that the board detail view is accessible for unregistered users.
        """
        self.client.logout()
        response = self.client.get(reverse('boards:board_detail', args=[self.board.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next=/boards/{self.board.id}/')
    
    def test_board_detail_view_for_non_owner(self):
        """
        Test that the board detail view is accessible for non-owners.
        """
        self.client.logout()
        self.client.force_login(self.user2)
        board_id = random.randint(1, 100000)
        response = self.client.get(reverse('boards:board_detail', args=[board_id]))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_board_owner_is_member(self):
        """
        Test that the board owner is a member of the board.
        """
        self.assertEqual(self.membership.user, self.user)
        self.assertEqual(self.membership.board, self.board)
        self.assertEqual(self.membership.role, Membership.ROLE_OWNER)
