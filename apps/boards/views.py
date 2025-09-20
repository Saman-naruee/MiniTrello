import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
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
from django.db import models
from django.http import HttpResponseBadRequest

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Board, List, Card, Membership
from apps.accounts.models import User
from custom_tools.logger import custom_logger
from .forms import *
from colorama import Fore
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden as HttpResponse403
from django.core.exceptions import PermissionDenied

# Fetch Helper functions to avoid repetition
from .permissions import BoardMemberRequiredMixin, BoardAdminRequiredMixin





# Class-Based Board Views
class BoardListView(LoginRequiredMixin, ListView):
    """Display all boards for the current user"""
    model = Board
    template_name = "boards/list.html"
    context_object_name = "boards"
    
    def get_queryset(self):
        """Return boards owned by or where user is active member."""
        return Board.objects.filter(
            Q(owner=self.request.user) | Q(memberships__user=self.request.user, memberships__is_active=True)
        ).distinct()


class BoardDetailView(LoginRequiredMixin, BoardMemberRequiredMixin, DetailView):
    """Display a specific board with its lists and cards"""
    model = Board
    template_name = "boards/detail.html"
    context_object_name = "board"
    pk_url_kwarg = 'board_id'
    
    def get_context_data(self, **kwargs):
        """Add optimized lists with prefetched cards to context."""
        # ❗❗❗ CORE FIX: Perform the optimized query here.
        context = super().get_context_data(**kwargs)
        # self.object is the board, securely fetched by the mixin and DetailView.
        # We add the optimized 'lists' queryset to the context.
        context['lists'] = self.object.lists.all().prefetch_related(
            Prefetch(
                'cards',
                queryset=Card.objects.prefetch_related("assignees").order_by("priority", "order"),
                to_attr='prefetched_cards' # This is the attribute the test is looking for
            )
        ).order_by("order")

        return context


# HTMX Views for dynamic interactions
class HTMXBoardCreateView(LoginRequiredMixin, CreateView):
    """Create a new board via HTMX"""
    model = Board
    template_name = "boards/partials/create_board.html"
    form_class = BoardForm

    def get(self, request, *args, **kwargs):
        """Render form for HTMX GET requests only."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")
        
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def form_invalid(self, form):
        """Render invalid form with errors for HTMX."""
        return render(self.request, self.template_name, {"form": form}, status=400)

    def form_valid(self, form):
        """Create board, add owner membership, return success HTML."""
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

        html = render_to_string("boards/partials/board_card.html", {"board": board})
        response = JsonResponse({"html": html})
        messages.success(self.request, "Board created successfully")
        response['HX-Trigger'] = 'boardCreated'
        return response
    
    def post(self, request, *args, **kwargs):
        """Handle POST for HTMX requests only."""
        # Ensure this is an HTMX request
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")
        
        return super().post(request, *args, **kwargs)

class HTMXBoardDeleteView(LoginRequiredMixin, BoardMemberRequiredMixin, DeleteView):
    """Delete a board via HTMX, restricted to owners/admins."""
    model = Board
    template_name = "boards/delete_confirm_board.html"
    success_url = reverse_lazy("boards:boards_list")
    pk_url_kwarg = 'board_id'

    def get_context_data(self, **kwargs):
        """Add board to context for confirmation."""
        context = super().get_context_data(**kwargs)
        context['board'] = self.object
        return context

    def get(self, request, *args, **kwargs):
        """Check permissions and render partial/full template."""
        # Check if user has permission to delete (admin/owner only)
        if not (self.board.owner == request.user or
                self.board.memberships.filter(user=request.user, role__in=[Membership.ROLE_ADMIN, Membership.ROLE_OWNER]).exists()):
            return HttpResponse(status=403)

        # For HTMX requests, return partial template
        if request.headers.get('HX-Request'):
            return render(request, "boards/partials/board_delete.html", {"board": self.board})

        # For regular requests, return full page
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Call the superclass's delete method to perform the deletion and
        then return an HTMX-friendly response if applicable.
        """
        # We need to get the object before it's deleted to log it or use its data.
        self.object = self.get_object()
        success_url = self.get_success_url()

        # This performs the actual deletion from the database.
        self.object.delete()

        # Now, check if this was an HTMX request.
        if self.request.headers.get('HX-Request'):
            # For HTMX, return a 204 No Content response.
            return HttpResponse(status=204)
        else:
            # For regular form submissions, redirect to the success URL.
            return HttpResponseRedirect(success_url)

    def post(self, request, *args, **kwargs):
        """Check permissions and call delete method."""
        # Check if user has permission to delete (admin/owner only)
        if not (self.board.owner == request.user or
                self.board.memberships.filter(user=request.user, role__in=[Membership.ROLE_ADMIN, Membership.ROLE_OWNER]).exists()):
            return HttpResponse(status=403)

        # We override post just to call our custom delete method.
        return self.delete(request, *args, **kwargs)

