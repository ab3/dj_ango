#
# More info about mplayer http://www.mplayerhq.hu/DOCS/tech/slave.txt
import os
import sys
import logging
from select import select, error
from socket import socket, AF_UNIX, SOCK_STREAM
from SocketServer import UnixStreamServer, StreamRequestHandler
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
        self._flush()
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
            self._flush()
            self._write('play\n')
    
    def pause(self):
        if self.is_playing():
            self._flush()
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
            return (self.is_playing(), self.get_length(), self.get_position())
    
    def stop(self):
        self._write('stop\n')


class MPlayerHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server):
        self._mp = MPlayerWrapper()
        self._active = False
        StreamRequestHandler.__init__(self, request, client_address, server)
    
    def _dispatch(self, s):
        if data == 'play':
            return self._mp.play()
        elif data == 'pause':
            return self._mp.play()
        elif data == 'skip':
            self._dispatch('stop')
            self._dispatch('start')
        elif data == 'start':
            if not self._active:
                try:
                    song = Song.objects.filter(is_playing=False).annotate(nr_votes=Count('votes')).order_by('-nr_votes')[0]
                except IndexError:
                    pass
                else:
                    self._active = True
                    song.is_playing = True
                    song.save()
                    self._mp.loadfile(song.file_path)
        elif data == 'stop':
            if not self._active:
                try:
                    song = Song.objects.filter(is_playing=True)[0]
                except IndexError:
                    pass
                else:
                    self._active = False
                    song.is_playing = False
                    for user in song.votes.all():
                        song.votes.remove(user)
                    song.save()
                    self._mp.stop()
        elif data == 'info':
            return 'jahaaaaaaaaaaaaaaaaa'
    
    def handle(self):
        logging.debug('handle')
        data = self.rfile.readline().strip()
        result = self.dispatch(data)
        self.wfile.write(result)


class MPlayerControl:
    @classmethod
    def get_socket(cls):
        logging.debug('client')
        s = None
        try:
            s = socket(AF_UNIX, SOCK_STREAM)
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
    os.system('rm %s' % FILE_SOCKET)
    server = UnixStreamServer(FILE_SOCKET, MPlayerHandler)
    server.serve_forever()