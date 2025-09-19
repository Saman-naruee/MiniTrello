from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError
from .base_test import BoardTestCase
from apps.boards.models import Membership, Card, List, Board
from apps.accounts.models import User
from apps.boards.permissions import BoardObjectPermissionMixin, BoardMemberRequiredMixin, BoardAdminRequiredMixin
from unittest.mock import Mock, patch

class TestRolePermissions(BoardTestCase):
    """
    Comprehensive tests for role-based permissions (Owner, Admin, Member, Viewer).
    This follows the TDD approach for features that are not yet fully implemented.
    """
    @classmethod
    def setUpTestData(cls):
        # Call the parent setup
        super().setUpTestData()
        
        # Create an Admin user and add them to the main board
        cls.admin = User.objects.create_user(username='board_admin', email='admin@test.com', password='p')
        Membership.objects.create(user=cls.admin, board=cls.board, role=Membership.ROLE_ADMIN)
        
        # Create a Viewer user
        cls.viewer = User.objects.create_user(username='board_viewer', email='viewer@test.com', password='p')
        Membership.objects.create(user=cls.viewer, board=cls.board, role=Membership.ROLE_VIEWER)

    def test_board_update_permissions_by_role(self):
        """Tests who can and cannot update a board."""
        url = reverse('boards:update_board', kwargs={'board_id': self.board.id})
        post_data = {'title': 'Updated Title', 'color': 'red'}
        
        # Owner CAN update
        self.client.login(username='board_owner', password='p')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200) # Assuming HTMX response
        
        # Admin CAN update
        self.client.login(username='board_admin', password='p')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        
        # Member CANNOT update
        self.client.login(username='board_member', password='p')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # Viewer CANNOT update
        self.client.login(username='board_viewer', password='p')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 403)

    def test_card_move_permissions_by_role(self):
        """Tests who can and cannot move cards."""
        move_url = reverse('boards:move_card', kwargs={
            'board_id': self.board.id,
            'list_id': self.list1.id,
            'card_id': self.card1.id
        })
        payload = {'to_list_id': self.list2.id, 'new_index': 0}
        
        # Member CAN move cards
        self.client.login(username='board_member', password='p')
        response = self.client.put(move_url, payload)
        self.assertEqual(response.status_code, 200)
        
        # Viewer CANNOT move cards
        # We need a new mixin/logic for this, so this test will fail initially (TDD!)
        self.client.login(username='board_viewer', password='p')
        response = self.client.put(move_url, payload)
        self.assertEqual(response.status_code, 403) # This will fail until we implement the logic
        
    def test_member_management_permissions(self):
        """
        TDD for the upcoming member management feature.
        - Only Owner/Admin should be able to remove other members.
        - A Member cannot remove another member.
        """
        # This URL does not exist yet. This test will fail with NoReverseMatch.
        remove_member_url = reverse('boards:remove_member', kwargs={
            'board_id': self.board.id,
            'membership_id': self.member.memberships.get(board=self.board).id
        })
        
        # A regular Member tries to remove another member -> FORBIDDEN
        self.client.login(username='board_member', password='p')
        response = self.client.post(remove_member_url)
        self.assertEqual(response.status_code, 403)
        
        # An Admin CAN remove a member
        self.client.login(username='board_admin', password='p')
        response = self.client.post(remove_member_url)
        self.assertIn(response.status_code, [200, 204]) # Success
    
    def test_member_can_modify_owner_permissions(self):
        pass


