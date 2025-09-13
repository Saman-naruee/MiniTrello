from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Q, Prefetch
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse_lazy
from django.views import View
from django.http import Http404, HttpResponseRedirect, HttpResponse

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Board, List, Card, Membership
from custom_tools.logger import custom_logger
from .forms import *
from colorama import Fore



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
    """Get all lists for a board with optimized queries and preloaded cards"""
    lists = (
        List.objects.filter(board=board)
        .select_related("board")
        .prefetch_related(
            Prefetch(
                'cards',
                queryset=Card.objects.select_related("assignee").order_by("priority", "order"),
                to_attr='prefetched_cards'
            )
        )
        .order_by("order")
    )
    return lists


def get_user_list(list_id, user, board):
    """Get a specific list for a user with permission check, ensuring it belongs to the given board"""
    custom_logger(f"get_user_list called with list_id: {list_id}, user: {user.email}, board_id: {board.id}", Fore.MAGENTA)
    custom_logger(f"Attempting to retrieve List with id={list_id}, board={board.id}, and user {user.email} as active member.", Fore.MAGENTA)
    return get_object_or_404(
        List,
        id=list_id,
        board=board, # Explicitly filter by the board object
        # board__memberships__user=user,
        # board__memberships__is_active=True
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
        lists = get_board_lists(board)
        context['lists'] = lists
        # context['cards_by_list'] is no longer needed as cards are attached to each list object
        context['board'] = board
        context['board_id'] = board.id
        return context


# HTMX Views for dynamic interactions
class HTMXBoardCreateView(LoginRequiredMixin, CreateView):
    """Create a new board via HTMX"""
    model = Board
    template_name = "boards/partials/create_board.html"
    form_class = BoardForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form}, status=400)

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
        membership = Membership.objects.create(
            user=self.request.user,
            board=board,
            role=Membership.ROLE_OWNER,
            can_edit=True,
            can_comment=True,
            can_invite=True,
        )

        custom_logger(f"membership created for user {self.request.user.username}, membership: {membership}")

        response = render_partial_response("boards/partials/board_card.html", {"board": board})
        response['HX-Trigger'] = 'boardCreated'
        return response

class HTMXBoardDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a board via HTMX"""
    model = Board
    template_name = "boards/delete_confirm_board.html"
    success_url = reverse_lazy("boards:boards_list")

    def get_object(self, queryset=None):
        return  get_user_board(self.kwargs['board_id'], self.request.user)

    def delete(self, request, *args, **kwargs):
        """
        Perform delete and return an HTMX-friendly response when applicable.
        """
        custom_logger(f"HTMXBoardDeleteView.delete called with args: {args}, kwargs: {kwargs}")
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        custom_logger(f"Deleted board: {self.object}")

        if request.headers.get("HX-Request") == "true":
            # Option A: 204 No Content — typical when the client-side will remove the row/card.
            return HttpResponse(status=204)
    
        return HttpResponseRedirect(success_url)

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


class BoardMembersView(LoginRequiredMixin, DetailView):
    """View and manage board members"""
    model = Board
    template_name = "boards/partials/board_members.html"
    context_object_name = "board"

    def get_object(self):
        return get_user_board(self.kwargs['board_id'], self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        board = self.get_object()
        memberships = board.memberships.select_related('user').all()
        members = [membership.user for membership in memberships]
        context['memberships'] = memberships
        context['members'] = members
        return context



# List Views
class HTMXListCreateView(LoginRequiredMixin, CreateView):
    """Create a new list via HTMX"""
    model = List
    template_name = "boards/partials/create_list.html"  # Assuming this template exists or will be created
    form_class = ListForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form, "board_id": self.kwargs['board_id']})

    def form_invalid(self, form):
        return render(self.request, self.template_name, {"form": form, "board_id": self.kwargs['board_id']}, status=400)

    def form_valid(self, form):
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        list_obj = form.save(commit=False)
        list_obj.board = board
        list_obj.order = get_next_order(List, {"board": board})
        list_obj.save()
        response = render_partial_response("boards/partials/list_column.html", {"list": list_obj})
        response['HX-Trigger'] = 'listCreated'
        return response

class HTMXListUpdateView(LoginRequiredMixin, UpdateView):
    """Update a list via HTMX"""

    model = List
    template_name = "boards/partials/update_list.html"
    form_class = ListForm

    def get_object(self):
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        return get_user_list(self.kwargs['list_id'], self.request.user, board)

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
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        return get_user_list(self.kwargs['list_id'], self.request.user, board)


class HTMXListDeleteView(LoginRequiredMixin, View):
    """Delete a list via HTMX"""
    
    def delete(self, request, board_id, list_id):
        board = get_user_board(board_id, request.user)
        list_obj = get_user_list(list_id, request.user, board)
        if list_obj.board.id != board_id:
            raise Http404("List not found")
        list_obj.delete()
        return JsonResponse({"success": True})




# Card Views
class HTMXCardDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a card via HTMX"""
    
    def delete(self, request, card_id):
        card = get_user_card(card_id, request.user)
        card.delete()
        return JsonResponse({"success": True})


