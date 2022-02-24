'''
    File name: main.py
    Author: Guillermo Campos
    Date created: 2/23/2022
    Date last modified: 2/23/2022
    Python Version: 3.8
'''

__author__ = "Guillermo Campos"
__email__ = "camposguillermo@hotmail.com"
__status__ = "Production"

import os
from flask import Flask, session, request, redirect, render_template
from flask_session import Session
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import spotipy
import uuid
import pprint
import time
import json
import datetime

load_dotenv()

CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"] = str(os.getenv("SPOTIPY_CLIENT_ID"))
CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"] = str(os.getenv("SPOTIPY_CLIENT_SECRET"))
REDIRECT_URI = os.environ["SPOTIPY_REDIRECT_URI"] = str(os.getenv("SPOTIPY_REDIRECT_URI"))


application = Flask(__name__)
application.config["SECRET_KEY"] = os.urandom(64)
application.config["SESSION_TYPE"] = "filesystem"
application.config["SESSION_FILE_DIR"] = "./.flask_session/"
Session(application)

caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get("uuid")


class get_devices:
    def __init__(self, res):
        self.strJSON = json.dumps(
            res, ensure_ascii=False, sort_keys=True, indent=2, separators=(",", ": ")
        )
        self.active_device_id = None
        self.active_device_volume_percent = None
        self.active_device_name = None
        self.active_device_type = None

        for i in res["devices"]:
            self.device_id = i["id"]
            self.device_volume_percent = i["volume_percent"]
            self.device_name = i["name"]
            self.device_type = i["type"]

            if i["is_active"] == True:
                self.active_device_id = i["id"]
                self.active_device_volume_percent = i["volume_percent"]
                self.active_device_name = i["name"]
                self.active_device_type = i["type"]


class currently_playing:
    def __init__(self, res, playlists):
        track = res
        playlists = playlists
        if not track is None:
            self.timestamp = track["timestamp"]
            self.progress_ms = track["progress_ms"]
            self.duration_ms = track["item"]["duration_ms"]
            self.is_playing = track["is_playing"]
            self.resuming = track["actions"]["disallows"]
            self.artist = track["item"]["album"]["artists"][0]["name"]
            self.artist_URL = track["item"]["album"]["artists"][0]["external_urls"][
                "spotify"
            ]
            self.album_URL = track["item"]["album"]["external_urls"]["spotify"]
            self.song_URL = track["item"]["external_urls"]["spotify"]
            self.album = track["item"]["album"]["name"]
            self.song = track["item"]["name"]
            self.album_image_big = track["item"]["album"]["images"][0]["url"]
            self.album_image_medium = track["item"]["album"]["images"][1]["url"]
            self.album_image_small = track["item"]["album"]["images"][2]["url"]
            self.playlists = json.dumps(
                playlists,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                separators=(",", ": "),
            )


@application.route("/")
def index():
    if not session.get("uuid"):
        # Step 1. Visitor is unknown, give random ID
        session["uuid"] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect("/")

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<h2><a href="{auth_url}">Sign in</a></h2>'

    # Step 4. Signed in, display data
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return (
        f'<h2>Hi {spotify.me()["display_name"]}, '
        f'<small><a href="/sign_out">[sign out]<a/></small></h2>'
        f'<a href="/playlists">my playlists</a> | '
        f'<a href="/currently_playing2">currently playing</a> | '
        f'<a href="/current_user">me</a>'
    )


@application.route("/sign_out")
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect("/")


@application.route("/playlists")
def playlists():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect("/")

    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify.current_user_playlists()


@application.route("/currently_playing2")
def currently_playing2():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect("/")
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    track = spotify.current_user_playing_track()
    if not track is None:
        return track
    return "No track currently playing."


@application.route("/current_user")
def current_user():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect("/")
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify.current_user()


@application.route("/index.html")
def index_html():
    return render_template("index.html")


@application.route("/play")
def play():
    # Step 1. Visitor is unknown, give random ID
    if not session.get("uuid"):
        # Step 1. Visitor is unknown, give random ID
        session["uuid"] = str(uuid.uuid4())
    print("USER  ID " + session["uuid"])

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_cached_token(request.args.get("code"))
        return redirect("/play")

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        print("NOT AUTH")
        auth_url = auth_manager.get_authorize_url()
        #return f'<h2><a href="{auth_url}">Sign in</a></h2>'

        return render_template("authorize.html",auth_url=auth_url)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()

    if not track is None:
        print("si hay track")
        device = get_devices(sp.devices())
        print("Aqui", str(sp.current_user_playing_track()))

        playing = currently_playing(sp.current_user_playing_track(),
            sp.current_user_playlists(limit=50, offset=0))
        if hasattr(device, "active_device_volume_percent"):
            volume = device.active_device_volume_percent
        else:
            volume = 100
        print(playing.duration_ms)
        print(playing.progress_ms)
        remaining_s = int((playing.duration_ms - playing.progress_ms) / 1000)
        if playing.is_playing == False:
            remaining_s = 3600

        return render_template(
            "spotify.html",
            AlbumImgURL=playing.album_image_big,
            AlbumURL=playing.album_URL,
            AlbumName=playing.album,
            Artist=playing.artist,
            ArtistURL=playing.artist_URL,
            Song=playing.song,
            SongURL=playing.song_URL,
            Timestamp=playing.timestamp,
            Duration=int(playing.duration_ms / 1000),
            Progress=int(playing.progress_ms / 1000),
            IsPlaying=playing.is_playing,
            Resuming=playing.resuming,
            Volume=volume,
            Refresh=remaining_s,
            JSONDevices=device.strJSON,
            JSONPlaylists=playing.playlists,
        )
    else:
        return render_template("noplaying.html")


