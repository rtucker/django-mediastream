// Props to: http://stackoverflow.com/a/1987545/205400
$.fn.stars = function() {
    return $(this).each(function() {
        // Get the value
        var val = parseFloat($(this).html());
        // Make sure that the value is in 0 - 5 range, multiply to get width
        var size = Math.max(0, (Math.min(5, val))) * 16;
        // Create stars holder
        var $span = $('<span />').width(size);
        // Replace the numerical value with stars
        $(this).html($span);
    });
}

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

var handle_groove = function(event){
    var groove_box = this;
    var data = false;
    if($(this).attr('checked')) {
        $(this).siblings().attr('checked', false);
        var data = {
            assetpk:  jplaylist.playlist[jplaylist.current].assetPk,
            groove: $(this).val()
        };
    } else if($(this).siblings(':checked').length < 1) {
        var data = {
            assetpk:  jplaylist.playlist[jplaylist.current].assetPk,
            groove: 'pokerface'
        };
    }
    if(data) {
        $.ajaxQueue({
            type: 'POST',
            url: player_rating_url,
            data: data,
            dataType: 'json',
            success: function(reply){
                // server sends: response
                if(reply.response){
                    $("#playeralerts").text(reply.response);
                    $("#playeralerts").slideDown(200);
                    $("#playeralerts").delay(20000);
                    $("#playeralerts").fadeOut(600);
                }
            }
        });
    }
}

var handle_rating = function(event){
    var offset = $(this).offset();
    var star_span = this;
    var x = Math.floor(event.pageX - offset.left);
    var rating = Math.floor(x * 5 / $(this).width());
    var data = {
        asset:  jplaylist.playlist[jplaylist.current].pk,
        rating: rating + 1
    };
    $.ajaxQueue({
        type: 'POST',
        url: player_rating_url,
        data: data,
        dataType: 'json',
        success: function(reply){
            // server sends: response, rating
            if(reply.response){
                $("#playeralerts").text(reply.response);
                $("#playeralerts").slideDown(200);
                $("#playeralerts").delay(20000);
                $("#playeralerts").fadeOut(600);
            }
            $('a.jp-playlist-current > span.jp-rating').html("average rating: " + reply.avg_rating + " (ratings: " + reply.total_ratings + ")").show();
            $(star_span).html(reply.rating);
            $(star_span).stars();
        }
    });
}

var reticulate_splines = function(){
    if(jplaylist.playlist[jplaylist.current].poster) {
        $("div#albumart img").attr("src", jplaylist.playlist[jplaylist.current].poster).show('slow');
    } else {
        $("div#albumart img").hide('slow');
    }

    if($('li.jp-playlist-current').has('div.starbox').length < 1) {
        $('li.jp-playlist-current > div').append('<div class="starbox"></div>');
        $('div.starbox').append('<span class="stars">0</span>');
        $('div.starbox > span.stars').stars();
        $('div.starbox > span.stars').click(handle_rating);
        $('div.starbox').append('<span class="groove"></span>');
        $('span.groove').append('<p>This set: <input class="groovebox" value="nope" type="checkbox">not doing it for me</input><input class="groovebox" value="awyeah" type="checkbox">grooving fiercely</input></p>');
        $('input.groovebox').click(handle_groove);
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
            if(reply.response){
                $("#playeralerts").text(reply.response);
                $("#playeralerts").slideDown(200);
                $("#playeralerts").delay(20000);
                $("#playeralerts").fadeOut(600);
            }
            if(reply.artistName && reply.trackName) {
                $('title').text(reply.trackName + " by " + reply.artistName + " | mediastream");
            } else {
                $('title').text('mediastream cloud music');
            }
            if(reply.artistBio){
                $("#artistbio").show();
                $("#artistbio").html(reply.artistBio);
            } else {
                $("#artistbio").hide();
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
