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
    """A simple wrapper around the mplayer music player.
    
    Use loadfile() to start playing a file
    
    """
    def __init__(self, mplayer_path='mplayer'):
        def read_mplayer_pipe(fd, q):
            while True:
                output = select([fd], [], [])[0][0]
                q.put(output.readline())
        
        cmd = [mplayer_path, '-slave', '-quiet', '-idle']
        self._mp = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=IGNORE)
        self._q = Queue()
        self._p = Process(target=read_mplayer_pipe, args=(self._mp.stdout, self._q))
        self._p.start()
        self._write = self._mp.stdin.write
        self._read = self._q.get
    
    def __del__(self):
        self.quit()
    
    def _flush(self):
        """Flush the communication Queue"""
        while not self._q.empty():
            self._q.get()

    def get_path(self):
        """Returns the path of the file that is currenly loaded.
        
        It return an empty string if no file is loaded
        """
        self._flush()
        self._write('pausing_keep_force get_property path\n')
        result = self._read().partition('=')[2].strip()
        return '' if result == '(null)' else result
    
    def get_filename(self):
        """Returns the name of the file that is currenly loaded.
        
        It return an empty string if no file is loaded
        """
        if self.is_file_loaded():
            return ''
        else:
            self._flush()
            self._write('pausing_keep_force get_property filename\n')
            return  self._read().partition('=')[2].rstrip()

    def is_file_loaded(self):
        """Return True if mplayer has loaded a file"""
        return self.get_path() != ''

    def loadfile(self, path):
        """load the the file 'path' and start playing it."""
        self._flush()
        self._write('pausing_keep_force loadfile %s\n' % (path))
    
    def is_paused(self):
        """Return True if mplayer has loaded a file and is playing this file."""
        self._flush()
        self._write('pausing_keep_force get_property pause\n')
        a = self._read().split('=')[1].strip()
        logging.debug('is_paused: %s|' % a)
        return self.is_file_loaded() and a == 'yes'
    
    def play(self):
        """if there is a song loaded it will start playing"""
        if self.is_file_loaded() and self.is_paused():
            self._flush()
            self._write('pause\n')
    
    def pause(self):
        """if there is a song loaded it will be paused"""
        if self.is_file_loaded() and not self.is_paused():
            self._flush()
            self._write('pause\n')

    def get_length(self):
        """Returns the length of the loaded song in seconds as int."""
        if self.get_path():
            self._flush()
            self._write('pausing_keep_force get_property length\n')
            return  int(float(self._read().partition('=')[2]))
        else:
            return -1
    
    def get_position(self):
        """Returns the position in the song as int between 0 and 100."""
        if self.is_file_loaded():
            self._flush()
            self._write('pausing_keep_force get_property time_pos\n')
            return  int(float(self._read().partition('=')[2]))
        else:
            return -1
        
    def quit(self):
        """Quit the mplayer supprocess.
        
        After this command MPlayerWrapper won't work correctly.
        """
        if self._mp.poll() is None:
            self._mp.communicate('quit\n')
    
    def stop(self):
        """Stop playing the current song and remove it"""
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
            rfile = request.makefile('r', self.READ_BUFFER_SIZE)
            wfile = request.makefile('w', self.WRITE_BUFFER_SIZE)
            self._dispatch(rfile.readline().strip(), rfile, wfile)
        except Exception, msg:
            logging.debug('Exception %s' % msg)
        finally:
            if not wfile.closed:
                wfile.flush()
            rfile.close()
            wfile.close()
    
    def _dispatch(self, s, rfile, wfile):
        logging.debug('_dispatch: %s' % s)
        if s == 'play':
            self._mp.play()
        elif s == 'pause':
            self._mp.pause()
        elif s == 'skip':
            self._dispatch('stop')
            self._dispatch('start')
        elif s == 'start':
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
            if self._mp.is_file_loaded():
                wfile.write(','.join((
                    str(self._mp.is_file_loaded()),
                    str(self._mp.is_paused()),
                    str(self._mp.get_length()),
                    str(self._mp.get_position()),
                )))
            else:
                wfile.write('False,False,-1,-1')
    
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
                    if not self._mp.is_file_loaded():
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
    READ_BUFFER_SIZE = -1
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
        s.close()
        return result
    
    @classmethod
    def status(cls):
        s = cls.get_socket()
        s.send('status\n')
        r = select([s.fileno()], [], [], )[0][0]
        rfile = s.makefile('r', cls.READ_BUFFER_SIZE)
        line = rfile.readline()
        s.close()
        rfile.close()
        return line


def run_server():
    os.system('rm %s' % FILE_SOCKET)
    server = MPlayerServer(FILE_SOCKET)
    server.run()