class HTMXCardCreateView(LoginRequiredMixin, CreateView):
    """Create a new card via HTMX"""
    model = Card
    form_class = CardForm
    template_name = "boards/partials/create_card.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        kwargs['board'] = board
        custom_logger(f"HTMXCardCreateView.get_form_kwargs called with kwargs: {kwargs}", Fore.YELLOW)
        return kwargs

    def get(self, request, *args, **kwargs):
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        form = self.form_class(board=board)
        custom_logger(f"HTMXCardCreateView.get called with args: {args}, kwargs: {kwargs}", Fore.YELLOW)
        response = render(request, self.template_name, {
            "form": form,
            "board_id": self.kwargs['board_id'],
            "list_id": self.kwargs['list_id']
        })

        response.headers['HX-Trigger'] = 'cardFormShown'
        response.headers['HX-Target'] = '#card-form-container-' + str(self.kwargs['list_id'])
        response.headers['HX-Swap'] = 'innerHTML'
        return response

    def form_valid(self, form):
        custom_logger(f"HTMXCardCreateView.form_valid entered.", Fore.GREEN)
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        card_list = get_user_list(self.kwargs['list_id'], self.request.user, board)
        
        card = form.save(commit=False)
        card.list = card_list
        card.order = get_next_order(Card, {"list": card_list})
        custom_logger(f"Card object before save: {card.__dict__}", Fore.CYAN)
        card.save()

        custom_logger(f"Card '{card.title}' created in list '{card_list.title}' on board '{board.title}' by user '{self.request.user}'")

        response = HttpResponse(
            render_to_string("boards/partials/card_item.html", {
                "card": card,
                "board_id": board.id,
                "list_id": card_list.id
            })
        )
        response.headers['HX-Trigger'] = 'cardCreated'
        return response

    def form_invalid(self, form):
        custom_logger(f"HTMXCardCreateView.form_invalid called with form errors: {form.errors}", Fore.RED)
        return render(self.request, self.template_name, {
            "form": form,
            "board_id": self.kwargs['board_id'],
            "list_id": self.kwargs['list_id']
        }, status=400)


class HTMXCardUpdateView(LoginRequiredMixin, View):
    """Update a card via HTMX"""
    
    def post(self, request, board_id, list_id, card_id):
        card = get_user_card(card_id, request.user)
        form = CardForm(request.POST or None, instance=card)
        if form.is_valid():
            form.save()
            return render_partial_response(
                "boards/partials/card_item.html",
                {"card": card, "list": card.list}
            )
        else:
            # Re-render the form with errors
            return render(request, "boards/partials/card_item.html", {"form": form, "card": card, "list": card.list}, status=400)


class HTMXCardDetailView(LoginRequiredMixin, DetailView):
    """View a card's details via HTMX"""

    model = Card
    template_name = "boards/partials/card_detail.html"
    context_object_name = "card"

    def get_object(self):
        return get_user_card(self.kwargs['card_id'], self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = self.get_object()
        context.update({
            'comments': card.comments.all(),
            'mini_tasks': card.mini_tasks.all(),
            'comment_form': CommentForm(),
            'mini_task_form': MiniTaskForm()
        })
        return context

    def get(self, request, *args, **kwargs):
        custom_logger("/n/nHTMXCardDetailView.get called/n/n", Fore.YELLOW)
        return super().get(request, *args, **kwargs)

@login_required
def add_member_to_board(request, board_id):
    # Check current user have right acccess
    board = get_user_board(board_id, request.user)

    # can check the owner
    # if board.owner != request.user:
    #     messages.error(request, "You don't have permission to add members.")
    #     return redirect('boards:board_detail', board_id=board.id)

    if request.method == 'POST':

        form = MembershipForm(request.POST, board=board)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.board = board
            membership.invited_by = request.user # invite the current user
            membership.save()
            
            messages.success(request, f"{membership.user.username} was added to the board.")
            return redirect('boards:board_detail', board_id=board.id)
    else:
        form = MembershipForm(board=board)
        
    return render(request, 'boards/add_member.html', {'form': form, 'board': board})

@login_required
def add_comment_to_card(request, board_id, list_id, card_id):
    card = get_user_card(card_id, request.user)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.card = card
            comment.user = request.user
            comment.save()
            return redirect('boards:card_detail', board_id=board_id, list_id=list_id, card_id=card_id)

@login_required
def add_mini_task_to_card(request, board_id, list_id, card_id):
    card = get_user_card(card_id, request.user)
    if request.method == 'POST':
        form = MiniTaskForm(request.POST)
        if form.is_valid():
            mini_task = form.save(commit=False)
            mini_task.card = card
            mini_task.save()
            return redirect('boards:card_detail', board_id=board_id, list_id=list_id, card_id=card_id)

@login_required
def toggle_mini_task(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        mini_task = MiniTask.objects.get(id=task_id)
        mini_task.is_completed = not mini_task.is_completed
        mini_task.save()
        return JsonResponse({'success': True})
