from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse_lazy
from django.views import View

from .models import Board, List, Card, Membership


# Helper functions to avoid repetition
def get_user_boards(user):
    """Get all boards for a user with optimized queries"""
    return (
        Board.objects.filter(memberships__user=user, memberships__is_active=True)
        .select_related("owner")
        .prefetch_related("memberships")
        .distinct()
    )


def get_user_board(board_id, user):
    """Get a specific board for a user with permission check"""
    return get_object_or_404(
        Board, 
        id=board_id, 
        memberships__user=user, 
        memberships__is_active=True
    )


def get_board_lists(board):
    """Get all lists for a board with optimized queries"""
    lists = (
        List.objects.filter(board=board)
        .select_related("board")
        .order_by("order")
    )
    
    # Preload cards for all lists to avoid N+1 queries
    for list_obj in lists:
        list_obj.cards = (
            Card.objects.filter(list=list_obj)
            .select_related("assignee")
            .order_by("priority", "order")
        )
    
    return lists


def get_user_list(list_id, user):
    """Get a specific list for a user with permission check"""
    return get_object_or_404(
        List, 
        id=list_id, 
        board__memberships__user=user, 
        board__memberships__is_active=True
    )


def get_user_card(card_id, user):
    """Get a specific card for a user with permission check"""
    return get_object_or_404(
        Card, 
        id=card_id, 
        list__board__memberships__user=user, 
        list__board__memberships__is_active=True
    )


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


# Class-Based Views
class BoardListView(LoginRequiredMixin, ListView):
    """Display all boards for the current user"""
    model = Board
    template_name = "boards/list.html"
    context_object_name = "boards"
    
    def get_queryset(self):
        return get_user_boards(self.request.user)


class BoardDetailView(LoginRequiredMixin, DetailView):
    """Display a specific board with its lists and cards"""
    model = Board
    template_name = "boards/detail.html"
    context_object_name = "board"
    
    def get_object(self):
        return get_user_board(self.kwargs['board_id'], self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lists'] = get_board_lists(self.object)
        return context


# HTMX Views for dynamic interactions
class HTMXBoardCreateView(LoginRequiredMixin, View):
    """Create a new board via HTMX"""
    
    def post(self, request):
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        color = request.POST.get("color", "blue")
        
        if not title:
            return JsonResponse({"error": "Title is required"}, status=400)
        
        # Check board limit
        user_boards_count = Board.objects.filter(owner=request.user).count()
        max_boards = getattr(settings, "MAX_BOARDS_PER_USER", 10)
        
        if user_boards_count >= max_boards:
            return JsonResponse({"error": "Board limit reached"}, status=400)
        
        # Create board
        board = Board.objects.create(
            owner=request.user,
            title=title,
            description=description,
            color=color
        )
        
        # Create owner membership
        Membership.objects.create(
            user=request.user,
            board=board,
            role=Membership.ROLE_OWNER,
            can_edit=True,
            can_comment=True,
            can_invite=True,
        )
        
        return render_partial_response("boards/partials/board_card.html", {"board": board})


class HTMXListCreateView(LoginRequiredMixin, View):
    """Create a new list via HTMX"""
    
    def post(self, request):
        board_id = request.POST.get("board")
        title = request.POST.get("title")
        
        if not board_id or not title:
            return JsonResponse({"error": "Board ID and title are required"}, status=400)
        
        board = get_user_board(board_id, request.user)
        
        # Get next order
        order = get_next_order(List, {"board": board})
        
        list_obj = List.objects.create(
            board=board,
            title=title,
            order=order
        )
        
        return render_partial_response("boards/partials/list_column.html", {"list": list_obj})


class HTMXCardCreateView(LoginRequiredMixin, View):
    """Create a new card via HTMX"""
    
    def post(self, request):
        list_id = request.POST.get("list")
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        priority = request.POST.get("priority", 50)
        
        if not list_id or not title:
            return JsonResponse({"error": "List ID and title are required"}, status=400)
        
        list_obj = get_user_list(list_id, request.user)
        
        # Get next order
        order = get_next_order(Card, {"list": list_obj})
        
        card = Card.objects.create(
            list=list_obj,
            title=title,
            description=description,
            priority=int(priority),
            order=order
        )
        
        return render_partial_response("boards/partials/card_item.html", {"card": card})


class HTMXCardUpdateView(LoginRequiredMixin, View):
    """Update a card via HTMX"""
    
    def patch(self, request, card_id):
        card = get_user_card(card_id, request.user)
        
        # Update fields
        if "title" in request.POST:
            card.title = request.POST["title"]
        if "description" in request.POST:
            card.description = request.POST["description"]
        if "priority" in request.POST:
            card.priority = int(request.POST["priority"])
        if "list" in request.POST:
            new_list = get_object_or_404(List, id=request.POST["list"])
            card.list = new_list
        if "order" in request.POST:
            card.order = int(request.POST["order"])
        
        card.save()
        
        return render_partial_response("boards/partials/card_item.html", {"card": card})


class HTMXBoardDeleteView(LoginRequiredMixin, View):
    """Delete a board via HTMX"""
    
    def delete(self, request, board_id):
        board = get_object_or_404(Board, id=board_id, owner=request.user)
        board.delete()
        return JsonResponse({"success": True})


class HTMXListDeleteView(LoginRequiredMixin, View):
    """Delete a list via HTMX"""
    
    def delete(self, request, list_id):
        list_obj = get_user_list(list_id, request.user)
        list_obj.delete()
        return JsonResponse({"success": True})


class HTMXCardDeleteView(LoginRequiredMixin, View):
    """Delete a card via HTMX"""
    
    def delete(self, request, card_id):
        card = get_user_card(card_id, request.user)
        card.delete()
        return JsonResponse({"success": True})

