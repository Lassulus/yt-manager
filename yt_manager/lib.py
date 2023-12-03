import os
import sys
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL

# we skip any track that contains any of these keywords from the channel
restricted_keywords = [ "live", "interview"]

class Track():
    def __init__(self, youtube_id: str, channel_id: str, track_title: str, track_artist: str, track_album: str or None, track_duration: int):
        self.youtube_id = youtube_id
        self.channel_id = channel_id
        self.title = track_title.replace("/", "_")
        self.artist = track_artist.replace("/", "_")
        self.album = track_album.replace("/", "_") if track_album else None
        self.duration = track_duration
        self.path = Path(f'.ytm/{channel_id}/{youtube_id}.ogg')

    def __str__(self):
        return f"{self.artist} - {self.title} https://youtu.be/{self.youtube_id} from https://www.youtube.com/channel/{self.channel_id}"

ytdl_fetcher_options = {
    'extract_flat': True,
}
def get_downloader_options(output_dir: Path = Path("/tmp/test")) -> dict:
    return {
        'format': 'bestaudio/best',
        'outtmpl': f'{str(output_dir)}/track.%(ext)s',
        'restrictfilenames': 'True',
        'postprocessors': [
            {  # Extract audio using ffmpeg
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'vorbis',
            },
            {  # Add metadata}
                'key': 'FFmpegMetadata',
            },
        ],
    }

# get all tracks from a channel via youtube music
def get_channel_releases(channel_id: str) -> dict[str, Track]:
    all_tracks = dict()
    ytmusic = YTMusic()
    try:
        albums = ytmusic.get_artist_albums(channel_id, "")
    except:
        albums = []
    for album in albums:
        tracks = ytmusic.get_album(album['browseId'])["tracks"]
        for track in tracks:
            if any(keyword in track['title'].lower() for keyword in restricted_keywords):
                continue
            all_tracks[track["videoId"]] = Track(
                track["videoId"],
                channel_id,
                track["title"],
                track["artists"][0]["name"],
                track["album"],
                track["duration_seconds"],
            )
    return all_tracks

def get_ydl_info(url: str) -> dict:
    ydl = YoutubeDL({"extract_flat": True})
    return ydl.extract_info(url, download=False)

# get all tracks from a youtube link
def get_tracks_via_ytdl(url: str) -> dict[str, Track]:
    all_tracks = dict()

    channel_info = get_ydl_info(url)
    if channel_info is not None and 'entries' in channel_info:
        for track in channel_info['entries']:
            if any(keyword in track['title'].lower() for keyword in restricted_keywords):
                continue
            # we skip any track that is not between 60 and 1000 seconds
            if "duration" not in track or track["duration"] > 1000 or track["duration"] < 60:
                continue

            # get the channel id from the track if it exists, otherwise use the channel id from the channel info
            # we want to prefer the channel id from the track because it is accurate in playlists
            channel_id = track["channel_id"]
            if channel_id is None:
                channel_id = channel_info["channel_id"]

            artist = track["artist"].split(",")[0] if "artist" in track else None
            if artist is None:
                artist = track["uploader"]
            if artist is None:
                artist = channel_info["channel"]

            print(artist)

            all_tracks[track["id"]] = Track(
                track["id"],
                channel_id,
                track["title"],
                artist,
                track.get("album", None),
                int(track["duration"]),
            )
    else:
        print("Error getting channel info with yt-dlp")
    return all_tracks


def get_single_track(url: str) -> Track:
    track_info = get_ydl_info(url)
    return Track(
        track_info["id"],
        track_info["channel_id"],
        track_info["title"],
        track_info["uploader"],
        track_info["album"],
        int(track_info["duration"]),
    )

# get all tracks from a channels video catalog
def get_channel_tracks(channel_id: str) -> dict[str, Track]:
    tracks = get_tracks_via_ytdl(f'https://www.youtube.com/channel/{channel_id}/videos')
    return tracks

# download a single track as ogg
def download_track(toplevel: Path, track: Track) -> Track:
    channel_id_file = toplevel / f'.ytm/{track.channel_id}/.channel'
    channel_id_file.parent.mkdir(parents=True, exist_ok=True)
    channel_id_file.write_text(track.channel_id)

    artist_info = toplevel / f'channels/{track.artist}/.channel'
    artist_info.parent.mkdir(parents=True, exist_ok=True)
    artist_info.write_text(track.channel_id) # TODO: append channel_id to file if it already exists and uniq it

    if track.album:
        link_to_track = toplevel / f'channels/{track.artist}/{track.album}/{track.title}.ogg'
    else:
        link_to_track = toplevel / f'channels/{track.artist}/unsorted/{track.title}.ogg'
    link_to_track.parent.mkdir(parents=True, exist_ok=True)
    link_to_track.unlink(missing_ok=True)
    link_to_track.symlink_to(os.path.relpath(toplevel / track.path, link_to_track.parent))
    if (toplevel / track.path).exists():
        print(f"Track {track.title} already exists, skipping...")
        return track
    with TemporaryDirectory() as tmp_dir:
        print(f'will download track {str(toplevel / track.path)}')
        ydl = YoutubeDL(get_downloader_options(output_dir = Path(tmp_dir)))
        ydl.download([track.youtube_id])
        tmp_path = Path(f'{tmp_dir}/track.ogg')
        (toplevel / track.path).parent.mkdir(parents=True, exist_ok=True)
        print(f'moving {tmp_path} to {toplevel / track.path}')
        shutil.move(tmp_path, toplevel / track.path)
    return track


def download_channel(toplevel: Path, channel_id: str) -> None:
    tracks =  get_channel_releases(channel_id) | get_channel_tracks(channel_id)
    for track in tracks:
        track = download_track(toplevel, tracks[track])

def download_playlist(toplevel: Path, playlist_url: str) -> None:
    playlist_info = get_ydl_info(playlist_url)

    playlist_url_file = toplevel / f'playlists/{playlist_info["title"]}/.playlist'
    playlist_url_file.parent.mkdir(parents=True, exist_ok=True)
    playlist_url_file.write_text(playlist_url)

    tracks = get_tracks_via_ytdl(playlist_url)
    for track in tracks:
        track = download_track(toplevel, tracks[track])
        link_to_track = toplevel / f'playlists/{playlist_info["title"]}/{track.title}.ogg'
        link_to_track.parent.mkdir(parents=True, exist_ok=True)
        link_to_track.unlink(missing_ok=True)
        link_to_track.symlink_to(os.path.relpath(toplevel / track.path, link_to_track.parent))

def find_ytm_directory() -> Path:
    path = Path.cwd()
    while path.parent != path:
        if (path / ".ytm").exists():
            print(f'found .ytm directory at {path}')
            return path
        path = path.parent
    raise Exception("Could not find .ytm directory")