@application.route("/next_track")
def next_track():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    if not track is None:
        device = get_devices(sp.devices())
        print(device.device_id)
        try:
            sp.next_track(device_id=False)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))

            #return str(e.args[2])
        #except:
         #   return "Spotify Premium required"

        return redirect("/play")
    return render_template("noplaying.html")


@application.route('/previous_track')
def previous_track():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    if not track is None:
        device = get_devices(sp.devices())
        print(device.device_id)
        try:
            sp.previous_track(device_id=False)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        return redirect("/play")
    return render_template("noplaying.html")


@application.route('/pause')
def pause():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    if not track is None:
        if track['is_playing'] == True:
            try:
                sp.pause_playback(device_id=False)
            except Exception as e:
                return render_template("error.html", error=str(e.args[2]))



        else:
            try:
                sp.start_playback(device_id=False)
            except Exception as e:
                return render_template("error.html", error=str(e.args[2]))
        return redirect('/play')
    return "No track currently playing."

@application.route('/volume_up')
def volume_up():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    device = get_devices(sp.devices())

    if not track is None:
        CurrentVolume = device.active_device_volume_percent + 10
        try:
            sp.volume(CurrentVolume, device.active_device_id)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        print(CurrentVolume)
        return redirect('/play')
    else:
        return "No track is currently playing"


@application.route('/volume_down')
def volume_down():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    device = get_devices(sp.devices())

    if not track is None:
        CurrentVolume = device.active_device_volume_percent - 10
        try:
            sp.volume(CurrentVolume, device.active_device_id)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))


        print(CurrentVolume)
        return redirect('/play')
    else:
        return "No track is currently playing"


@application.route('/set_volume')
def set_volume():
    volume = int(request.args.get('volume'))
    print("setting volume: " + str(volume))
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    device = get_devices(sp.devices())

    if not track is None:
        print("setting volume: " + str(volume) + " on device: " + str(device.active_device_name))
        try:
            sp.volume(volume, device.active_device_id)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        time.sleep(1)
        return redirect('/play')
    else:
        return redirect('/play')


@application.route('/seek_track')
def seek_track():
    position_ms = int(request.args.get('position'))
    position_ms = position_ms * 1000
    print(position_ms)
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()
    device = get_devices(sp.devices())

    if not track is None:

        try:
            sp.seek_track(position_ms, device.active_device_id)

        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        time.sleep(1)
        return redirect('/play')
    else:
        return redirect('/play')






@application.route('/transfer_playback')
def transfer_playback():
    device = request.args.get('device')
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()

    if not track is None:
        try:
            sp.transfer_playback(device, force_play=True)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        return redirect('/play')
    else:
        return redirect('/play')




@application.route('/set_playlist')
def set_playlist():
    playlistURI = request.args.get('playlistURI')
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()

    if not track is None:
        try:
            sp.start_playback(device_id=None, context_uri=playlistURI, uris=None, offset=None, position_ms=None)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        return redirect('/play')
    else:
        return redirect('/play')


@application.route('/set_playback')
def set_playback():
    URI = request.args.get('URI')
    URI = URI.split()
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
        cache_handler=cache_handler,
        show_dialog=True,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track = sp.current_user_playing_track()

    if not track is None:
        try:
            sp.start_playback(device_id=None, context_uri=None, uris=URI, offset=None, position_ms=None)
        except Exception as e:
            return render_template("error.html", error=str(e.args[2]))
        return redirect('/play')
    else:
        return redirect('/play')




