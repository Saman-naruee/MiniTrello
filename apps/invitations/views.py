from django.views.generic import FormView, View  # Change CreateView to FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


from .models import Invitation
from .forms import InvitationSendForm
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
        kwargs['board'] = self.board # self.board is from the mixin
        return kwargs

    def form_valid(self, form):
        # Create the invitation object
        invitation = Invitation.objects.create(
            email=form.cleaned_data['email'],
            board=self.board,
            inviter=self.request.user
        )

        # Build the acceptance link
        accept_url = self.request.build_absolute_uri(
            reverse_lazy('invitations:accept_invitation', kwargs={'token': invitation.token})
        )
        
        # Prepare email context
        context = {
            'inviter_name': self.request.user.username,
            'board_name': self.board.title,
            'accept_url': accept_url,
        }
        
        # Render the email content from templates
        subject = f"You're invited to join the board '{self.board.title}'"
        html_message = render_to_string('emails/invitation_email.html', context)
        plain_message = render_to_string('emails/invitation_email.txt', context)

        # Send the actual email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            html_message=html_message,
            fail_silently=False
        )
        
        messages.success(self.request, f"Invitation sent to {invitation.email}.")
        return redirect('boards:board_detail', board_id=self.board.id)
    

class InvitationAcceptView(LoginRequiredMixin, View):
    """Handles accepting an invitation to join a board."""
    pass
