from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.home, name='home'),
    path('logs/', views.logs_page, name='logs'),
    path('logs/entries.json', views.log_entries, name='log_entries'),
    path('logs/levels/', views.save_log_levels, name='save_log_levels'),
]
