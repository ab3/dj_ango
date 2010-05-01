# More info about mplayer http://www.mplayerhq.hu/DOCS/tech/slave.txt
import os
import sys
import logging
from select import select, error
from socket import socket, AF_UNIX, SOCK_DGRAM
from SocketServer import UnixDatagramServer, TCPServer, BaseRequestHandler, StreamRequestHandler
from subprocess import Popen, PIPE
from multiprocessing import Process, Queue
from django.db.models import Count
from models import Song

IGNORE = open(os.devnull, 'r+')
FILE_SOCKET = '/tmp/dj_ango_musicplayer.sock'

# Debug
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s')


class MPlayerWrapper:
    def __init__(self):
        def read_mplayer_pipe(fd, q):
            while True:
                output = select([fd], [], [])[0][0]
                q.put(output.readline())
        
        cmd = ['mplayer', '-slave', '-quiet', '-idle']
        self._mp = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=IGNORE)
        self._q = Queue()
        self._p = Process(target=read_mplayer_pipe, args=(self._mp.stdout, self._q))
        self._p.start()
        self._write = self._mp.stdin.write
        self._read = self._q.get # unpack list, allways use first element
        self._read() # Clean
        self._read() # Clean
    
    def __del__(self):
        self.quit()
    
    def _flush(self):
        while not self._q.empty():
            self._q.get()

    def get_filename(self):
        self._flush()
        self._write('pausing_keep_force get_property filename\n')
        return  self._read().partition('=')[2].rstrip()
    
    def get_length(self):
        self._flush()
        self._write('pausing_keep_force get_property length\n')
        return  int(float(self._read().partition('=')[2]))
    
    def loadfile(self, path):
        self._write('pausing_keep_force loadfile %s\n' % (path))
    
    def get_path(self):
        self._flush()
        self._write('pausing_keep_force get_property path\n')
        return  self._read().partition('=')[2]

    def is_playing(self):
        self._flush()
        self._write('pausing_keep_force get_property pause\n')
        return self._read().partition('=')[2] == 'no\n'
    
    def play(self):
        if not self.is_playing():
            self._write('pause\n')

    def pause(self):
        if self.is_playing():
            self._write('pause\n')
    
    def get_position(self):
        self._flush()
        self._write('pausing_keep_force get_property time_pos\n')
        return  int(float(self._read().partition('=')[2]))
        
    def quit(self):
        if self._mp.poll() is None:
            self._mp.communicate('quit\n')
        self._mp_send = None
        self._mp_recv = None
    
    def status(self):
        if self._mp.poll() is not None:
            return None
        else:
            # tuple (stopped, playing, time_length, time_pos)
            return tuple(self.is_playing(), self.get_length(), self.get_position())
    
    def stop(self):
        self._write('stop\n')

class MPlayerHandler(StreamRequestHandler):
    def __init__(self):
        self._mp = MPlayerWrapper()
        self._active = False
    
    def dispatch(self, s):
        pass
    
    def handle(self):
        data = self.rfile.readline().strip()
        dispatch(data)
        self.wfile.write('hello')
        
        


class MPlayerDispatch:
    def __init__(self, file_socket):
        self._mp = MPlayerWrapper()
        self.socket = socket(AF_UNIX, SOCK_DGRAM)
        self.socket.bind(file_socket)
        self.active = False

    def run(self):
        data = ''
        #self.socket.listen(1)
        #conn, addr = self.socket.accept()
        while True:
            data += self.socket.recv(1024)
            logging.debug('run: '+data)

            # Dispatch command
            if data.startswith('play'):
                self._mp.play()
                data = data.replace('play', '', 1)
            elif data.startswith('pause'):
                self._mp.pause()
                data = data.replace('pause', '', 1)
            elif data.startswith('skip'):
                self._mp.skip()
                data = data.replace('skip', '', 1)
            elif data.startswith('start'):
                logging.debug('start')
                self.active = True
                try:
                    song = Song.objects.filter(is_playing=False).annotate(nr_votes=Count('votes')).order_by('-nr_votes')[0]
                except IndexError:
                    pass
                else:
                    song.is_playing = True
                    for user in song.votes.all():
                        song.votes.remove(user)
                    song.save()
                    self._mp.loadfile(song.file_path)
                data = data.replace('skip', '', 1)
            elif data.startswith('stop'):
                logging.debug('stop')
                self.active = False
                try:
                    song = Song.objects.filter(is_playing=True)[0]
                except IndexError:
                    pass
                else:
                    song.is_playing = False
                    song.save()
                    #song.delete()
                    # delete song
                    #self._mp.loadfile(song.file_path)
                data = data.replace('skip', '', 1)
            elif data.startwith('info'):
                logging.debug('info')

            # Check if mplayer is still playing
            # filename will return a empty string if
            # mplayer isn't playing anything
            if not self._mp.get_filename() and self.active:
                try:
                    current_song = Song.objects.filter(is_playing=True)[0]
                    next_song = Song.objects.filter(is_playing=False).annotate(nr_votes=Count('votes')).order_by('-nr_votes')[0]
                except IndexError:
                    pass
                else:
                    # Remove current song
                    current_song.is_playing = False
                    for user in current_song.votes.all():
                        current_song.votes.remove(user)
                    current_song.save()
                        
                    #os.remove(current_song.file_path)
                    #current_song.delete()
                    
                    #start playing next song
                    next_song.is_playing = True
                    next_song.save()
                    self._mp.loadfile(current_song.file_path)


class MPlayerControl:
    @classmethod
    def get_socket(cls):
        s = None
        try:
            s = socket(AF_UNIX, SOCK_DGRAM)
        except error, msg:
            logging.debug(msg)
            sys.exit(1)
        try:
            s.connect(FILE_SOCKET)
        except error, msg:
            s.close()
            logging.debug(msg)
            sys.exit(1)
        return s
        
    @classmethod
    def play(cls):
        s = cls.get_socket()
        s.send('play')
        s.close()
    
    @classmethod
    def pause(cls):
        s = cls.get_socket()
        s.send('pause')
        s.close()

    @classmethod
    def skip(cls):
        s = cls.get_socket()
        s.send('skip')
        s.close()
    
    @classmethod
    def start(cls):
        s = cls.get_socket()
        s.send('start')
        s.close()

    @classmethod
    def stop(cls):
        s = cls.get_socket()
        s.send('stop')
        s.close()
    
    @classmethod
    def info(cls):
        s = cls.get_socket()
        s.send('info')
        s.close()


def runshell():
    os.system('rm /tmp/dj_ango_musicplayer.sock')
    player = MPlayerDispatch(FILE_SOCKET)
    #player._mp.loadfile('/Users/abe/Code/dj_ango/music/chan.mp3')
    player.run()

def run():
    if sys.argv[1] == 'runserver':
        os.system('rm /tmp/dj_ango_musicplayer.sock')
        player = MPlayerDispatch(FILE_SOCKET)
        #player._mp.loadfile('/Users/abe/Code/dj_ango/music/chan.mp3')
        player.run()


if __name__ == '__main__':
    run()