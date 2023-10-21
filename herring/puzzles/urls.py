from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('resources/', views.get_resources, name='resources'),
    path('puzzles/', views.get_puzzles, name='get'),
    #path('run_scraper/', views.run_scraper, name='run_scraper'),
    path('post_discord/', views.post_discord, name='post_discord'),
    path('puzzles/<int:puzzle_id>/', views.one_puzzle, name='one_puzzle'),
    path('s/<int:puzzle_id>', views.puzzle_spreadsheet, name='puzzle_spreadsheet'),
    path('disc/<int:puzzle_id>/<int:use_app>', views.discord_channel_link, name='discord_channel_link'),
]
