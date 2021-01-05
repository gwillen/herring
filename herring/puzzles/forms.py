from django.contrib.auth.forms import UserCreationForm
from django import forms

from puzzles.models import UserProfile


class UserSignupForm(UserCreationForm):
    magic_secret = forms.CharField(
        label="Magic Secret",
        strip=False,
        widget=forms.PasswordInput(),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'first_name', 'last_name', 'email',)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('discord_identifier', 'avatar_url')
