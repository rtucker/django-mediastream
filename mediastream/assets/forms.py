from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

class UploadFileForm(forms.Form):
    file = forms.FileField()
