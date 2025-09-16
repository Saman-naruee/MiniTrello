import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Q, Prefetch
from django.db import transaction
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse_lazy
from django.views import View
from django.http import Http404, HttpResponseRedirect, HttpResponse

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Board, List, Card, Membership
from apps.accounts.models import User
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
                queryset=Card.objects.prefetch_related("assignees").order_by("priority", "order"),
                to_attr='prefetched_cards'
            )
        )
        .order_by("order")
    )
    return lists


def get_user_list(list_id, user, board):
    """Get a specific list for a user with permission check, ensuring it belongs to the given board"""
    
    if board.owner == user or board.memberships.filter(user=user, is_active=True).exists():
        return get_object_or_404(
            List,
            id=list_id,
            board=board, # Explicitly filter by the board object
        )
    return False


def is_owner_or_member(card_id, user):
    board_of_this_card = Card.objects.get(id=card_id).list.board
    return True if board_of_this_card.owner == user \
        or board_of_this_card.memberships.filter(user=user, is_active=True).exists()\
        else False


def get_user_card(card_id, user):
    """Get a specific card for a user with permission check"""
    is_o_or_m = is_owner_or_member(card_id, user)
    custom_logger(is_o_or_m, Fore.MAGENTA)
    if is_o_or_m:
        return get_object_or_404(
            Card, 
            id=card_id, 
        )
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
        context['update_board_form'] = BoardForm(instance=self.get_object())
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
            messages.error(self.request, "Board limit reached")
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
        messages.success(self.request, "Board created successfully")
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
    """Update a board via HTMX inside a modal"""
    model = Board
    template_name = "boards/partials/update_board.html"
    form_class = BoardForm

    def get_object(self):
        return get_user_board(self.kwargs['board_id'], self.request.user)

    def get_success_url(self):
        return reverse_lazy("boards:board_detail", kwargs={"board_id": self.object.id})

    def form_valid(self, form):
        board = form.save()
        custom_logger(f"[BoardUpdate] Board updated to {board.title}")

        # currently, this condition is true
        if self.request.htmx:
            # render the updated title section
            updated_title_partial = render_to_string("boards/partials/board_title_section.html", {"board": board})
            
            # construct the response
            response = HttpResponse(updated_title_partial)
            
            # set a trigger with a success message to display to the user
            trigger_data = {
                "boardUpdated": True, # to trigger the modal
                "showMessage": f"Board '{board.title}' updated successfully!" # to display to the user
            }
            response['HX-Trigger'] = json.dumps(trigger_data)
            
            return response
            
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        custom_logger("[BoardUpdate] Form invalid")
        return render(self.request, self.template_name, {"form": form, "board": self.get_object()})


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

    def get_object(self, queryset=None):
        # This method correctly finds the list based on permissions
        board = get_user_board(self.kwargs['board_id'], self.request.user)
        return get_user_list(self.kwargs['list_id'], self.request.user, board)

    def get_context_data(self, **kwargs):
        # ❗❗❗ CORE FIX: Add this method to pass all necessary context
        context = super().get_context_data(**kwargs)
        context['board'] = self.get_object().board
        context['list'] = self.get_object()
        return context

    def form_valid(self, form):
        # This method handles a successful form submission
        list_obj = form.save()
        
        # We need to re-render the entire list_column to reflect the changes
        list_column_html = render_to_string(
            "boards/partials/list_column.html", 
            {"list": list_obj, "board": list_obj.board, "request": self.request} # Pass request for CSRF token
        )
        response = HttpResponse(list_column_html)
        
        # Send a trigger to close the modal and show a success message
        trigger_data = {
            "listUpdated": True, # Custom event name for closing modal
            "showMessage": f"List '{list_obj.title}' updated successfully."
        }
        response['HX-Trigger'] = json.dumps(trigger_data)
        return response



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

    def delete(self, request, board_id, list_id, card_id):
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
    
    def get(self, request, board_id, list_id, card_id):
        card = get_user_card(card_id, request.user)
        form = CardForm(instance=card, board=card.list.board)
        context = {
            "form": form,
            "card": card,
            "board": card.list.board,
            "list_id": list_id
        }
        return render(request, "boards/card_update.html", context)

    def post(self, request, board_id, list_id, card_id):
        card = get_user_card(card_id, request.user)
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, "Card updated successfully")
            return redirect("boards:card_detail", board_id=board_id, list_id=list_id, card_id=card_id)
        
        return render(request,
            "boards/card_update.html",
            {"form": form, "card": card, "board": card.list.board, "list_id": list_id},
            status=400
        )    


