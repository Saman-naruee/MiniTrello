from django.urls import path

from .views import (
    BoardListView, BoardDetailView,
    HTMXBoardCreateView, HTMXListCreateView, HTMXCardCreateView,
    HTMXBoardDeleteView, HTMXListDeleteView, HTMXCardDeleteView,
    HTMXCardUpdateView
)

app_name = "boards"

urlpatterns = [
    # Main pages
    path("", BoardListView.as_view(), name="boards_list"),
    path("<int:board_id>/", BoardDetailView.as_view(), name="board_detail"),
    
    # Board operations
    path("create/", HTMXBoardCreateView.as_view(), name="create_board"),
    path("<int:board_id>/delete/", HTMXBoardDeleteView.as_view(), name="delete_board"),
    
    # List operations (nested under boards)
    path("lists/create/", HTMXListCreateView.as_view(), name="create_list"),
    path("lists/<int:list_id>/delete/", HTMXListDeleteView.as_view(), name="delete_list"),
    
    # Card operations (nested under lists)
    path("cards/create/", HTMXCardCreateView.as_view(), name="create_card"),
    path("cards/<int:card_id>/update/", HTMXCardUpdateView.as_view(), name="update_card"),
    path("cards/<int:card_id>/delete/", HTMXCardDeleteView.as_view(), name="delete_card"),
]


