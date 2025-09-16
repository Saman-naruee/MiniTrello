from django.test import TestCase
from apps.boards.forms import BoardForm # Assuming you have a BoardForm

class BoardFormTest(TestCase):
    def test_valid_data(self):
        form = BoardForm(data={'title': 'Test Board', 'color': 'blue'})
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = BoardForm(data={'title': '', 'color': 'blue'})
        self.assertFalse(form.is_valid())

    def test_title_length_validation(self):
        form = BoardForm(data={'title': 'ab', 'color': 'blue'})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
