from django.test import TestCase
from django.conf import settings
from apps.accounts.views import User
from apps.boards.models import Board, List, Card, Membership

max_board_per_user = settings.MAX_BOARDS_PER_USER
max_member_per_board = settings.MAX_MEMBERS_PER_BOARD
max_membership_per_user = settings.MAX_MEMBERSHIP_PER_USER


class BaseTestCase(TestCase):
    def setUp(self):
        # Users
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.user2 = User.objects.create_user('testuser2', email='test2@example.com', password='password2')
        
        # Boards
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')
        self.board2 = Board.objects.create(owner=self.user, title='Test Board 2', color='green')
        self.board3 = Board.objects.create(owner=self.user, title='Test Board 3', color='red')
        self.board4 = Board.objects.create(owner=self.user, title='Test Board 4', color='orange')
        self.board5 = Board.objects.create(owner=self.user, title='Test Board 5', color='yellow')
        self.board6 = Board.objects.create(owner=self.user, title='Test Board 6', color='violet')
        self.board7 = Board.objects.create(owner=self.user, title='Test Board 7', color='indigo')
        self.board8 = Board.objects.create(owner=self.user, title='Test Board 8', color='cyan')
        self.board9 = Board.objects.create(owner=self.user, title='Test Board 9', color='magenta')

        # lists
        self.list = List.objects.create(board=self.board, title='Test List', order=1)
        self.list2 = List.objects.create(board=self.board, title='Test List 2', order=2)
        self.list3 = List.objects.create(board=self.board, title='Test List 3', order=3)
        self.list4 = List.objects.create(board=self.board, title='Test List 4', order=4)
        self.list5 = List.objects.create(board=self.board, title='Test List 5', order=5)
        self.list6 = List.objects.create(board=self.board, title='Test List 6', order=6)
        self.list7 = List.objects.create(board=self.board, title='Test List 7', order=7)
        self.list8 = List.objects.create(board=self.board, title='Test List 8', order=8)
        self.list9 = List.objects.create(board=self.board, title='Test List 9', order=9)

        # cards
        self.card = Card.objects.create(list=self.list, title='Test Card', order=1)
        self.card2 = Card.objects.create(list=self.list, title='Test Card 2', order=2)
        self.card3 = Card.objects.create(list=self.list, title='Test Card 3', order=3)
        self.card4 = Card.objects.create(list=self.list, title='Test Card 4', order=4)
        self.card5 = Card.objects.create(list=self.list, title='Test Card 5', order=5)
        self.card6 = Card.objects.create(list=self.list, title='Test Card 6', order=6)
        self.card7 = Card.objects.create(list=self.list, title='Test Card 7', order=7)
        self.card8 = Card.objects.create(list=self.list, title='Test Card 8', order=8)
        self.card9 = Card.objects.create(list=self.list, title='Test Card 9', order=9)

        # memberships
        self.membership = Membership.objects.create(user=self.user, board=self.board, role=Membership.ROLE_OWNER)
        self.membership2 = Membership.objects.create(user=self.user2, board=self.board, role=Membership.ROLE_MEMBER)
        self.membership3 = Membership.objects.create(user=self.user, board=self.board2, role=Membership.ROLE_MEMBER)
        self.membership4 = Membership.objects.create(user=self.user, board=self.board3, role=Membership.ROLE_MEMBER)
        self.membership5 = Membership.objects.create(user=self.user, board=self.board4, role=Membership.ROLE_MEMBER)
        self.membership6 = Membership.objects.create(user=self.user, board=self.board5, role=Membership.ROLE_MEMBER)
        self.membership7 = Membership.objects.create(user=self.user, board=self.board6, role=Membership.ROLE_MEMBER)
        self.membership8 = Membership.objects.create(user=self.user, board=self.board7, role=Membership.ROLE_MEMBER)
        self.membership9 = Membership.objects.create(user=self.user, board=self.board8, role=Membership.ROLE_MEMBER)
        self.membership10 = Membership.objects.create(user=self.user, board=self.board9, role=Membership.ROLE_MEMBER)