class HTMXBoardUpdateView(LoginRequiredMixin, BoardAdminRequiredMixin, UpdateView):
    """Update a board via HTMX inside a modal"""
    model = Board
    template_name = "boards/partials/update_board.html"
    form_class = BoardForm
    pk_url_kwarg = 'board_id'

    def get_success_url(self):
        """Return URL to board detail."""
        return reverse_lazy("boards:board_detail", kwargs={"board_id": self.object.id})

    def form_valid(self, form):
        """Save changes and return updated partial for HTMX."""
        board = form.save()
        custom_logger(f"[BoardUpdate] Board updated to {board.title}")

        # currently, this condition is true
        if self.request.headers.get('HX-Request'):
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
        """Render invalid form for HTMX."""
        custom_logger("[BoardUpdate] Form invalid")
        return render(self.request, self.template_name, {"form": form, "board": self.get_object()})


class BoardMembersView(LoginRequiredMixin, BoardMemberRequiredMixin, DetailView):
    """View and manage board members"""
    model = Board
    template_name = "boards/partials/board_members.html"
    context_object_name = "board"
    pk_url_kwarg = 'board_id'

    def get_context_data(self, **kwargs):
        """Add memberships and members to context."""
        context = super().get_context_data(**kwargs)
        board = self.object
        memberships = board.memberships.select_related('user').all()
        members = [membership.user for membership in memberships]
        context['memberships'] = memberships
        context['members'] = members
        return context



# List Views
class HTMXListCreateView(LoginRequiredMixin, BoardMemberRequiredMixin, CreateView):
    """Create a new list via HTMX"""
    model = List
    template_name = "boards/partials/create_list.html"
    form_class = ListForm

    def get(self, request, *args, **kwargs):
        """Render form for HTMX GET requests only."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Pass board_id to template for form action."""
        """Pass board_id to the template for the form's action URL."""
        context = super().get_context_data(**kwargs)
        context['board_id'] = self.kwargs['board_id']
        return context

    def form_invalid(self, form):
        """Render invalid form with errors for HTMX."""
        """
        If the form is invalid, re-render it with the errors and a 400 status code.
        """
        # We need to pass the context again, so we call get_context_data
        context = self.get_context_data(form=form)
        return self.render_to_response(context, status=400)

    def form_valid(self, form):
        """Create list with auto-order, return partial HTML."""
        """
        This method is called on a valid POST request.
        We already know the user has access because of dispatch().
        """
        list_obj = form.save(commit=False)
        list_obj.board = self.board
        max_order = List.objects.filter(board=self.board).aggregate(max_order=Max('order'))['max_order'] or 0
        list_obj.order = max_order + 1
        list_obj.save()

        list_column_html = render_to_string(
            "boards/partials/list_column.html", 
            {"list": list_obj, "board": self.board}
        )
        response = HttpResponse(list_column_html)
        trigger_data = {
            "listCreated": True,
            "showMessage": f"List '{list_obj.title}' created successfully."
        }
        response['HX-Trigger'] = json.dumps(trigger_data)
        return response

class HTMXListUpdateView(LoginRequiredMixin, BoardMemberRequiredMixin, UpdateView):
    """Update a list via HTMX"""
    model = List
    template_name = "boards/partials/update_list.html"
    form_class = ListForm

    def get(self, request, *args, **kwargs):
        """Render partial/full template based on request type."""
        # For HTMX requests, return partial template
        if request.headers.get('HX-Request'):
            return super().get(request, *args, **kwargs)

        # For regular requests, return full template response
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Fetch list object for the board."""
        return get_object_or_404(List, id=self.kwargs['list_id'], board=self.board)

    def get_context_data(self, **kwargs):
        """Add board and list to context."""
        context = super().get_context_data(**kwargs)
        context['board'] = self.board
        context['list'] = self.object
        return context

    def form_valid(self, form):
        """Save changes and return updated list column HTML."""
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



class HTMXListDetailView(LoginRequiredMixin, BoardMemberRequiredMixin, DetailView):
    """View a list's details via HTMX"""

    model = List
    template_name = "boards/partials/list_detail.html"
    context_object_name = 'list'

    def get(self, request, *args, **kwargs):
        """Render partial/full template based on request type."""
        # For HTMX requests, return partial template
        if request.headers.get('HX-Request'):
            return super().get(request, *args, **kwargs)

        # For regular requests, return full template response
        return super().get(request, *args, **kwargs)

    def get_object(self):
        """Fetch list object for the board."""
        return get_object_or_404(List, id=self.kwargs['list_id'], board=self.board)

    def get_context_data(self, **kwargs):
        """Add cards, board, and list to context."""
        context = super().get_context_data(**kwargs)
        list_obj = self.object
        context['cards'] = list_obj.cards.all().order_by('order')
        context['board'] = self.board
        context['list'] = list_obj # self.board.lists.all().order_by('order')
        custom_logger(f"context: {context}")
        return context