class searchthis():
    def __init__(self, arg):
        cache_handler = spotipy.cache_handler.CacheFileHandler(
            cache_path=session_cache_path()
        )
        auth_manager = spotipy.oauth2.SpotifyOAuth(
            scope="user-read-currently-playing playlist-modify-private,user-read-playback-state,user-modify-playback-state",
            cache_handler=cache_handler,
            show_dialog=True,
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        track = sp.current_user_playing_track()

        self.numberoftracks = 0
        #print(currentDevice('id'))
        #print("SP : " + str(sp))
        if not track is None:
            try:
                result = sp.search(arg, limit=12, offset=0, type='track,album,playlist', market=None)
            except Exception as e:
                return render_template("error.html", error=str(e.args[2]))
            else:
                searches=0
                itemnumber = 0
                print("EL RESULTADO" + str(result))
                self.numberoftracks = numberoftracks = len(result['tracks']['items'])
                self.numberofalbums = numberofalbums = len(result['albums']['items'])
                self.numberofplaylists = numberofplaylists= len(result['playlists']['items'])
                self.searches =searches = numberoftracks + numberofalbums + numberofplaylists


                id=[]
                search_type=[]
                track_name=[]
                uri=[]
                track_URL=[]
                artist_name=[]
                artist_URL=[]
                album_name=[]
                album_release_date=[]
                album_cover_image=[]
                album_URL=[]
                playlist_name=[]
                playlist_description=[]




                if numberoftracks > 0:
                    for i in result['tracks']['items']:
                        id.append(itemnumber)
                        search_type.append(i['type'])
                        track_name.append(i['name'])
                        uri.append(i['uri'])
                        track_URL.append(i['external_urls']['spotify'])
                        artist_name.append(i['artists'][0]['name'])
                        artist_URL.append(i['artists'][0]['external_urls']['spotify'])
                        album_name.append(i['album']['name'])
                        album_release_date.append(i['album']['release_date'])
                        album_cover_image.append(i['album']['images'][0]['url'])
                        album_URL.append(i['album']['external_urls']['spotify'])
                        playlist_name.append("")
                        playlist_description.append("")
                        itemnumber = itemnumber + 1

                else:
                    print('No track results')

                if numberofalbums > 0:
                    for i in result['albums']['items']:
                        id.append(itemnumber)
                        search_type.append(i['type'])
                        track_name.append("")
                        uri.append(i['uri'])
                        track_URL.append("")
                        artist_name.append(i['artists'][0]['name'])
                        artist_URL.append(i['artists'][0]['external_urls']['spotify'])
                        album_name.append(i['name'])
                        album_release_date.append(i['release_date'])
                        album_cover_image.append(i['images'][0]['url'])
                        album_URL.append(i['external_urls']['spotify'])
                        playlist_name.append("")
                        playlist_description.append("")
                        itemnumber = itemnumber + 1


                else:
                        print('No album results')

                if numberofplaylists > 0:
                    for i in result['playlists']['items']:
                        id.append(itemnumber)
                        search_type.append(i['type'])
                        track_name.append("")
                        uri.append(i['uri'])
                        track_URL.append("")
                        artist_name.append("")
                        artist_URL.append("")
                        album_name.append("")
                        album_release_date.append("")
                        album_cover_image.append(i['images'][0]['url'])
                        album_URL.append(i['external_urls']['spotify'])
                        playlist_name.append(i['name'])
                        playlist_description.append(i['description'])
                        itemnumber = itemnumber + 1


                else:
                        print('No Playlist results')







                if itemnumber > 0:
                    JSONList = []
                    JSONListTrack = []
                    SearchJSONAlbum = []
                    SearchJSONPlaylist = []

                    for x in id:
                        JSONList.append({"id" : x, "search_type" : search_type[x], "track_name": track_name[x], "uri": uri[x], "track_URL": track_URL[x], "artist_name": artist_name[x], "artist_URL": artist_URL[x], "album_name": album_name[x], "album_release_date": album_release_date[x], "album_cover_image": album_cover_image[x], "album_URL": album_URL[x], "playlist_name": playlist_name[x], "playlist_description": playlist_description[x] })

                    JSONListTrack = [x for x in JSONList if x['search_type'] == 'track']
                    JSONListAlbum = [x for x in JSONList if x['search_type'] == 'album']
                    JSONListPlaylist = [x for x in JSONList if x['search_type'] == 'playlist']

                    self.SearchJSON = json.dumps(JSONList)
                    self.Track = json.dumps(JSONListTrack)
                    self.Album = json.dumps(JSONListAlbum)
                    self.Playlist = json.dumps(JSONListPlaylist)


                else:
                    self.SearchJSON = ""









@application.route('/search')
def search():
    search = request.args.get('search')
    if search is not None:
        JSONSearch = searchthis(search)
        print(JSONSearch)
        #print("TRACKs("+str(JSONSearch.numberoftracks) + ") "  + JSONSearch.Track)
        #print("Album("+str(JSONSearch.numberofalbums) + ") " + JSONSearch.Album)
        #print("Playlist("+str(JSONSearch.numberofplaylists) + ") " +  JSONSearch.Playlist)



        return render_template("search.html", NumberOfTracks = JSONSearch.numberoftracks, JSONTrack = JSONSearch.Track, NumberOfAlbums = JSONSearch.numberofalbums, JSONAlbum = JSONSearch.Album, NumberOfPlaylists = JSONSearch.numberofplaylists, JSONPlaylist = JSONSearch.Playlist, searchresults=searchthis(search).searches, searchstring=search)
    else:
        return "No search parameters"





if __name__ == "__main__":
    application.run(
        threaded=True,
        port=8080
    )
