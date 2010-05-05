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