class HTMXListDeleteView(LoginRequiredMixin, BoardMemberRequiredMixin, View):
    """Delete a list via HTMX"""

    def delete(self, request, board_id, list_id):
        """Delete list and return success JSON."""
        list_obj = get_object_or_404(List, id=list_id, board=self.board)
        list_obj.delete()
        return JsonResponse({"success": True}, status=200)




# Card Views
class HTMXCardDeleteView(LoginRequiredMixin, BoardMemberRequiredMixin, View):
    """Delete a card via HTMX"""

    def delete(self, request, board_id, list_id, card_id):
        """Delete card and return success JSON."""
        card = get_object_or_404(Card, id=card_id, list__board=self.board)
        card.delete()
        return JsonResponse({"success": True}, status=200)


class HTMXCardCreateView(LoginRequiredMixin, BoardMemberRequiredMixin, CreateView):
    """Create a new card via HTMX"""
    model = Card
    form_class = CardForm
    template_name = "boards/partials/create_card.html"

    def get_form_kwargs(self):
        """Pass board to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['board'] = self.board
        return kwargs

    def get(self, request, *args, **kwargs):
        """Render form for HTMX GET requests only."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")
        form = self.form_class(board=self.board)
        return render(request, self.template_name, {
            "form": form,
            "board_id": self.kwargs['board_id'],
            "list_id": self.kwargs['list_id']
        })

    def form_valid(self, form):
        """Create card with auto-order, save M2M, return partial HTML."""
        card_list = get_object_or_404(List, id=self.kwargs['list_id'], board=self.board)
        
        card = form.save(commit=False)
        card.list = card_list
        max_order = Card.objects.filter(list=card_list).aggregate(max_order=Max('order'))['max_order'] or 0
        card.order = max_order + 1
        card.save()
        
        form.save_m2m()

        custom_logger(f"Card '{card.title}' created in list '{card_list.title}'")

        card_item_html = render_to_string("boards/partials/card_item.html", {
            "card": card,
            "board": self.board,
            "list": card_list
        })
        
        response = HttpResponse(card_item_html)
        trigger_data = {
            "cardCreated": True,
            "showMessage": f"Card '{card.title}' created."
        }
        response['HX-Trigger'] = json.dumps(trigger_data)
        return response

    def form_invalid(self, form):
        """Render invalid form for HTMX."""
        custom_logger(f"HTMXCardCreateView form invalid: {form.errors}", Fore.RED)
        return render(self.request, self.template_name, {
            "form": form,
            "board_id": self.kwargs['board_id'],
            "list_id": self.kwargs['list_id']
        }, status=400)


class HTMXCardUpdateView(LoginRequiredMixin, BoardMemberRequiredMixin, View):
    """Update a card via HTMX"""

    def get(self, request, board_id, list_id, card_id):
        """Render form for card update."""
        card = get_object_or_404(Card, id=card_id, list__board=self.board)
        form = CardForm(instance=card, board=self.board)
        context = {
            "form": form,
            "card": card,
            "board": self.board,
            "list_id": list_id
        }

        # For HTMX requests, return partial template
        if request.headers.get('HX-Request'):
            return render(request, "boards/partials/card_update.html", context)

        # For regular requests, return full template response
        return render(request, "boards/card_update.html", context)

    def post(self, request, board_id, list_id, card_id):
        """Save card changes and return updated HTML or redirect."""
        card = get_object_or_404(Card, id=card_id, list__board=self.board)
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, "Card updated successfully")

            # For HTMX requests, return the updated card HTML
            if request.headers.get('HX-Request'):
                card_item_html = render_to_string("boards/partials/card_item.html", {
                    "card": card,
                    "board": self.board,
                    "list": card.list
                })
                response = HttpResponse(card_item_html)
                trigger_data = {
                    "cardUpdated": True,
                    "showMessage": f"Card '{card.title}' updated successfully."
                }
                response['HX-Trigger'] = json.dumps(trigger_data)
                return response
            else:
                return redirect("boards:card_detail", board_id=board_id, list_id=list_id, card_id=card_id)

        # For invalid forms, return the form with errors
        context = {
            "form": form,
            "card": card,
            "board": self.board,
            "list_id": list_id
        }

        # For HTMX requests, return partial template
        if request.headers.get('HX-Request'):
            return render(request, "boards/partials/card_update.html", context, status=400)

        # For regular requests, return full template response
        return render(request, "boards/card_update.html", context, status=400)


