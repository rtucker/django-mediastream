var send_event = function(event){
    if(jplaylist.current > 0){
        jplaylist.remove(0);
    }
    var data = {
        eventType:      event.type,
        currentTime:    event.jPlayer.status.currentTime,
        src:            event.jPlayer.status.src,
        seekPercent:    event.jPlayer.status.seekPercent,
        bufferPercent:  event.jPlayer.status.currentPercentRelative,
        mediaPk:        event.jPlayer.status.media.pk
    }
    if (event.type == 'jPlayer_error'){
        data.errorType = event.jPlayer.error.type;
        data.errorMsg  = event.jPlayer.error.message;
    }
    bug_server(data);
}

var reticulate_splines = function(){
    if(jplaylist.playlist[jplaylist.current].poster) {
        $("div#albumart img").attr("src", jplaylist.playlist[jplaylist.current].poster).show('slow');
    } else {
        $("div#albumart img").hide('slow');
    }
}

var bug_server = function(data){
    $.ajaxQueue({
        type: 'POST',
        url: player_event_url,
        data: function(data){
            data.user           = user_id;
            data.playlistLength = $(jplaylist.playlist).length;
            data.caboosePk      = $(jplaylist.playlist).last()[0].pk;
            return data;
        }(data),
        dataType: "json",
        success: function(reply){
            $.each(reply.tracks, function(index, value) {
                jplaylist.add(value);
            });
            $("#playeralerts").text(reply.response);
            if(reply.artistName && reply.trackName) {
                $('title').text(reply.trackName + " by " + reply.artistName + " | mediastream");
            } else {
                $('title').text('mediastream cloud music');
            }
            reticulate_splines();
        }
    });
};

$(document).ready(function(){
  $("#jquery_jplayer_1").bind($.jPlayer.event.ended,      send_event);
  $("#jquery_jplayer_1").bind($.jPlayer.event.error,      send_event);
  $("#jquery_jplayer_1").bind($.jPlayer.event.canplaythrough, send_event);
  $("#jquery_jplayer_1").bind($.jPlayer.event.pause,      send_event);
  $("#jquery_jplayer_1").bind($.jPlayer.event.play,       send_event);
  $("#jquery_jplayer_1").bind($.jPlayer.event.waiting,    send_event);
});
