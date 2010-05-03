import os
import logging

MUSIC_PATH = '/Users/abe/Code/dj_ango/music/'

def handle_upload_mp3file(f):
    logging.debug('handler mp3 file')
    #file_saved = False
    nr  = 0
    while True:
        logging.debug('handler mp3 file')
        try:
            destination = open(MUSIC_PATH+('-%s.' % nr).join(f.name.rsplit('.', 1)), 'wb+')
        except IOError:
            nr += 1
        else:
            for chunk in f.chunks():
                destination.write(chunk)
            destination.close()
            return MUSIC_PATH+destination.name

def handle_add_youtubevideo():
    pass


def handle_add_daapfile():
    pass