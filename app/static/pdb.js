


function start(stream)
{
    var vlc     = null;
    vlc = document.getElementById('vlcPlayer');
    vlc.playlist.stop();
    vlc.playlist.items.clear();
    vlc.playlist.add(stream);
    vlc.playlist.play();
}
