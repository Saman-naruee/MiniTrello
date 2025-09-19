from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import AccessMixin
from .models import Board, List, Card, Membership
from .permissions import can_modify_board, is_owner_or_member, get_user_board, get_user_list, get_user_card


class BoardAccessMixin(AccessMixin):
    """
    Mixin to check if the user is the owner or a member of the board.
    Assumes the view has a 'board_id' in kwargs.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = kwargs.get('board_id')
        if not board_id:
            raise Http404("Board ID not provided")

        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this board.")

        try:
            self.board = get_user_board(board_id, request.user)
        except Http404:
            raise Http404("Board not found")
        except PermissionDenied:
            raise Http404("Board not found")

        return super().dispatch(request, *args, **kwargs)


class BoardModifyMixin(BoardAccessMixin):
    """
    Mixin to check if the user can modify the board (owner or admin).
    Inherits from BoardAccessMixin to set self.board.
    """
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(self, 'board') and not can_modify_board(self.board, request.user):
            return self.handle_no_permission()
        return response


class ListAccessMixin(AccessMixin):
    """
    Mixin to check access to a list within a board.
    Assumes 'board_id' and 'list_id' in kwargs.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = kwargs.get('board_id')
        list_id = kwargs.get('list_id')
        if not board_id or not list_id:
            raise Http404("Board or List ID not provided")

        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this list.")

        try:
            self.board = get_user_board(board_id, request.user)
            self.list_obj = get_user_list(list_id, request.user, self.board)
        except Http404:
            raise Http404("List not found")
        except PermissionDenied:
            raise Http404("List not found")

        return super().dispatch(request, *args, **kwargs)


class CardAccessMixin(AccessMixin):
    """
    Mixin to check access to a card.
    Assumes 'card_id' in kwargs.
    """
    def dispatch(self, request, *args, **kwargs):
        card_id = kwargs.get('card_id')
        if not card_id:
            raise Http404("Card ID not provided")

        if not self.request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this card.")

        try:
            self.card = get_user_card(card_id, self.request.user)
        except Http404:
            raise Http404("Card not found")
        except PermissionDenied:
            raise Http404("Card not found")

        return super().dispatch(request, *args, **kwargs)


class BoardOwnerMixin(AccessMixin):
    """
    Mixin to check if the user is the owner of the board.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = kwargs.get('board_id')
        if not board_id:
            raise Http404("Board ID not provided")

        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this board.")

        board = get_object_or_404(Board, id=board_id)
        if board.owner != request.user:
            raise Http404("Board not found")

        self.board = board
        return super().dispatch(request, *args, **kwargs)
