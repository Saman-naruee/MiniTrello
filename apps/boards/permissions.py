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
    Verifies the logged-in user is an active member of the board.
    - If not a member, raises Http404 to hide the board's existence.
    - Attaches the board to the view as `self.board`.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = self.kwargs.get('board_id')
        if not board_id:
            raise ValueError("This mixin requires 'board_id' in the URL.")

        try:
            # Try to get the board only if the user is a member.
            self.board = Board.objects.filter(
                memberships__user=request.user, 
                memberships__is_active=True
            ).distinct().get(pk=board_id)
        except Board.DoesNotExist:
            # ❗❗❗ BEHAVIOR CHANGE: Raise Http404 for non-members.
            raise Http404("Board not found or you are not a member.")
            
        return super().dispatch(request, *args, **kwargs)

class BoardAdminRequiredMixin:
    """
    Verifies the logged-in user has admin privileges (owner or admin).
    - If not a member, raises Http404.
    - If a member but with an insufficient role, raises PermissionDenied (403).
    - Attaches the board to the view as `self.board`.
    """
    def dispatch(self, request, *args, **kwargs):
        board_id = self.kwargs.get('board_id')
        if not board_id:
            raise ValueError("This mixin requires 'board_id' in the URL.")

        try:
            # Same logic as above: find the board through membership first.
            board = Board.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True
            ).select_related('owner').distinct().get(pk=board_id)
        except Board.DoesNotExist:
            raise Http404("Board not found or you are not a member.")
        
        # Now that we know the user is a member, check their role.
        if board.owner == request.user:
            self.board = board
            return super().dispatch(request, *args, **kwargs)
        
        membership = board.memberships.get(user=request.user)
        if membership.role not in [Membership.ROLE_OWNER, Membership.ROLE_ADMIN]:
            # ❗❗❗ BEHAVIOR CHANGE: Raise 403 for insufficient role.
            raise PermissionDenied("You must be an admin or owner to perform this action.")
        
        self.board = board
        return super().dispatch(request, *args, **kwargs)




