from django.contrib import admin

from .models import Round, Puzzle, UserProfile


class PuzzleInline(admin.TabularInline):
    model = Puzzle
    extra = 1
    exclude = ('answer', 'note', 'tags', 'url')


class RoundAdmin(admin.ModelAdmin):
    inlines = [PuzzleInline]
    list_display = ('__str__', 'name',)
    search_fields = ['name']


class PuzzleAdmin(admin.ModelAdmin):
    exclude = ('answer', 'note', 'tags', 'url')
    search_fields = ['name']

class UserProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(Round, RoundAdmin)
admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
