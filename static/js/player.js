$(document).ready(function() {
    updater.poll();
})

function sec_to_hms(seconds) {
    var h = Math.floor(seconds/3600); 
    var m = Math.floor(seconds/60) - (h*60); 
    var s = seconds - (h*3600)-(m*60); 
    
    if (h > 0 ) {
        return ""+h+":"+m+":"+s;
    } else
        return ""+m+":"+s;
}

var updater = {
    defaultSleepTime: 2000,
    errorSleepTime: 5000,
    
    poll: function() {
        $.ajax({url:"/status/", dataType:"json", success: updater.onSuccess, error: updater.onError});
    },
    
    onSuccess: function(response) {
        // Update Player Controls
        var song_info = $("#song_info");
        song_info.empty();
        song_info.append(response.current_song.title);-
        if (response.current_song.album != null)
            song_info.append(' - '+response.current_song.album);
            
        // Update playlist
        var playlist = $("#playlist_songs");
        playlist.empty();
        for (var song in response.songs) {
            var row_class;
            var vote_class = '"vote_open"';
            if (song % 2 == 0) {
                row_class = '<tr class="odd">';
            } else {
                row_class = '<tr class="even">';
            }
            for (var vote in response.votes) {
                if (response.songs[song].pk == response.votes[vote].pk) {
                    vote_class = '"vote_passed"';
                    break;
                }
            }
            playlist.append(
                row_class+
                '<td class="playlist_votes"><a class='+vote_class+
                ' href="/vote/'+response.songs[song].pk+
                '">&nbsp;</a>'+response.songs[song].nr_votes+
                '</td><td>'+response.songs[song].title+
                '</td><td class="lean_right">'+sec_to_hms(response.songs[song].duration)+
                '</td><td>'+response.songs[song].artist+
                '</td><td>'+response.songs[song].album+
                '</td></tr>\n'
            );
        }
        window.setTimeout(updater.poll, updater.defaultSleepTime);
    },
    
    onError: function(response) {
        console.log('Poll Error')
        window.setTimeout(updater.poll, updater.errorSleepTime);
    },
}