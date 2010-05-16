#
# More info about mplayer http://www.mplayerhq.hu/DOCS/tech/slave.txt
import os
import sys
import logging
from select import select, error as SelectError
from socket import socket, AF_UNIX, SOCK_STREAM, error as SocketError
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


class MPlayerWrapper(object):
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
        result = self._read().partition('=')[2].strip()
        return '' if result == '(null)' else result
    
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


class MPlayerServer(object):
    REQUEST_QUEUE_SIZE = 5
    READ_BUFFER_SIZE = -1
    WRITE_BUFFER_SIZE = 0
    
    def __init__(self, file_socket):
        self._mp = MPlayerWrapper()
        self._socket = socket(AF_UNIX, SOCK_STREAM)
        self._file_socket = file_socket
        self._active = False
    
    def _handle_request(self):
        try:
            request, client_address = self._socket.accept()
        except SocketError, msg:
            logging.debug('SocketError %s' % msg)
            return
        
        try:
            rfile = request.makefile('rb', self.READ_BUFFER_SIZE)
            wfile = request.makefile('wb', self.WRITE_BUFFER_SIZE)
            logging.debug('Dispatch')
            self._dispatch(rfile.readline().strip())
        except:
            pass
        finally:
            rfile.close()
            wfile.close()
    
    def _dispatch(self, s):
        if s == 'play':
            logging.debug('play')
            self._mp.play()
        elif s == 'pause':
            logging.debug('pause')
            self._mp.pause()
        elif s == 'skip':
            logging.debug('skip')
            #self._mp.stop()
            self._dispatch('stop')
            self._dispatch('start')
        elif s == 'start':
            logging.debug('start')
            self._active = True
        elif s == 'stop':
            logging.debug('stop')
            try:
                current_song = Song.objects.filter(is_playing=True)[0]
            except IndexError:
                pass
            else:
                os.remove(current_song.file_path)
                current_song.delete()
            self._active = False
            
            self._mp.stop()
        elif s == 'status':
            logging.debug('status')
            return str(self._mp.status())        
    
    def fileno(self):
        return self._socket.fileno()
    
    def run(self, poll_interval=0.5):
        self._socket.bind(self._file_socket)     # bind socket
        self._socket.listen(self.REQUEST_QUEUE_SIZE)  # activate socket
        while True:
            # Listen to socket
            try:
                r, w, e = select([self], [], [], poll_interval)
                if r:
                    logging.debug('handle request')
                    self._handle_request()
            except SelectError, msg:
                logging.debug('run except %s' % msg)
                self._socket.close()
                self._mp.quit()
                return
            else:
                if self._active:
                    if not self._mp.get_path():
                        try:
                            current_song = Song.objects.filter(is_playing=True)[0]
                        except IndexError:
                            pass
                        else:
                            os.remove(current_song.file_path)
                            current_song.delete()
                        
                        try:
                            next_song = next_song = Song.objects.filter(is_playing=False) \
                                .annotate(nr_votes=Count('votes')).order_by('-nr_votes')[0]
                        except IndexError:
                            pass
                        else:
                            next_song.is_playing = True
                            next_song.save()
                            self._mp.loadfile(next_song.file_path)
                
                        next_song = None


class MPlayerControl(object):
    @classmethod
    def get_socket(cls):
        logging.debug('client')
        s = None
        try:
            s = socket(AF_UNIX, SOCK_STREAM)
        except SocketError, msg:
            logging.debug(msg)
            sys.exit(1)
        try:
            s.connect(FILE_SOCKET)
        except SocketError, msg:
            s.close()
            logging.debug(msg)
            #sys.exit(1)
        return s
    
    @classmethod
    def play(cls):
        s = cls.get_socket()
        s.send('play\n')
        s.close()
    
    @classmethod
    def pause(cls):
        s = cls.get_socket()
        s.send('pause\n')
        s.close()
    
    @classmethod
    def skip(cls):
        s = cls.get_socket()
        s.send('skip\n')
        s.close()
    
    @classmethod
    def start(cls):
        s = cls.get_socket()
        s.send('start\n')
        s.close()
    
    @classmethod
    def stop(cls):
        s = cls.get_socket()
        s.send('stop\n')
        result = select([s.fileno()], [], [], )[0][0]
        s.close()
        return result
    
    @classmethod
    def status(cls):
        s = cls.get_socket()
        s.send('status\n')
        result = select([s.fileno()], [], [], )[0][0]
        result2 = s.recv(4096)
        s.close()
        return result2


def run_server():
    os.system('rm %s' % FILE_SOCKET)
    server = MPlayerServer(FILE_SOCKET)
    server.run()