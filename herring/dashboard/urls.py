from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.home, name='home'),
    path('logs/', views.logs_page, name='logs'),
    path('logs/entries.json', views.log_entries, name='log_entries'),
    path('logs/levels/', views.save_log_levels, name='save_log_levels'),
    path('discord/', views.discord_servers, name='discord'),
    path('discord/snapshots/', views.take_snapshot, name='take_snapshot'),
    path('discord/snapshots/<int:snapshot_id>/', views.snapshot_detail, name='snapshot'),
    path('discord/templates/', views.import_template, name='import_template'),
    path('discord/setup/', views.create_setup_plan, name='create_setup_plan'),
    path('discord/setup/<int:plan_id>/', views.setup_plan_detail, name='setup_plan'),
    path('discord/setup/<int:plan_id>/apply/', views.apply_setup_plan, name='apply_setup_plan'),
]
