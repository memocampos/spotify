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

