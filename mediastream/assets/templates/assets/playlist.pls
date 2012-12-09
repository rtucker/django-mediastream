{% load url from future %}
[playlist]
{% for track in object.streamable_tracks %}
File{{ forloop.counter }}={{ baseurl }}{% url 'stream-track' pk=track.pk %}
Title{{ forloop.counter }}={{ track.artist }} - {{ track.name }}
Length{{ forloop.counter }}={{ track.length }}
{% if forloop.last %}
NumberOfEntries={{ forloop.counter }}
Version=2
{% endif %}
{% endfor %}
