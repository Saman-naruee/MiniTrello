from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Q
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse_lazy
from django.views import View
from django.http import Http404

from .models import Board, List, Card, Membership
from custom_tools.logger import custom_logger
from .forms import *

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
        if board.owner == user or board.memberships.filter(user=user, is_active=True).exists():
            return board
    except Board.DoesNotExist:
        raise Http404("Board not found")

def get_board_lists(board):
    """Get all lists for a board with optimized queries"""
    lists = (
        List.objects.filter(board=board)
        .select_related("board")
        .order_by("order")
    )
    
    # Preload cards for all lists to avoid N+1 queries
    # No direct assignment to list_obj.cards
    cards_by_list = {}
    for list_obj in lists:
        cards_by_list[list_obj.id] = (
            Card.objects.filter(list=list_obj)
            .select_related("assignee")
            .order_by("priority", "order")
        )

    return lists, cards_by_list


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


# Class-Based Board Views
class BoardListView(LoginRequiredMixin, ListView):
    """Display all boards for the current user"""
    model = Board
    template_name = "boards/list.html"
    context_object_name = "boards"
    
    def get_queryset(self):
        return Board.objects.filter(
            Q(owner=self.request.user) | Q(memberships__user=self.request.user, memberships__is_active=True)
        ).distinct()


class BoardDetailView(LoginRequiredMixin, DetailView):
    """Display a specific board with its lists and cards"""
    model = Board
    template_name = "boards/detail.html"
    context_object_name = "board"
    
    def get_object(self):
        return get_user_board(self.kwargs['board_id'], self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        board = self.get_object()
        lists, cards_by_list = get_board_lists(board)
        context['lists'] = lists
        context['cards_by_list'] = cards_by_list
        context['board'] = board
        context['board_id'] = board.id
        return context


# HTMX Views for dynamic interactions
class HTMXBoardCreateView(LoginRequiredMixin, CreateView):
    """Create a new board via HTMX"""
    model = Board
    template_name = "boards/partials/create_board.html"
    form_class = BoardForm

    def form_valid(self, form):
        # Check board limit
        user_boards_count = Board.objects.filter(owner=self.request.user).count()
        max_boards = getattr(settings, "MAX_BOARDS_PER_USER", 10)
        
        if user_boards_count >= max_boards:
            form.add_error(None, "Board limit reached")
            return self.form_invalid(form)

        # Create board
        board = form.save(commit=False)
        board.owner = self.request.user
        board.save()
        
        # Create owner membership
        Membership.objects.create(
            user=self.request.user,
            board=board,
            role=Membership.ROLE_OWNER,
            can_edit=True,
            can_comment=True,
            can_invite=True,
        )

        return render_partial_response("boards/partials/board_card.html", {"board": board})

class HTMXBoardDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a board via HTMX"""
    
    def delete(self, request, board_id):
        board = get_user_board(board_id, request.user)
        board.delete()
        # return render_partial_response("boards/partials/board_delete.html", {"board": board})
        return JsonResponse({"success": True})


class HTMXBoardUpdateView(LoginRequiredMixin, UpdateView):
    """Update a board via HTMX"""
    
    model = Board
    template_name = "boards/partials/update_board.html"
    form_class = BoardForm

    def get_object(self):
        return get_user_board(self.kwargs['board_id'], self.request.user)

    def post(self, request, *args, **kwargs):
        board = self.get_object()
        form = self.get_form()
        if form.is_valid():
            form.save()
            return render_partial_response("boards/partials/board_card.html", {"board": board})
        return render_partial_response("boards/partials/update_board.html", {"form": form, "board": board})



# List Views
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

class HTMXListUpdateView(LoginRequiredMixin, UpdateView):
    """Update a list via HTMX"""

    model = List
    template_name = "boards/partials/update_list.html"
    form_class = ListForm

    def get_object(self):
        return get_user_list(self.kwargs['list_id'], self.request.user)

    def post(self, request, *args, **kwargs):
        list_obj = self.get_object()
        form = self.get_form()
        if form.is_valid():
            form.save()
            return render_partial_response("boards/partials/list_column.html", {"list": list_obj})
        return render_partial_response("boards/partials/update_list.html", {"form": form, "list": list_obj})


class HTMXListDetailView(LoginRequiredMixin, DetailView):
    """View a list's details via HTMX"""

    model = List
    template_name = "boards/partials/list_detail.html"

    def get_object(self):
        return get_user_list(self.kwargs['list_id'], self.request.user)


class HTMXListDeleteView(LoginRequiredMixin, View):
    """Delete a list via HTMX"""
    
    def delete(self, request, board_id, list_id):
        list_obj = get_user_list(list_id, request.user)
        if list_obj.board.id != board_id:
            raise Http404("List not found")
        list_obj.delete()
        return JsonResponse({"success": True})




# Card Views
class HTMXCardDeleteView(LoginRequiredMixin, View):
    """Delete a card via HTMX"""
    
    def delete(self, request, card_id):
        card = get_user_card(card_id, request.user)
        card.delete()
        return JsonResponse({"success": True})


class HTMXCardCreateView(LoginRequiredMixin, View):
    """Create a new card via HTMX"""
    
    def post(self, request, board_id, list_id):
        board = get_user_board(board_id, request.user)
        card_list = get_user_list(list_id, request.user)

        form = CardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.list = card_list

            last_card = Card.objects.filter(list=card_list).order_by('-order').first()
            card.order = last_card.order + 1 if last_card else 1
            card.save()
            return render_partial_response("boards/partials/card_item.html", {"card": card})
        return JsonResponse({"error": "Invalid form data"}, status=400)


class HTMXCardUpdateView(LoginRequiredMixin, View):
    """Update a card via HTMX"""
    
    def patch(self, request, card_id):
        card = get_user_card(card_id, request.user)
        form = CardForm(request.PATCH or request.POST)
        if form.is_valid():
            form.save()
            return render_partial_response(
                "boards/partials/card.html",
                {"card": card, "list": card.list}
            )
        else:
            return JsonResponse({"errors": form.errors}, status=400)


class HTMXCardDetailView(LoginRequiredMixin, DetailView):
    """View a card's details via HTMX"""

    model = Card
    template_name = "boards/partials/card_detail.html"

    def get_object(self):
        return get_user_card(self.kwargs['card_id'], self.request.user)
