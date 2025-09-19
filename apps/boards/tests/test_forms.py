from django.test import TestCase
from apps.boards.forms import BoardForm, ListForm, CardForm, MembershipForm
from apps.boards.models import Board, Membership, Card, List
from apps.accounts.models import User

class BoardFormTest(TestCase):
    def test_valid_data(self):
        form = BoardForm(data={'title': 'Test Board', 'color': 'blue'})
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = BoardForm(data={'title': '', 'color': 'blue'})
        self.assertFalse(form.is_valid())

    def test_title_length_validation(self):
        form = BoardForm(data={'title': 'ab', 'color': 'blue'})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class ListFormTest(TestCase):
    def test_valid_data(self):
        form = ListForm(data={'title': 'Test List'})
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = ListForm(data={'title': ''})
        self.assertFalse(form.is_valid())

    def test_title_length_validation(self):
        form = ListForm(data={'title': 'a'})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class CardFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')

    def test_valid_data(self):
        form = CardForm(data={'title': 'Test Card', 'priority': 50}, board=self.board)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = CardForm(data={'title': '', 'priority': 50}, board=self.board)
        self.assertFalse(form.is_valid())

    def test_due_date_validation(self):
        form = CardForm(data={'title': 'Test Card', 'priority': 50, 'due_date': '2020-01-01'}, board=self.board)
        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)


class MembershipFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', email='test@example.com', password='password')
        self.board = Board.objects.create(owner=self.user, title='Test Board', color='blue')

    def test_valid_data(self):
        new_user = User.objects.create_user('newuser', email='newuser@example.com', password='password')
        form = MembershipForm(data={'user': new_user.id, 'role': Membership.ROLE_MEMBER}, board=self.board)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = MembershipForm(data={'user': '', 'role': Membership.ROLE_MEMBER}, board=self.board)
        self.assertFalse(form.is_valid())

    def test_user_already_member(self):
        new_user = User.objects.create_user('newuser2', email='newuser2@example.com', password='password')
        Membership.objects.create(user=new_user, board=self.board, role=Membership.ROLE_MEMBER)
        form = MembershipForm(data={'user': new_user.id, 'role': Membership.ROLE_MEMBER}, board=self.board)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
