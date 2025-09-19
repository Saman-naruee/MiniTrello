from django.test import TestCase
from django.conf import settings
from apps.accounts.models import User
from apps.boards.models import Board, List, Card, Membership


class BaseTestCase(TestCase):
    """
    A base class for all tests for all models in this project.
    To Reusablity.
    """
    pass



class BaseBoardTestCase(BaseTestCase):
    """
    A base TestCase providing a rich, pre-populated environment for all board-related tests.
    
    This class reduces code duplication by creating a comprehensive set of objects:
    - Users: An owner, a member, a non-member, and other users for various scenarios.
    - Boards: A primary board for detailed testing, a secondary board for access separation,
      and a set of additional boards to test user limits.
    - Lists & Cards: A populated structure within the primary board.
    - Memberships: Clear roles for users on the primary board.
    
    Test classes for specific views should inherit from this class.
    """
    # Get the maximum values from the settings
    max_board_per_user = settings.MAX_BOARDS_PER_USER
    max_member_per_board = settings.MAX_MEMBERS_PER_BOARD
    max_membership_per_user = settings.MAX_MEMBERSHIPS_PER_USER

    @classmethod
    def setUpTestData(cls):
        """Create all common objects used across multiple test classes."""
        cls._create_users()
        cls._create_boards()
        cls._create_memberships()
        cls._create_lists_and_cards()


    @classmethod
    def _create_users(cls):
        """Create a standard set of users with clear roles."""
        cls.owner = User.objects.create_user(username='board_owner', email='owner@test.com', password='p')
        cls.member = User.objects.create_user(username='board_member', email='member@test.com', password='p')
        cls.non_member = User.objects.create_user(username='non_member', email='nonmember@test.com', password='p')
        # This user will own the secondary board and can be used for invitation/membership limit tests
        cls.another_user = User.objects.create_user(username='another_user', email='another@test.com', password='p')

    @classmethod
    def _create_boards(cls):
        """Create a primary board, a secondary board, and extra boards for limit testing."""
        # The main board used for most tests (CRUD on lists, cards, etc.)
        cls.board = Board.objects.create(
            owner=cls.owner,
            title='Primary Test Board',
            color='blue'
        )

        # A secondary board to test access control (e.g., owner/member of cls.board cannot see this)
        cls.other_board = Board.objects.create(
            owner=cls.another_user,
            title='Secondary Board (Private)',
            color='green'
        )

        # Create boards up to the user limit for the owner user, for testing creation limits
        cls.owner_extra_boards = []
        # We already created one board for the owner, so we create MAX-1 more.
        for i in range(cls.max_board_per_user - 1):
            board = Board.objects.create(
                owner=cls.owner,
                title=f'Owner Board {i+2}',
                color='red'
            )
            cls.owner_extra_boards.append(board)

    @classmethod
    def _create_memberships(cls):
        """Create memberships to define user roles on the primary board."""
        # The owner is automatically a member with the 'Owner' role.
        Membership.objects.create(user=cls.owner, board=cls.board, role=Membership.ROLE_OWNER)
        # Add 'member' user to the primary board with the 'Member' role.
        Membership.objects.create(user=cls.member, board=cls.board, role=Membership.ROLE_MEMBER)

    @classmethod
    def _create_lists_and_cards(cls):
        """Create a basic structure of lists and cards within the primary board."""
        cls.list1 = List.objects.create(board=cls.board, title='To Do', order=1)
        cls.list2 = List.objects.create(board=cls.board, title='In Progress', order=2)
        
        cls.card1 = Card.objects.create(list=cls.list1, title='Card 1 in To Do', order=1)
        cls.card2 = Card.objects.create(list=cls.list1, title='Card 2 in To Do', order=2)
        cls.card3 = Card.objects.create(list=cls.list2, title='Card 3 in Progress', order=1)
        
        # Add assignees to a card for testing permissions/display
        cls.card1.assignees.add(cls.owner, cls.member)

    def setUp(self):
        """This method is run before each individual test, ensuring a clean client."""
        # It's good practice to not log in any user by default.
        # Each test method will explicitly log in the user whose perspective it is testing.
        pass
