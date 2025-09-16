from django.test import TestCase
from apps.accounts.models import User
from ..models import Board, List, Card, Membership

class BoardModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')
        self.list = List.objects.create(board=self.board, title='Test List', order=1)
        self.card = Card.objects.create(list=self.list, title='Test Card', order=1)
        self.membership = Membership.objects.create(user=self.user, board=self.board, role=Membership.ROLE_OWNER)

    def test_board_creation(self):
        """
        Test that a Board can be created successfully.
        """
        self.assertIsInstance(self.board, Board)
        self.assertEqual(self.board.title, 'Test Board')
        self.assertEqual(self.board.color, 'blue')
        self.assertEqual(self.board.owner, self.user)
    
    def test_list_creation(self):
        """
        Test that a List can be created successfully.
        """
        self.assertIsInstance(self.list, List)
        self.assertEqual(self.list.title, 'Test List')
        self.assertEqual(self.list.board, self.board)
        self.assertEqual(self.list.order, 1)
    
    def test_card_creation(self):
        """
        Test that a Card can be created successfully.
        """
        self.assertIsInstance(self.card, Card)
        self.assertEqual(self.card.title, 'Test Card')
        self.assertEqual(self.card.list, self.list)
        self.assertEqual(self.card.order, 1)
    
    def test_membership_creation(self):
        """
        Test that a Membership for a board instance can be created successfully.
        """
        self.assertIsInstance(self.membership, Membership)
        self.assertEqual(self.membership.user, self.user)
        self.assertEqual(self.membership.board, self.board)
        self.assertEqual(self.membership.role, Membership.ROLE_OWNER)



class ListModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')
        self.list_obj = List.objects.create(board=self.board, title='Test List', order=1)

    
    def test_list_str_representation(self):
        self.assertEqual(str(self.list_obj), f'{self.list_obj.title} - {self.board.title}')



class CardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')
        self.list_obj = List.objects.create(board=self.board, title='Test List', order=1)
        self.card = Card.objects.create(list=self.list_obj, title='Test Card', order=1)


    def test_card_move_to_different_list(self):
        new_list = List.objects.create(board=self.board, title='New List', order=2)
        self.card.move_to(new_list)
        self.assertEqual(self.card.list, new_list)
