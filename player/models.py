import datetime
from django.db.models import Model, IntegerField, CharField, TextField, DateTimeField, EmailField, BooleanField, \
    FilePathField, ForeignKey, ManyToManyField
from django.contrib.auth.models import User

class Song(Model):
    title = CharField(max_length=120)
    album = CharField(max_length=120, blank=True)
    artist = CharField(max_length=120, blank=True)
    duration = IntegerField(blank=True, help_text='duration of the song in seconds')
    file_path = TextField(max_length=120, blank=True)
    pub_date = DateTimeField(default=datetime.datetime.now())
    is_playing = BooleanField(default=False)
    votes = ManyToManyField(User, blank=True)
    
    def __unicode__(self):
        return '%s - %s - %s' % (self.title, self.album, self.artist)
    
