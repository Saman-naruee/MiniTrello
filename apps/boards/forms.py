from django import forms
from .models import Board


class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ["title", "description", "color"]
    

    def clean_title(self):
        title = self.cleaned_data["title"] = self.cleaned_data["title"].strip()
        if len(title) <= 3:
            raise forms.ValidationError("Title must be at least 4 characters long")
        return title
