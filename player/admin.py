from django.contrib.admin import ModelAdmin, StackedInline, site
from models import Song

class SongAdmin(ModelAdmin):
    model = Song
    list_display = ('title', 'duration', 'artist', 'album')
    search_fields = ['title', 'duration', 'artist']


site.register(Song, SongAdmin)