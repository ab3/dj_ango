from django.forms import Form, FileField, CharField, URLField

class UploadMp3FileForm(Form):
    title = CharField(max_length=120)
    album = CharField(max_length=120, required=False)
    artist = CharField(max_length=120, required=False)
    mp3_file = FileField()


class AddYoutubeVideoForm(Form):
    title = CharField(max_length=120)
    album = CharField(max_length=120, required=False)
    artist = CharField(max_length=120, required=False)
    video_link = URLField(verify_exists=False)


class AddDaapFileForm(Form):
    daap_path = CharField()