from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

from .models import Invitation
from custom_tools.logger import custom_logger

@shared_task
def send_invitation_email(invitation_id):
    """
    A Celery task to send an invitation email asynchronously.
    """
    try:
        invitation = Invitation.objects.get(pk=invitation_id)
        
        accept_url = f"{settings.BASE_URL.rstrip('/')}{reverse('invitations:accept_invitation', kwargs={'token': invitation.token})}"
        
        context = {
            'inviter_name': invitation.inviter.username,
            'board_name': invitation.board.title,
            'accept_url': accept_url,
        }
        
        subject = f"You're invited to join the board '{invitation.board.title}'"
        html_message = render_to_string('emails/invitation_email.html', context)
        plain_message = render_to_string('emails/invitation_email.txt', context)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            html_message=html_message,
            fail_silently=False
        )
        custom_logger(f"Successfully sent invitation email to {invitation.email} for board {invitation.board.id}", level="SUCCESS")
        return True
    except Invitation.DoesNotExist:
        custom_logger(f"Failed to send invitation: Invitation with id {invitation_id} does not exist.", level="ERROR")
        return False
    except Exception as e:
        custom_logger(f"An unexpected error occurred while sending email: {e}", level="CRITICAL")
        # In production, you might want to retry the task
        return False
