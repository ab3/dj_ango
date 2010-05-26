import os
import logging

MUSIC_PATH = '/Users/abe/Code/dj_ango/music/'

def handle_upload_mp3file(f):
    nr  = 0
    while True:
        name = MUSIC_PATH+('-%s.' % nr).join(f.name.rsplit('.', 1))
        logging.debug('handle: %s', name)
        if os.path.isfile(name):
            nr += 1
        else:
            try:
                destination = open(name, 'wb+')
            except IOError, msg:
                logging.debug('Handle error:\n'+msg)
                return
            else:
                for chunk in f.chunks():
                    destination.write(chunk)
                destination.close()
                return name
    

def handle_add_youtubevideo():
    pass

 
def handle_add_daapfile():
    pass