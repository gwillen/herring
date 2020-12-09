from django.forms import ModelForm

from puzzles.models import UserProfile


class UserProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('discord_identifier', 'avatar_url')
