from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Count, F
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from mplayer import MPlayerControl
from models import Song
from forms import UploadMp3FileForm

import logging

class N:
    pass

def index(request):
    songs = Song.objects.filter(is_playing=False).annotate(nr_votes=Count('votes')).order_by('-nr_votes')
    votes = songs.filter(votes=request.user)
    current_song = N()
    try:
        current_song = Song.objects.filter(is_playing=True)[0]
    except IndexError:
        current_song.title = 'hello'
    
    return render_to_response('player/index.html', {'request': request, 'songs': songs, 'votes': votes, 'current_song': current_song})

def start(request):
    MPlayerControl.start()
    return HttpResponseRedirect(reverse('player-index'))


def stop(request):
    MPlayerControl.stop()
    return HttpResponseRedirect(reverse('player-index'))


def play(request):
    MPlayerControl.play()
    return HttpResponseRedirect(reverse('player-index'))


def pause(request):
    MPlayerControl.pause()
    return HttpResponseRedirect(reverse('player-index'))


def skip(request):
    MPlayerControl.skip()
    return HttpResponseRedirect(reverse('player-index'))


def add(request):
    return HttpResponse('hello')


def remove(request):
    return HttpResponse('hello')

def upload_file(request):
    if request.method == 'POST':
        pass
    else:
        pass
    
        


@login_required
def vote(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    try:
        Song.objects.get(pk=song.pk, votes=request.user)
    except ObjectDoesNotExist as ex:
        song.votes.add(request.user)
        song.votes.save()
    finally:
        return HttpResponseRedirect(reverse('player-index'))