var send_event = function(event){
    if(jplaylist.current > 0){
        jplaylist.remove(0);
    }
    $.ajaxQueue({
        type: 'POST',
        url: player_event_url,
        data: function(event){
                var data = {
                    user:           user_id,
                    eventType:      event.type,
                    currentTime:    event.jPlayer.status.currentTime,
                    src:            event.jPlayer.status.src,
                    seekPercent:    event.jPlayer.status.seekPercent,
                    bufferPercent:  event.jPlayer.status.currentPercentRelative,
                    mediaPk:        event.jPlayer.status.media.pk,
                    playlistLength: $(".jp-playlist > ul > li").length
                };
                if (event.type == 'jPlayer_error'){
                    data.errorType = event.jPlayer.error.type;
                    data.errorMsg = event.jPlayer.error.message;
                }
                return data;
            }(event),
        dataType: "json",
        success: function(reply){
            $("#playeralerts").text(reply.response);
            $.each(reply.tracks, function(index, value) {
                jplaylist.add(value);
            });
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
