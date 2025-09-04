from django.urls import path

from .views import (
    BoardListView, BoardDetailView,
    HTMXBoardCreateView, HTMXListCreateView, HTMXCardCreateView,
    HTMXBoardDeleteView, HTMXListDeleteView, HTMXCardDeleteView,
    HTMXCardUpdateView, HTMXBoardUpdateView, HTMXBoardDeleteView,
    HTMXListUpdateView, HTMXListDetailView, HTMXCardDetailView
)

urlpatterns = [
    # Main pages
    path("", BoardListView.as_view(), name="boards_list"),
    path("<int:board_id>/", BoardDetailView.as_view(), name="board_detail"),
    
    # Board operations
    path("create/", HTMXBoardCreateView.as_view(), name="create_board"),
    path("<int:board_id>/delete/", HTMXBoardDeleteView.as_view(), name="delete_board"),
    path("<int:board_id>/lists/", HTMXBoardUpdateView.as_view(), name="update_board"),

    # List operations (nested under boards)
    path("<int:board_id>/lists/create/", HTMXListCreateView.as_view(), name="create_list"),
    path("<int:board_id>/lists/<int:list_id>/delete/", HTMXListDeleteView.as_view(), name="delete_list"),
    path("<int:board_id>/lists/<int:list_id>/update/", HTMXListUpdateView.as_view(), name="update_list"),
    path("<int:board_id>/lists/<int:list_id>/", HTMXListDetailView.as_view(), name="list_detail"),

    # Card operations (nested under lists)
    path("<int:board_id>/lists/<int:list_id>/cards/create/", HTMXCardCreateView.as_view(), name="create_card"),
    path("<int:board_id>/lists/<int:list_id>/cards/<int:card_id>/update/", HTMXCardUpdateView.as_view(), name="update_card"),
    path("<int:board_id>/lists/<int:list_id>/cards/<int:card_id>/delete/", HTMXCardDeleteView.as_view(), name="delete_card"),
    path("<int:board_id>/lists/<int:list_id>/cards/<int:card_id>/", HTMXCardDetailView.as_view(), name="card_detail"),
]