class BoardObjectPermissionMixin(View):
    """
    A flexible mixin that verifies the logged-in user has permission to access
    a specific board object (Card, List, Board) based on board membership.
    
    This mixin handles authentication, object retrieval, board relationship resolution,
    and permission checking in a generic way that works with different model types.
    
    Attributes:
        model_to_check: The model class to retrieve (e.g., Card, List, Board)
        id_kwarg_name: The URL kwarg name for the object ID (e.g., 'card_id', 'list_id')
        board_relationship_path: Optional path to board from object (e.g., 'list.board' for Card)
    """
    model_to_check = None  # e.g., Card, List, Board
    id_kwarg_name = None   # e.g., 'card_id', 'list_id' 
    board_relationship_path = None  # e.g., 'list.board' for Card
    
    def get_board_from_object(self, obj):
        """
        Dynamically resolve the board from the object based on model type.
        
        Args:
            obj: The model instance (Card, List, or Board)
            
        Returns:
            Board instance
            
        Raises:
            ValueError: If board cannot be determined from object
        """
        if isinstance(obj, Board):
            return obj
        elif isinstance(obj, List):
            return obj.board
        elif isinstance(obj, Card):
            return obj.list.board
        else:
            raise ValueError(f"Cannot determine board from {obj.__class__.__name__}")
    
    def dispatch(self, request, *args, **kwargs):
        """
        Handle authentication, object retrieval, and permission checking.
        
        This method:
        1. Validates user authentication
        2. Validates required attributes are set
        3. Retrieves the target object with optimized queries
        4. Resolves the associated board
        5. Checks board membership permissions
        6. Attaches objects to view for easy access
        """
        # 1. Authentication check with proper error handling
        if not request.user.is_authenticated:
            custom_logger(
                f"Unauthenticated access attempt to {self.__class__.__name__}",
                Fore.RED
            )
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        # 2. Validate required attributes
        if not self.model_to_check:
            raise ValueError(
                f"{self.__class__.__name__} requires 'model_to_check' to be set"
            )
        if not self.id_kwarg_name:
            raise ValueError(
                f"{self.__class__.__name__} requires 'id_kwarg_name' to be set"
            )
        
        # 3. Get object ID from URL kwargs
        obj_id = self.kwargs.get(self.id_kwarg_name)
        if not obj_id:
            raise ValueError(
                f"Missing required kwarg '{self.id_kwarg_name}' in URL"
            )
        
        # 4. Retrieve object with optimized queries
        try:
            # Use select_related for foreign key relationships to avoid N+1 queries
            if self.model_to_check == Card:
                obj = get_object_or_404(
                    self.model_to_check.objects.select_related(
                        'list__board__owner'
                    ).prefetch_related('assignees'),
                    pk=obj_id
                )
            elif self.model_to_check == List:
                obj = get_object_or_404(
                    self.model_to_check.objects.select_related(
                        'board__owner'
                    ),
                    pk=obj_id
                )
            elif self.model_to_check == Board:
                obj = get_object_or_404(
                    self.model_to_check.objects.select_related('owner'),
                    pk=obj_id
                )
            else:
                # Fallback for other models
                obj = get_object_or_404(self.model_to_check, pk=obj_id)
                
        except (ValueError, TypeError) as e:
            custom_logger(
                f"Invalid object ID '{obj_id}' for model {self.model_to_check.__name__}: {e}",
                Fore.YELLOW
            )
            raise Http404("Invalid object ID")
        
        # 5. Resolve the board from the object
        try:
            board = self.get_board_from_object(obj)
        except ValueError as e:
            custom_logger(
                f"Failed to get board from {obj.__class__.__name__}({obj_id}): {e}",
                Fore.RED
            )
            raise Http404("Board not found")
        
        # 6. Check board membership with optimized query
        try:
            is_member = board.memberships.filter(
                user=request.user, 
                is_active=True
            ).exists()
            
            if not is_member:
                custom_logger(
                    f"User {request.user.email} denied access to "
                    f"{obj.__class__.__name__}({obj_id}) on board '{board.title}': "
                    "Not a board member",
                    Fore.YELLOW
                )
                raise PermissionDenied(
                    "You must be a member of this board to access this resource."
                )
                
        except Exception as e:
            custom_logger(
                f"Error checking membership for user {request.user.email} "
                f"on board '{board.title}': {e}",
                Fore.RED
            )
            raise PermissionDenied("Unable to verify board membership")
        
        # 7. Attach objects to view for easy access in child views
        self.board = board
        self.object = obj
        
        custom_logger(
            f"User {request.user.email} granted access to "
            f"{obj.__class__.__name__}({obj_id}) on board '{board.title}'",
            Fore.GREEN
        )
        
        return super().dispatch(request, *args, **kwargs)


class BoardReadWritePermissionMixin:
    """
    A mixin that verifies the user has at least "Member" level permissions,
    blocking "Viewer" roles from performing write actions (create, update, delete, move).
    
    This should be used for views that modify board content, like creating a card or list.
    It inherits from BoardMemberRequiredMixin to first ensure basic membership.
    """
    def dispatch(self, request, *args, **kwargs):
        # First, ensure the user is at least a member by calling the parent mixin's logic.
        # This will also handle non-members (404) and attach `self.board`.
        response = super().dispatch(request, *args, **kwargs)

        # Now, perform the more specific role check.
        try:
            membership = self.board.memberships.get(user=request.user, is_active=True)
            if membership.role > Membership.ROLE_MEMBER: # ROLE_VIEWER has a higher value (40 > 30)
                raise PermissionDenied("You do not have permission to modify content on this board.")
        except Membership.DoesNotExist:
            # This case should technically be caught by BoardMemberRequiredMixin,
            # but we handle it here for safety.
            if self.board.owner != request.user:
                 raise PermissionDenied("You do not have permission to modify content on this board.")

        return response
