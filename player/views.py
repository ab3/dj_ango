from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from mplayer import MPlayerControl
from models import Song
from forms import UploadMp3FileForm
from handlers import handle_upload_mp3file, handle_add_youtubevideo, handle_add_daapfile

import logging

MUSIC_PATH = '/Users/abe/Code/dj_ango/music/'

def index(request):
    songs = Song.objects.filter(is_playing=False).annotate(nr_votes=Count('votes')).order_by('-nr_votes')
    votes = songs.filter(votes=request.user)
    status = MPlayerControl.status().split(',')
    status_dict = {
        'is_file_loaded': True if status[0] == 'True' else False,
        'is_playing': True if status[1] == 'True' else False,
        'length': int(status[2]),
        'position': int(status[3]),
    }
    try:
        current_song = Song.objects.filter(is_playing=True)[0]
    except IndexError:
        logging.debug('epic fail')
        current_song = None
    mp3file_form = UploadMp3FileForm()
    return render_to_response('player/index.html', {
        'request': request,
        'songs': songs,
        'votes': votes,
        'current_song': current_song,
        'status_dict': status_dict,
        'mp3file_form': mp3file_form,
    })

def status(request):
    status = MPlayerControl.status().split(',')
    status_dict = {
        'is_file_loaded': True if status[0] == 'True' else False,
        'is_playing': True if status[1] == 'True' else False,
        'length': int(status[2]),
        'position': int(status[3]),
    }

@login_required
def start(request):
    MPlayerControl.start()
    return HttpResponseRedirect(reverse('player-index'))


@login_required
def stop(request):
    MPlayerControl.stop()
    return HttpResponseRedirect(reverse('player-index'))


@login_required
def play(request):
    MPlayerControl.play()
    return HttpResponseRedirect(reverse('player-index'))


@login_required
def pause(request):
    MPlayerControl.pause()
    return HttpResponseRedirect(reverse('player-index'))


@login_required
def skip(request):
    r = MPlayerControl.skip()
    logging.debug('skip')
    return HttpResponseRedirect(reverse('player-index'))


def add(request):
    return HttpResponse('hello')


def remove(request):
    return HttpResponse('hello')


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadMp3FileForm(request.POST, request.FILES)
        logging.debug('upload'+str(form.errors))
        if form.is_valid():
            file_path = handle_upload_mp3file(request.FILES['mp3_file'])
            
            # Determen the play time of the uploaded mp3
            import eyeD3
            if eyeD3.isMp3File(file_path):
                logging.debug(file_path)
                audio_file = eyeD3.Mp3AudioFile(file_path)
                duration = audio_file.getPlayTime()
                
                song = Song(
                    title=form.cleaned_data['title'],
                    duration=duration,
                    file_path=file_path)
                song.save()
                return HttpResponseRedirect(reverse('player-index'))
            else:
                # return error: The uploaded file is not a mp3
                return HttpResponseRedirect(reverse('player-index'))
    else:
        form = UploadMp3FileForm()
    return HttpResponseRedirect(reverse('player-index'))


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