from django.forms import Form, FileField, CharField

class UploadMp3FileForm(Form):
    title = CharField(max_length=120)
    album = CharField(max_length=120, blank=True)
    artist = CharField(max_length=120, blank=True)
    mp3_file = FileField()


class AddYoutubeVideoForm(Form):
    title = CharField(max_length=120)
    album = CharField(max_length=120, blank=True)
    artist = CharField(max_length=120, blank=True)
    video_link = URLField()


class AddDaapFileForm(Form):
    daap_path = CharField()