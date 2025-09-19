# apps/boards/tests/test_card_views.py

import json
from django.urls import reverse
from .base_test import BaseBoardTestCase
from apps.boards.models import Card, List

class TestCardListView(BaseBoardTestCase):
    """
    Tests for listing cards within a list.
    Note: Card listing is part of BoardDetailView, which is already tested.
    This class is a placeholder for any future dedicated card list view.
    No tests are needed here for now as the behavior is covered in TestBoardDetailView.
    """
    pass

class TestCardDetailView(BaseBoardTestCase):
    """
    Tests for the HTMXCardDetailView.
    URL: /boards/<board_id>/lists/<list_id>/cards/<card_id>/
    """
    def setUp(self):
        self.url = reverse('boards:card_detail', kwargs={
            'board_id': self.board.id,
            'list_id': self.list1.id,
            'card_id': self.card1.id
        })

    # --- Approach 2: Authorized Access ---
    def test_member_can_view_card_details(self):
        """Tests if an authorized member can view a card's detail page."""
        self.client.login(username='board_member', password='p')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.card1.title)
        # Check if assignee is rendered
        self.assertContains(response, self.member.username)

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_gets_403_for_card_detail(self):
        """Tests that a non-member cannot access a card's detail page."""
        self.client.login(username='non_member', password='p')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class TestCardCreateView(BaseBoardTestCase):
    """
    Tests for the HTMXCardCreateView.
    URL: /boards/<board_id>/lists/<list_id>/cards/create/
    """
    def setUp(self):
        self.url = reverse('boards:create_card', kwargs={'board_id': self.board.id, 'list_id': self.list1.id})

    # --- Approach 2: Authorized Access ---
    def test_member_can_create_card(self):
        """Tests successful card creation by an authorized member."""
        self.client.login(username='board_member', password='p')
        card_count_before = Card.objects.filter(list=self.list1).count()
        post_data = {
            'title': 'A brand new card',
            'description': 'Test description',
            'priority': Card.PRIORITY_LOW,
            'assignees': [self.owner.pk]
        }
        
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Card.objects.filter(list=self.list1).count(), card_count_before + 1)
        
        new_card = Card.objects.get(title='A brand new card')
        self.assertTrue(new_card.assignees.filter(pk=self.owner.pk).exists())
        self.assertIn('cardCreated', response.headers.get('HX-Trigger', ''))

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_cannot_create_card(self):
        """Tests that a non-member is forbidden from creating a card."""
        self.client.login(username='non_member', password='p')
        post_data = {'title': 'Illegal Card'}
        response = self.client.post(self.url, post_data, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 403) # Based on the updated permission helpers
        self.assertFalse(Card.objects.filter(title='Illegal Card').exists())


class TestCardUpdateView(BaseBoardTestCase):
    """
    Tests for the HTMXCardUpdateView.
    URL: /boards/<board_id>/lists/<list_id>/cards/<card_id>/update/
    """
    def setUp(self):
        self.url = reverse('boards:card_update', kwargs={
            'board_id': self.board.id,
            'list_id': self.card1.list.id,
            'card_id': self.card1.id
        })

    # --- Approach 2: Authorized Access ---
    def test_member_can_update_card(self):
        """Tests if a board member can update a card's details."""
        self.client.login(username='board_member', password='p')
        post_data = {
            'title': 'Updated Card Title',
            'description': self.card1.description,
            'priority': Card.PRIORITY_TOP,
            'assignees': [self.owner.pk, self.member.pk] # Update assignees
        }
        response = self.client.post(self.url, post_data)

        # The view redirects to the card detail page on success
        self.assertEqual(response.status_code, 302)
        
        self.card1.refresh_from_db()
        self.assertEqual(self.card1.title, 'Updated Card Title')
        self.assertEqual(self.card1.assignees.count(), 2)

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_cannot_update_card(self):
        """Tests that a non-member gets a 403 when trying to update a card."""
        self.client.login(username='non_member', password='p')
        post_data = {'title': 'Should not update'}
        response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 403)


class TestCardDeleteView(BaseBoardTestCase):
    """
    Tests for the HTMXCardDeleteView.
    URL: /boards/<board_id>/lists/<list_id>/cards/<card_id>/delete/
    """
    def setUp(self):
        # Create a disposable card for deletion tests
        self.card_to_delete = Card.objects.create(list=self.list1, order=99, title='Card to Delete')
        self.url = reverse('boards:card_delete', kwargs={
            'board_id': self.board.id,
            'list_id': self.list1.id,
            'card_id': self.card_to_delete.id
        })
        
    # --- Approach 2: Authorized Access ---
    def test_member_can_delete_card(self):
        """Tests successful card deletion by an authorized member."""
        self.client.login(username='board_member', password='p')
        
        card_id = self.card_to_delete.id
        self.assertTrue(Card.objects.filter(id=card_id).exists())
        
        # Act: Send a DELETE request via HTMX
        response = self.client.delete(self.url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200) # Your view returns a 200 OK with JSON
        self.assertFalse(Card.objects.filter(id=card_id).exists())

    # --- Approach 3: Unauthorized Access ---
    def test_non_member_cannot_delete_card(self):
        """Tests that a non-member gets a 403 when trying to delete a card."""
        self.client.login(username='non_member', password='p')
        response = self.client.delete(self.url, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Card.objects.filter(id=self.card_to_delete.id).exists())
