from django.contrib import admin

from .models import Round, Puzzle

class PuzzleInline(admin.TabularInline):
    model = Puzzle
    extra = 1
    exclude = ('answer', 'note', 'tags',)

class RoundAdmin(admin.ModelAdmin):
    inlines = [PuzzleInline]
    list_display = ('__unicode__', 'name',)
    search_fields = ['name']

class PuzzleAdmin(admin.ModelAdmin):
	exclude = ('answer', 'note', 'tags',)
	search_fields = ['name']

admin.site.register(Round, RoundAdmin)
admin.site.register(Puzzle, PuzzleAdmin)