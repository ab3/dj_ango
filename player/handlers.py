import os
import logging

MUSIC_PATH = '/Users/abe/Code/dj_ango/music/'

def handle_upload_mp3file(f):
    nr  = 0
    while True:
        try:
            destination = open(MUSIC_PATH+('-%s.' % nr).join(f.name.rsplit('.', 1)), 'wb+')
        except IOError:
            nr += 1
        else:
            for chunk in f.chunks():
                destination.write(chunk)
            destination.close()
            return destination.name

def handle_add_youtubevideo():
    pass

 
def handle_add_daapfile():
    pass