class HTMXCardDetailView(LoginRequiredMixin, DetailView):
    """View a card's details via HTMX"""

    model = Card
    template_name = "boards/card_detail.html"
    context_object_name = "card"

    def get_object(self, queryset=None):
        card_id = self.kwargs.get("card_id")
        return get_user_card(card_id, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = self.object
        context["card"] = card
        context["list"] = card.list
        context["board"] = card.list.board
        return context



class HTMXCardAssignMembersView(LoginRequiredMixin, View):
    """Assign multiple members to a card via HTMX"""

    def post(self, request, board_id, list_id, card_id):
        card = get_user_card(card_id, request.user)
        member_ids = request.POST.getlist('member_ids')

        # Validate member_ids
        valid_members = card.list.board.memberships.filter(user_id__in=member_ids).values_list('user_id', flat=True)
        invalid_members = set(member_ids) - set(map(str, valid_members))

        if invalid_members:
            messages.error(request, f"Invalid member(s) selected: {', '.join(invalid_members)}")
            return redirect("boards:card_detail", board_id=board_id, list_id=list_id, card_id=card_id)

        # Assign members to the card
        card.assignees.clear()
        for member_id in member_ids:
            card.assignees.add(User.objects.get(id=member_id))

        messages.success(request, "Members assigned to the card successfully")
        return redirect("boards:card_detail", board_id=board_id, list_id=list_id, card_id=card_id)




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
            membership.invited_by = request.user
            membership.save()
            
            messages.success(request, f"{membership.user.username} was added to the board.")
            return redirect('boards:board_detail', board_id=board.id)
    else:
        form = MembershipForm(board=board)
        
    return render(request, 'boards/add_member.html', {'form': form, 'board': board})


def custom_404(request, exception):
    return render(request, '404.html', status=404)


class HTMXCardMoveView(LoginRequiredMixin, View):
    
    @transaction.atomic
    # Main fix: get all parameters from URL
    def put(self, request, board_id, list_id, card_id):
        # Currently, this log should work
        custom_logger(f"In PUT method for moving card_id: {card_id}", Fore.GREEN)
        
        # Use card_id and user to check initial access
        card = get_user_card(card_id, request.user)
        
        data = json.loads(request.body)
        to_list_id = data.get('to_list_id')
        new_index = int(data.get('new_index', 0))

        # Get the destination list
        # Also check if the destination list belongs to the same board
        to_list = get_object_or_404(List, id=to_list_id, board_id=board_id)
        
        # 1. Move the card to the new list (this part is not changed)
        card.list = to_list
        card.save(update_fields=['list'])

        custom_logger(f"Card '{card.title}' moved to list '{to_list.title}'", Fore.CYAN)
        
        # 2. Update the order of cards in the new list (this part is not changed)
        other_cards = to_list.cards.exclude(id=card.id).order_by('order')
        card_list_for_reorder = list(other_cards)
        card_list_for_reorder.insert(new_index, card)
        
        for index, c in enumerate(card_list_for_reorder):
            c.order = index
            c.save(update_fields=['order'])
        
        custom_logger("Card reordering complete.", Fore.GREEN)
        return HttpResponse(status=200, reason="Card moved and reordered successfully.")
