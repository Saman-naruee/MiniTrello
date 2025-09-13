from django import forms
from .models import Board, List, Card, Membership
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
