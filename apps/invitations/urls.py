from django.urls import path
from . import views

app_name = 'invitations'

urlpatterns = [
    path('boards/<int:board_id>/invite/', views.InvitationCreateView.as_view(), name='send_invitation'),
    path('accept/<uuid:token>/', views.InvitationAcceptView.as_view(), name='accept_invitation'),
]
