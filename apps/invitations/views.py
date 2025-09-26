from django.views.generic import FormView, View  # Change CreateView to FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.http import Http404

from apps.boards.views import custom_404
from custom_tools.logger import custom_logger
from celery.exceptions import OperationalError as CeleryOperationalError  # For specific catch

from .models import Invitation
from .forms import InvitationSendForm
from .tasks import send_invitation_email
from apps.boards.permissions import BoardAdminRequiredMixin



class InvitationCreateView(LoginRequiredMixin, BoardAdminRequiredMixin, FormView):
    """
    Handles sending an invitation to a new member.
    Accessible only to board admins/owners.
    """
    form_class = InvitationSendForm
    template_name = 'invitations/send_invitation.html'

    def get_form_kwargs(self):
        """Pass the board object to the form for validation."""
        kwargs = super().get_form_kwargs()
        kwargs['board'] = self.board  # self.board is from the mixin
        return kwargs

    def form_valid(self, form):
        custom_logger(f"Form valid: {form.cleaned_data}")
        invitation = Invitation.objects.create(
            email=form.cleaned_data['email'],
            board=self.board,
            inviter=self.request.user
        )
        custom_logger(f"Invitation created: {invitation.id}")

        # Queue email task asynchronously (non-blocking; log if fails)
        try:
            send_invitation_email.delay(invitation.id)
            custom_logger(f"Email task queued for invitation {invitation.id}")
        except CeleryOperationalError as e:
            custom_logger(f"Failed to queue email task for {invitation.id}: {str(e)}")
            # Don't raise; invitation still created/successful for user
        except Exception as e:
            custom_logger(f"Unexpected error queuing email for {invitation.id}: {str(e)}")
            # Optional: Track in DB (e.g., invitation.email_sent = False)

        messages.success(self.request, f"Invitation sent to {invitation.email}.")
        return redirect(reverse_lazy('boards:board_detail', kwargs={'board_id': self.board.id}))
    

class InvitationAcceptView(View):
    """
    Handles a user clicking an invitation link.
    It validates the token and decides what to do based on the user's auth state.
    """
    def get(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        
        # 1. Find a valid, active invitation with this token
        try:
            # We look for an invitation that matches the token and is still 'sent'
            invitation = Invitation.objects.get(token=token, status=Invitation.STATUS_SENT)
            
            # Check if the invitation has expired using our helper method
            if not invitation.is_active():
                messages.error(request, "This invitation link has expired.")
                # TDD FIX: This now raises Http404, which results in a 404 response
                raise Http404 
                
        except Invitation.DoesNotExist:
            messages.error(request, "This invitation link is invalid or has already been used.")
            # TDD FIX: This now raises Http404
            raise Http404

        # --- If the invitation is valid, decide what to do next ---

        # 2. If the user is already authenticated (logged in)
        if request.user.is_authenticated:
            # We must ensure the logged-in user's email matches the invitation,
            # unless we want to allow any logged-in user to claim it.
            # For higher security, we'll check.
            if request.user.email.lower() != invitation.email.lower():
                messages.warning(request, f"This invitation was sent to {invitation.email}, but you are logged in as {request.user.email}. Please log out and try again.")
                return redirect(reverse_lazy('boards:boards_list')) # Redirect to a safe page

            # The user is correct, accept the invitation and add them to the board
            invitation.accept(request.user)
            messages.success(request, f"Welcome! You have successfully joined the board '{invitation.board.title}'.")
            
            # TDD FIX: Redirect to the board detail page
            return redirect(reverse_lazy('boards:board_detail', kwargs={'board_id': invitation.board.id}))

        # 3. If the user is NOT authenticated
        else:
            # Store the token in the session, so we can retrieve it after signup/login
            request.session['invitation_token'] = str(token)
            
            # TDD FIX: Redirect to the signup page, pre-filling the email address
            signup_url = reverse('account_signup')
            return redirect(f'{signup_url}?email={invitation.email}')