class HTMXCardDetailView(LoginRequiredMixin, BoardMemberRequiredMixin, DetailView):
    """View a card's details via HTMX"""

    model = Card
    template_name = "boards/card_detail.html"
    context_object_name = "card"

    def get(self, request, *args, **kwargs):
        """Render detail for HTMX requests only."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Fetch card object for the board."""
        card_id = self.kwargs.get("card_id")
        return get_object_or_404(Card, id=card_id, list__board=self.board)

    def get_context_data(self, **kwargs):
        """Add list and board to context."""
        context = super().get_context_data(**kwargs)
        card = self.object
        context["card"] = card
        context["list"] = card.list
        context["board"] = card.list.board
        return context



class HTMXCardAssignMembersView(LoginRequiredMixin, BoardMemberRequiredMixin, View):
    """Assign multiple members to a card via HTMX"""

    def post(self, request, board_id, list_id, card_id):
        """Assign selected members to card and redirect."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")

        card = get_object_or_404(Card, id=card_id, list__board=self.board)
        member_ids = request.POST.getlist('member_ids')

        # Validate member_ids
        valid_members = self.board.memberships.filter(user_id__in=member_ids).values_list('user_id', flat=True)
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
    board = get_object_or_404(Board, id=board_id)
    # Ensure the requester is a member or the owner
    if not (board.owner == request.user or board.memberships.filter(user=request.user, is_active=True).exists()):
        raise PermissionDenied("You are not authorized to add members to this board.")

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


class HTMXCardMoveView(LoginRequiredMixin, BoardMemberRequiredMixin, View):
    """Move a card to another list via HTMX PUT request."""
    
    @transaction.atomic
    def put(self, request, board_id, list_id, card_id):
        """Move card, update version, reorder cards in target list."""
        if not request.headers.get('HX-Request'):
            return HttpResponseBadRequest("This endpoint is for HTMX requests only")

        custom_logger(f"In PUT method for moving card_id: {card_id}", Fore.GREEN)
        
        from django.http import QueryDict
        put_data = QueryDict(request.body)

        to_list_id = put_data.get('to_list_id')
        new_index = int(put_data.get('new_index', 0))
 
        if not to_list_id:
            return HttpResponse("Missing 'to_list_id' in request.", status=400)

        card = get_object_or_404(Card, id=card_id, list__board=self.board)
        to_list = get_object_or_404(List, id=to_list_id, board=self.board)
        
        card.list = to_list
        card.version += 1
        card.save(update_fields=['list', 'version'])
        
        # Reorder cards
        other_cards = to_list.cards.exclude(id=card.id).order_by('order')
        card_list_for_reorder = list(other_cards)
        card_list_for_reorder.insert(new_index, card)
        
        for index, c in enumerate(card_list_for_reorder):
            c.order = index
            c.save(update_fields=['order'])
        
        custom_logger("Card reordering complete.", Fore.GREEN)
        return HttpResponse(status=200)


class MemberRemoveView(LoginRequiredMixin, BoardAdminRequiredMixin, View):
    """
    Handles the deletion of a board membership.
    Only accessible to board admins/owners.
    """

    def delete(self, request, *args, **kwargs):
        membership_id = self.kwargs.get('membership_id')
        membership = get_object_or_404(Membership, id=membership_id, board=self.board)

        # Business Rule: Cannot remove the owner.
        if membership.role == Membership.ROLE_OWNER:
            return HttpResponse("Cannot remove the board owner.", status=400)
            
        membership.delete()
        # For HTMX, we can return a 200 OK which will cause the target element to be empty.
        return HttpResponse(status=200)


class MemberRoleUpdateView(LoginRequiredMixin, BoardAdminRequiredMixin, View):
    """
    Handles updating a member's role.
    Only accessible to board admins/owners.
    """
    def post(self, request, *args, **kwargs):
        membership_id = self.kwargs.get('membership_id')
        membership = get_object_or_404(Membership, id=membership_id, board=self.board)
        
        new_role = request.POST.get('role')
        
        # Validate the new role
        valid_roles = [role[0] for role in Membership.ROLE_CHOICES]
        try:
            new_role = int(new_role)
            if new_role not in valid_roles:
                raise ValueError
        except (ValueError, TypeError):
            return HttpResponse("Invalid role provided.", status=400)

        # Business Rule: Cannot change the owner's role.
        if membership.role == Membership.ROLE_OWNER:
            return HttpResponse("Cannot change the owner's role.", status=400)

        membership.role = new_role
        membership.save()
        
        # For HTMX, we can return a partial of the updated member row.
        # (For now, a simple 200 OK is enough to pass the test)
        return HttpResponse(status=200)
