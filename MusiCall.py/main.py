import secrets
import threading
import webbrowser
from datetime import datetime

import spotipy
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

# Use a strong, randomly generated key for session management
app.secret_key = secrets.token_hex(16)


class SpotifyClient:
    def __init__(self):
        self.sp = None
        self.token = None
        self.token_info = None
        self.sp_oauth = SpotifyOAuth(
            client_id="f9a585407c8c460fbbc4e0068cb5b3c5",  # Replace with your Spotify client ID
            client_secret="fac43f882c064e918d2852f782c8049d",  # Replace with your Spotify client secret
            redirect_uri="http://127.0.0.1:5000/callback",  # Redirect URI
            scope="user-library-read user-read-playback-state user-read-currently-playing user-read-recently-played user-modify-playback-state",  # Added play permissions
        )

    def authenticate(self):
        auth_url = self.sp_oauth.get_authorize_url()
        webbrowser.open(auth_url)  # Opens the URL in the default web browser
        return auth_url

    def set_token(self, code):
        try:
            self.token_info = self.sp_oauth.get_access_token(code)
            self.token = self.token_info["access_token"]
            self.sp = spotipy.Spotify(auth=self.token)
            return True
        except Exception as e:
            print(f"Error during token exchange: {e}")
            return False

    def get_current_playback(self):
        if self.sp:
            current_playback = self.sp.current_playback()
            if current_playback and current_playback["is_playing"]:
                song = current_playback["item"]
                album = song["album"]
                return {
                    "song_name": song["name"],
                    "artist": song["artists"][0]["name"],
                    "album_name": album["name"],
                    "album_cover_url": album["images"][0]["url"],  # Album cover URL
                    "uri": song["uri"],  # Song URI for playback control
                    "spotify_url": song["external_urls"][
                        "spotify"
                    ],  # Link to song on Spotify
                }
        return None

    def get_recent_tracks(self):
        if self.sp:
            recent_tracks = self.sp.current_user_recently_played(limit=10)
            tracks = []
            for item in recent_tracks["items"]:
                song_name = item["track"]["name"]
                artist = item["track"]["artists"][0]["name"]
                album_name = item["track"]["album"]["name"]
                album_image = item["track"]["album"]["images"][0][
                    "url"
                ]  # Get album cover image
                played_at = item["played_at"]
                tracks.append(
                    {
                        "song_name": song_name,
                        "artist": artist,
                        "album_name": album_name,
                        "album_image": album_image,
                        "played_at": played_at,
                        "uri": item["track"]["uri"],  # URI needed for playback
                    }
                )
            return tracks
        return []

    def play_track(self, uri):
        try:
            if self.sp:
                self.sp.start_playback(uris=[uri])
                return True
        except Exception as e:
            print(f"Playback error: {e}")
            return False


spotify_client = SpotifyClient()


@app.route("/")
def home():
    if "user_id" in session:
        return render_template("index.html")
    return redirect(url_for("login"))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/authenticate")
def authenticate():
    auth_url = spotify_client.authenticate()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if spotify_client.set_token(code):
        session["user_id"] = spotify_client.token_info["access_token"]
        return redirect(url_for("home"))
    return "Authentication failed."


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))


@app.route("/current_song")
def current_song():
    if "user_id" in session:
        song = spotify_client.get_current_playback()
        return render_template("current_song.html", song=song)
    return redirect(url_for("login"))


@app.route("/recent_tracks")
def recent_tracks():
    if "user_id" in session:
        tracks = spotify_client.get_recent_tracks()
        for track in tracks:
            track["played_at"] = datetime.strptime(
                track["played_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).strftime("%Y-%m-%d %H:%M:%S")
        return render_template("recent_tracks.html", tracks=tracks)
    return redirect(url_for("login"))


@app.route("/play_track", methods=["POST"])
def play_track():
    if "user_id" in session:
        uri = request.form.get("uri")
        if uri and spotify_client.play_track(uri):
            return redirect(url_for("recent_tracks"))
    return redirect(url_for("login"))


@app.route("/play/<uri>")
def play(uri):
    if "user_id" in session:
        spotify_client.play_track(uri)
        return redirect(url_for("current_song"))
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