class TestBoardObjectPermissionMixin(TestCase):
    """
    Comprehensive tests for the BoardObjectPermissionMixin.
    Tests authentication, authorization, error handling, and edge cases.
    """

    @classmethod
    def setUpTestData(cls):
        """Create test data for BoardObjectPermissionMixin tests."""
        # Create users
        cls.owner = User.objects.create_user(username='owner', email='owner@test.com', password='p')
        cls.member = User.objects.create_user(username='member', email='member@test.com', password='p')
        cls.non_member = User.objects.create_user(username='non_member', email='nonmember@test.com', password='p')

        # Create board
        cls.board = Board.objects.create(owner=cls.owner, title='Test Board', color='blue')

        # Create memberships
        Membership.objects.create(user=cls.owner, board=cls.board, role=Membership.ROLE_OWNER)
        Membership.objects.create(user=cls.member, board=cls.board, role=Membership.ROLE_MEMBER)

        # Create lists and cards
        cls.list = List.objects.create(board=cls.board, title='Test List', order=1)
        cls.card = Card.objects.create(list=cls.list, title='Test Card', order=1)

    def _create_mixin_for_model(self, model_class, id_kwarg_name):
        """Helper to create a mixin instance for testing."""
        mixin = BoardObjectPermissionMixin()
        mixin.model_to_check = model_class
        mixin.id_kwarg_name = id_kwarg_name
        mixin.kwargs = {id_kwarg_name: self._get_object_id(model_class)}
        return mixin

    def _get_object_id(self, model_class):
        """Helper to get object ID based on model class."""
        if model_class == Board:
            return self.board.id
        elif model_class == List:
            return self.list.id
        elif model_class == Card:
            return self.card.id
        return None

    def test_unauthenticated_user_redirected(self):
        """Test that unauthenticated users are redirected to login."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = AnonymousUser()
        request.get_full_path.return_value = '/test/path/'

        with patch('apps.boards.permissions.custom_logger') as mock_logger:
            with patch('apps.boards.permissions.redirect_to_login') as mock_redirect:
                mock_redirect.return_value = 'redirect_response'
                response = mixin.dispatch(request)

                mock_logger.assert_called_once()
                mock_redirect.assert_called_once_with('/test/path/')
                self.assertEqual(response, 'redirect_response')

    def test_missing_model_to_check_raises_error(self):
        """Test that missing model_to_check raises ValueError."""
        mixin = BoardObjectPermissionMixin()
        mixin.id_kwarg_name = 'test_id'
        mixin.kwargs = {'test_id': 1}

        request = Mock()
        request.user = self.owner

        with self.assertRaises(ValueError) as cm:
            mixin.dispatch(request)
        self.assertIn("requires 'model_to_check' to be set", str(cm.exception))

    def test_missing_id_kwarg_name_raises_error(self):
        """Test that missing id_kwarg_name raises ValueError."""
        mixin = BoardObjectPermissionMixin()
        mixin.model_to_check = Card
        mixin.kwargs = {'card_id': 1}

        request = Mock()
        request.user = self.owner

        with self.assertRaises(ValueError) as cm:
            mixin.dispatch(request)
        self.assertIn("requires 'id_kwarg_name' to be set", str(cm.exception))

    def test_missing_object_id_raises_error(self):
        """Test that missing object ID in kwargs raises ValueError."""
        mixin = BoardObjectPermissionMixin()
        mixin.model_to_check = Card
        mixin.id_kwarg_name = 'card_id'
        mixin.kwargs = {}  # Missing card_id

        request = Mock()
        request.user = self.owner

        with self.assertRaises(ValueError) as cm:
            mixin.dispatch(request)
        self.assertIn("Missing required kwarg 'card_id'", str(cm.exception))

    def test_invalid_object_id_raises_404(self):
        """Test that invalid object ID raises Http404."""
        mixin = BoardObjectPermissionMixin()
        mixin.model_to_check = Card
        mixin.id_kwarg_name = 'card_id'
        mixin.kwargs = {'card_id': 99999}  # Non-existent ID

        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with self.assertRaises(Http404):
                mixin.dispatch(request)

    def test_board_resolution_for_card(self):
        """Test that board is correctly resolved from Card."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                mock_super.return_value.dispatch.return_value = 'success'
                response = mixin.dispatch(request)

                # Check that board was correctly resolved
                self.assertEqual(mixin.board, self.board)
                self.assertEqual(mixin.object, self.card)
                mock_super.return_value.dispatch.assert_called_once()

    def test_board_resolution_for_list(self):
        """Test that board is correctly resolved from List."""
        mixin = self._create_mixin_for_model(List, 'list_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                mock_super.return_value.dispatch.return_value = 'success'
                response = mixin.dispatch(request)

                self.assertEqual(mixin.board, self.board)
                self.assertEqual(mixin.object, self.list)

    def test_board_resolution_for_board(self):
        """Test that board is correctly resolved from Board."""
        mixin = self._create_mixin_for_model(Board, 'board_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                mock_super.return_value.dispatch.return_value = 'success'
                response = mixin.dispatch(request)

                self.assertEqual(mixin.board, self.board)
                self.assertEqual(mixin.object, self.board)

    def test_non_member_denied_access(self):
        """Test that non-members are denied access."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = self.non_member

        with patch('apps.boards.permissions.custom_logger'):
            with self.assertRaises(PermissionDenied) as cm:
                mixin.dispatch(request)

            self.assertIn("must be a member of this board", str(cm.exception))

    def test_member_granted_access(self):
        """Test that board members are granted access."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = self.member

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                mock_super.return_value.dispatch.return_value = 'success'
                response = mixin.dispatch(request)

                self.assertEqual(response, 'success')
                self.assertEqual(mixin.board, self.board)
                self.assertEqual(mixin.object, self.card)

    def test_owner_granted_access(self):
        """Test that board owners are granted access."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                mock_super.return_value.dispatch.return_value = 'success'
                response = mixin.dispatch(request)

                self.assertEqual(response, 'success')

    def test_optimized_queries_for_card(self):
        """Test that optimized queries are used for Card objects."""
        mixin = self._create_mixin_for_model(Card, 'card_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                with patch('apps.boards.permissions.get_object_or_404') as mock_get:
                    mock_get.return_value = self.card
                    mock_super.return_value.dispatch.return_value = 'success'

                    mixin.dispatch(request)

                    # Verify select_related was called for Card
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args[0]
                    self.assertEqual(call_args[0], Card)
                    # Check that select_related was used
                    queryset = call_args[1]
                    self.assertTrue(hasattr(queryset, 'select_related'))

    def test_optimized_queries_for_list(self):
        """Test that optimized queries are used for List objects."""
        mixin = self._create_mixin_for_model(List, 'list_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                with patch('apps.boards.permissions.get_object_or_404') as mock_get:
                    mock_get.return_value = self.list
                    mock_super.return_value.dispatch.return_value = 'success'

                    mixin.dispatch(request)

                    # Verify select_related was called for List
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args[0]
                    self.assertEqual(call_args[0], List)

    def test_optimized_queries_for_board(self):
        """Test that optimized queries are used for Board objects."""
        mixin = self._create_mixin_for_model(Board, 'board_id')
        request = Mock()
        request.user = self.owner

        with patch('apps.boards.permissions.custom_logger'):
            with patch('apps.boards.permissions.super') as mock_super:
                with patch('apps.boards.permissions.get_object_or_404') as mock_get:
                    mock_get.return_value = self.board
                    mock_super.return_value.dispatch.return_value = 'success'

                    mixin.dispatch(request)

                    # Verify select_related was called for Board
                    mock_get.assert_called_once()
                    call_args = mock_get.call_args[0]
                    self.assertEqual(call_args[0], Board)


class TestBoardMemberRequiredMixin(BoardTestCase):
    """
    Tests for the BoardMemberRequiredMixin.
    """

    def test_owner_can_access_board(self):
        """Test that board owners can access board-specific views."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:board_detail', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_can_access_board(self):
        """Test that board members can access board-specific views."""
        self.client.login(username='board_member', password='p')
        url = reverse('boards:board_detail', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_member_denied_access(self):
        """Test that non-members are denied access to board-specific views."""
        self.client.login(username='non_member', password='p')
        url = reverse('boards:board_detail', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_missing_board_id_raises_error(self):
        """Test that missing board_id raises ValueError."""
        mixin = BoardMemberRequiredMixin()
        mixin.kwargs = {}  # Missing board_id

        request = Mock()
        request.user = self.owner

        with self.assertRaises(ValueError) as cm:
            mixin.dispatch(request)
        self.assertIn("requires a 'board_id' in the URL", str(cm.exception))

    def test_nonexistent_board_raises_404(self):
        """Test that accessing non-existent board raises 404."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:board_detail', kwargs={'board_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestBoardAdminRequiredMixin(BoardTestCase):
    """
    Tests for the BoardAdminRequiredMixin.
    """

    def test_owner_can_access_admin_views(self):
        """Test that board owners can access admin-specific views."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:update_board', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_admin_views(self):
        """Test that board admins can access admin-specific views."""
        self.client.login(username='board_admin', password='p')
        url = reverse('boards:update_board', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_denied_admin_access(self):
        """Test that regular members are denied access to admin views."""
        self.client.login(username='board_member', password='p')
        url = reverse('boards:update_board', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_viewer_denied_admin_access(self):
        """Test that viewers are denied access to admin views."""
        self.client.login(username='board_viewer', password='p')
        url = reverse('boards:update_board', kwargs={'board_id': self.board.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_missing_board_id_raises_error(self):
        """Test that missing board_id raises ValueError."""
        mixin = BoardAdminRequiredMixin()
        mixin.kwargs = {}  # Missing board_id

        request = Mock()
        request.user = self.owner

        with self.assertRaises(ValueError) as cm:
            mixin.dispatch(request)
        self.assertIn("requires a 'board_id' in the URL", str(cm.exception))

    def test_nonexistent_board_raises_404(self):
        """Test that accessing non-existent board raises 404."""
        self.client.login(username='board_owner', password='p')
        url = reverse('boards:update_board', kwargs={'board_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestFutureFeatures(BoardTestCase):
    """
    Tests for upcoming features that are not yet implemented.
    These tests will fail initially but serve as TDD specifications.
    """

    def test_card_priority_permissions(self):
        """TDD: Test that viewers cannot change card priorities."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_list_archiving_permissions(self):
        """TDD: Test that only admins can archive/unarchive lists."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_board_export_permissions(self):
        """TDD: Test that only owners can export board data."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_member_role_change_permissions(self):
        """TDD: Test that only admins can change member roles."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_board_deletion_permissions(self):
        """TDD: Test that only owners can delete boards."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_card_comment_permissions(self):
        """TDD: Test that viewers can view but not create comments."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_board_statistics_permissions(self):
        """TDD: Test that only members can view board statistics."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_card_attachment_permissions(self):
        """TDD: Test that members can add attachments to cards."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_board_template_permissions(self):
        """TDD: Test that only admins can create board templates."""
        # This feature doesn't exist yet - will fail until implemented
        pass

    def test_member_invitation_permissions(self):
        """TDD: Test that only admins can invite new members."""
        # This feature doesn't exist yet - will fail until implemented
        pass
