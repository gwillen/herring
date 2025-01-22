from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from puzzles.models import UserProfile

class UserSignupForm(UserCreationForm):
    magic_secret = forms.CharField(
        label="Magic Secret",
        strip=False,
        widget=forms.PasswordInput(),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'first_name', 'last_name', 'email',)

class UserEditForm(forms.ModelForm):
    username = forms.CharField(disabled=True)
    email = forms.CharField(disabled=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email',)

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('discord_identifier', 'subscriptions')
        # Exclude avatar_url because, to my knowledge, it's literally never used.
