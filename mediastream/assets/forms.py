from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

class UploadFileForm(forms.Form):
    file = forms.FileField(required=False, help_text="Each file must be an audio file, or a ZIP containing audio files.")

class ImportFileForm(forms.Form):
    path = forms.FilePathField(required=False, path='/tmp', recursive=True, help_text="A single file to process, from /tmp", match="\.(zip|mp4|m4a|mp3|flac|ogg)")
