from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.conf import settings

from .models import Round, Puzzle, UserProfile

class HuntIdListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Hunt ID'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'hunt_id'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            # Only ofer the current hunt; hide all others
            (settings.HERRING_HUNT_ID, settings.HERRING_HUNT_ID),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        return queryset.filter(hunt_id = self.value())

    # always filter for only the current hunt
    def value(self):
        return settings.HERRING_HUNT_ID

class PuzzleInline(admin.TabularInline):
    model = Puzzle
    extra = 1
    exclude = ('answer', 'note', 'tags', 'sheet_id')


class RoundAdmin(admin.ModelAdmin):
    inlines = [PuzzleInline]
    list_display = ('__str__', 'name',)
    list_filter = (HuntIdListFilter,)
    search_fields = ['name']
    readonly_fields = ('discord_categories',)


class PuzzleAdmin(admin.ModelAdmin):
    exclude = ('answer', 'note', 'tags', 'sheet_id')
    readonly_fields = ('slack_channel_id',)
    list_filter = (HuntIdListFilter,)
    search_fields = ['name']


class UserProfileAdmin(admin.ModelAdmin):
    pass


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "profile"


class UserAdminWithProfile(UserAdmin):
    inlines = (UserProfileInline, )


admin.site.unregister(User)
admin.site.register(User, UserAdminWithProfile)
admin.site.register(Round, RoundAdmin)
admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
