from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^resources/$', views.get_resources, name='resources'),
    url(r'^puzzles/$', views.get_puzzles, name='get'),
    url(r'^webhook/$', views.update_puzzle_hook, name='webhook'),
    url(r'^run_scraper/$', views.run_scraper, name='run_scraper'),
    url(r'^puzzles/(?P<puzzle_id>[0-9]+)/$', views.one_puzzle,
        name='one_puzzle'),
]
