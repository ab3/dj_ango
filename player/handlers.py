import os

MUSIC_PATH = '/Users/abe/Code/dj_ang/music/'

def handle_upload_mp3file(f):
    file_saved = False
    nr  = 0
    while not file_saved:
        try:
            destination = open(MUSIC_PATH+f.name+'-%s' % nr, 'wb+')
        except OSError:
            nr += 1
        else:
            for chunk in f.chunks():
                destination.write(chunk)
                destination.close()
            file_saved = True

def handle_add_youtubevideo():
    pass


def handle_add_daapfile():
    pass