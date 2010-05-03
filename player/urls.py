from django.conf.urls.defaults import *
from player import views


urlpatterns = patterns('',
    url(r'^$', views.index, name='player-index'),
    url(r'^play/$', views.play, name='player-play'),
    url(r'^pause/$', views.pause, name='player-pause'),
    url(r'^skip/$', views.skip, name='player-skip'),
    url(r'^add/$', views.add, name='player-add'),
    url(r'^vote/(?P<song_id>\d+)/$', views.vote, name='player-vote'),
    
    # Adding File
    url(r'^upload_file/$', views.upload_file, name='player-upload_file'),
    
    # Active
    url(r'^start/$', views.start, name='player-start'),
    url(r'^stop/$', views.stop, name='player-stop'),
)