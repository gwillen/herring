from django.contrib.auth.forms import UserCreationForm
from django import forms

from puzzles.models import UserProfile


class UserSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ('username', 'first_name', 'last_name', 'email',)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('discord_identifier', 'avatar_url')
