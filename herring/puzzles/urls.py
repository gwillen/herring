from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^resources/$', views.get_resources, name='resources'),
    url(r'^puzzles/$', views.get_puzzles, name='get'),
    url(r'^puzzles/(?P<puzzle_id>[0-9]+)/$', views.one_puzzle,
        name='one_puzzle'),
]
