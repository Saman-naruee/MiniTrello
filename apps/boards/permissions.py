from django.views import View
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Max, Prefetch
from django.db import transaction
from django.template.loader import render_to_string
from custom_tools.logger import custom_logger
from .forms import *
from colorama import Fore
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.http import Http404
from .models import Board, List, Card, Membership



# Helper functions to avoid repetition
def get_user_boards(user):
    """Get all boards for a user with optimized queries"""
    boards = (
        Board.objects.filter(memberships__user=user, memberships__is_active=True)
        .select_related("owner")
        .prefetch_related("memberships")
        .distinct()
    )
    custom_logger(f"Retrieved {boards.count()} boards for user `{user.email}`")
    custom_logger(f"Boards: {boards}")
    return boards


def get_user_board(board_id, user):
    """Get a specific board for a user with permission check"""
    try:
        board = get_object_or_404(Board, id=board_id)
        return board if is_owner_or_member(board_id, user, Board) else False
    except Board.DoesNotExist:
        raise Http404("Board not found")

def get_board_lists(board):
    """Get all lists for a board with optimized queries and preloaded cards"""
    lists = (
        List.objects.filter(board=board)
        .select_related("board")
        .prefetch_related(
            Prefetch(
                'cards',
                queryset=Card.objects.prefetch_related("assignees").order_by("priority", "order"),
                to_attr='prefetched_cards'
            )
        )
        .order_by("order")
    )
    return lists


def get_user_list(list_id, user, board):
    """Get a specific list for a user with permission check, ensuring it belongs to the given board"""
    
    if is_owner_or_member(list_id, user, List):
        return get_object_or_404(
            List,
            id=list_id,
            board=board, # Explicitly filter by the board object
        )
    return False

def can_modify_board(board, user):
    """
    Check if user has permission to modify (update/delete) the board
    """
    # Check if user is owner
    if board.owner == user:
        return True
    
    # Check if user is admin
    membership = board.memberships.filter(user=user, is_active=True).first()
    custom_logger(f"method: can_modify_board/nMembership: {membership.role}", Fore.YELLOW)
    return membership and membership.role in [Membership.ROLE_OWNER, Membership.ROLE_ADMIN]

def is_owner_or_member(obj_id, user, model_class=None) -> bool:
    """
    Check if the user is the owner or a member of the object.
        . At this level created for Card, List, Board
    """
    if not user.is_authenticated:
        raise PermissionDenied("You must be logged in to perform this action.")
    
    
    result = False
    if model_class:
        if model_class == Card:
            board_of_this_card = model_class.objects.get(id=obj_id).list.board
            result = True if board_of_this_card.owner == user \
                or board_of_this_card.memberships.filter(user=user, is_active=True).exists()\
                else False

        elif model_class == List:
            board_of_this_list = model_class.objects.get(id=obj_id).board
            result = True if board_of_this_list.owner == user \
                or board_of_this_list.memberships.filter(user=user, is_active=True).exists()\
                else False
        elif model_class == Board:
            result = True if model_class.objects.get(id=obj_id).owner == user \
                or model_class.objects.get(id=obj_id).memberships.filter(user=user, is_active=True).exists()\
                else False

        if not result:
            raise PermissionDenied("You are not authorized to perform this action")
        return result
    raise ValidationError("Invalid model class")


@transaction.atomic
def get_user_card(card_id, user):
    """Get a specific card for a user with permission check"""
    is_o_or_m = is_owner_or_member(card_id, user, Card)
    custom_logger(is_o_or_m, Fore.MAGENTA)
    if is_o_or_m:
        if card_id:
            try:
                card = Card.objects.select_for_update().get(id=card_id)
                return card
            except Card.DoesNotExist:
                pass
    raise Http404("Card not found")


def get_next_order(model_class, filter_kwargs):
    """Get the next order number for a model"""
    max_order = model_class.objects.filter(**filter_kwargs).aggregate(
        max_order=Max('order')
    )['max_order'] or 0
    return max_order + 1


def render_partial_response(template_name, context):
    """Render a partial template and return JSON response"""
    html = render_to_string(template_name, context)
    return JsonResponse({"html": html})



class BoardMemberRequiredMixin:
    """
    A mixin that verifies the logged-in user is an active member of the board
    specified in the URL kwargs ('board_id'). This is for actions where any
    member (including owner, admin, member) has access.
    
    It fetches the board and attaches it to the view as `self.board`.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = self.kwargs.get('board_id')
        if not board_id:
            raise ValueError("BoardMemberRequiredMixin requires a 'board_id' in the URL.")

        self.board = get_object_or_404(Board, pk=board_id)

        is_member = self.board.memberships.filter(user=request.user, is_active=True).exists()
        
        if not is_member:
            raise PermissionDenied("You are not a member of this board.")
            
        return super().dispatch(request, *args, **kwargs)


class BoardAdminRequiredMixin:
    """
    A mixin that verifies the logged-in user has administrative privileges
    (owner or admin) on the board specified by 'board_id'.
    
    It fetches the board and attaches it to the view as `self.board`.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = self.kwargs.get('board_id')
        if not board_id:
            raise ValueError("BoardAdminRequiredMixin requires a 'board_id' in the URL.")
            
        self.board = get_object_or_404(Board.objects.select_related('owner'), pk=board_id)

        # A simple check for owner role first for efficiency.
        if self.board.owner == request.user:
            return super().dispatch(request, *args, **kwargs)

        # If not the owner, check for admin membership.
        try:
            membership = self.board.memberships.get(user=request.user, is_active=True)
            if membership.role not in [Membership.ROLE_OWNER, Membership.ROLE_ADMIN]:
                raise PermissionDenied("You must be an admin or owner to perform this action.")
        except Membership.DoesNotExist:
            # If no membership exists, they cannot be an admin.
            raise PermissionDenied("You are not a member of this board.")
        
        return super().dispatch(request, *args, **kwargs)




class BoardObjectPermissionMixin(View):
    # This mixin will be the new parent for almost all our views.
    
    # We define attributes that child views can override
    model_to_check = None # e.g., Card, List
    id_kwarg_name = None # e.g., 'card_id', 'list_id'

    def dispatch(self, request, *args, **kwargs):
        # 1. Check if user is authenticated
        if not request.user.is_authenticated:
            # Handle redirection...
            pass

        # 2. Get the object (Card, List, etc.) based on the attributes
        obj_id = self.kwargs.get(self.id_kwarg_name)
        obj = get_object_or_404(self.model_to_check, pk=obj_id)

        # 3. Find the board this object belongs to
        board = obj.list.board # Example for Card
        
        # 4. Check if the user is a member of that board
        if not board.memberships.filter(user=request.user, is_active=True).exists():
            raise PermissionDenied("You are not a member of this board.")
            
        # Attach objects to the view for easy access
        self.board = board
        self.object = obj
        
        return super().dispatch(request, *args, **kwargs)
