from django import forms
from .models import Board, List, Card, Membership, Comment, MiniTask
from django.utils import timezone


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
        fields = ["title", "description", "priority", "due_date", "assignee"]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assignee': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)
        if self.board:
            # Filter assignee choices to only show board members
            members = self.board.memberships.select_related('user').values_list('user', flat=True)
            self.fields['assignee'].queryset = self.fields['assignee'].queryset.filter(id__in=members)

    def clean_assignee(self):
        assignee = self.cleaned_data.get('assignee')
        if assignee and self.board:
            # Verify the assigned user is a board member
            is_member = self.board.memberships.filter(user=assignee).exists()
            if not is_member:
                raise forms.ValidationError("Assignee must be a member of this board")
        return assignee

    def clean_title(self):
        title = self.cleaned_data["title"] = self.cleaned_data["title"].strip()
        if len(title) <= 1:
            raise forms.ValidationError("Title must be at least 2 characters long")
        return title

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date and due_date <= timezone.now().date():
            raise forms.ValidationError("Due date cannot be in the past or today")
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

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

class MiniTaskForm(forms.ModelForm):
    class Meta:
        model = MiniTask
        fields = ['text']
