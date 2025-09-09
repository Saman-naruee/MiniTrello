from django.conf import settings
from django.test import TestCase
from .models import Board, List, Card, Membership
from apps.accounts.models import User

class BoardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'testuser@example.com', 'password')
        self.board = Board.objects.create(title='Test Board', owner=self.user)
        self.list1 = List.objects.create(title='To-do', board=self.board, order=1)
        self.list2 = List.objects.create(title='In Progress', board=self.board, order=2)
        self.list3 = List.objects.create(title='Done', board=self.board, order=3)
        self.card1 = Card.objects.create(title='Card 1', list=self.list1, order=1)
        self.card2 = Card.objects.create(title='Card 2', list=self.list1, order=2)
        self.card3 = Card.objects.create(title='Card 3', list=self.list2, order=1)
        self.card4 = Card.objects.create(title='Card 4', list=self.list2, order=1)
        self.card5 = Card.objects.create(title='Card 5', list=self.list3, order=1)

    def test_board_lists(self):
        self.assertEqual(self.board.lists.count(), 3)
        self.assertEqual(self.board.lists.filter(title='To-do').count(), 1)
        self.assertEqual(self.board.lists.filter(title='In Progress').count(), 1)
        self.assertEqual(self.board.lists.filter(title='Done').count(), 1)

    def test_card_lists(self):
        self.assertEqual(self.list1.cards.count(), 2)
        self.assertEqual(self.list2.cards.count(), 2)
        self.assertEqual(self.list3.cards.count(), 1)

    def test_card_move(self):
        self.card1.move_to(self.list2)
        self.assertEqual(self.list1.cards.count(), 1)
        self.assertEqual(self.list2.cards.count(), 3)

    def test_board_members(self):
        user2 = User.objects.create_user('testuser2', 'testuser2@example.com', 'password')
        user3 = User.objects.create_user('testuser3', 'testuser3@example.com', 'password')
        Membership.objects.create(user=user2, board=self.board, role=Membership.ROLE_MEMBER)
        Membership.objects.create(user=user3, board=self.board, role=Membership.ROLE_VIEWER)
        self.assertEqual(self.board.memberships.count(), 3)
        self.assertEqual(self.board.memberships.filter(user=user2).count(), 1)
        self.assertEqual(self.board.memberships.filter(user=user3).count(), 1)
        self.assertEqual(self.board.memberships.filter(role=Membership.ROLE_MEMBER).count(), 1)
        self.assertEqual(self.board.memberships.filter(role=Membership.ROLE_VIEWER).count(), 1)

