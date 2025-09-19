from django import forms
from .models import Board, List, Card, Membership
from django.utils import timezone
from apps.accounts.models import User


class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ["title", "description", "color"]
    
    
    def clean_title(self):
        title = self.cleaned_data["title"] = self.cleaned_data["title"].strip()
        if len(title) <= 3:
            raise forms.ValidationError("Title must be at least 4 characters long")
        return title


class ListForm(forms.ModelForm):

    class Meta:
        model = List
        fields = ["title"]
    

    def clean_title(self):
        title = self.cleaned_data["title"] = self.cleaned_data["title"].strip()
        if len(title) <= 1:
            raise forms.ValidationError("Title must be at least 2 characters long")
        return title

class CardForm(forms.ModelForm):
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Card
        fields = ["title", "description", "priority", "due_date", "assignees"]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            # Using checkbox for assignees
            'assignees': forms.CheckboxSelectMultiple,
        }

    # This method is crucial for filtering the assignees options
    def __init__(self, *args, **kwargs):
        # Get the board object from the view
        board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)

        if board:
            # Limit the assignees field options to only the members of this board.
            board_members = User.objects.filter(memberships__board=board, memberships__is_active=True)
            self.fields['assignees'].queryset = board_members

    def clean_title(self):
        title = self.cleaned_data["title"] = self.cleaned_data["title"].strip()
        if len(title) <= 1:
            raise forms.ValidationError("Title must be at least 2 characters long")
        return title

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError("Due date cannot be in the past")
        return due_date


class MembershipForm(forms.ModelForm):


    class Meta:
        model = Membership
        fields = ['user', 'role']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)

    def clean_user(self):
        user = self.cleaned_data['user']
        if self.board and Membership.objects.filter(board=self.board, user=user).exists():
            raise forms.ValidationError("This user is already a member of this board.")
        return user
