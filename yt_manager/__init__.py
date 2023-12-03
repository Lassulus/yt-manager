import argparse
from pathlib import Path
from .lib import download_channel, download_playlist, find_ytm_directory


def init_command(args: argparse.Namespace) -> None:
    args.path.mkdir(parents=True, exist_ok=True)
    (args.path / ".ytm").mkdir(parents=True, exist_ok=True)

def pull_command(args: argparse.Namespace) -> None:
    ytm_toplevel = find_ytm_directory()
    if (args.path / ".channel").exists():
        channel_id = (args.path / ".channel").read_text().strip()
        download_channel(ytm_toplevel, channel_id)
    elif (args.path / ".playlist").exists():
        download_playlist(ytm_toplevel, (args.path / ".playlist").read_text().strip())
    else:
        raise Exception("Could not find .channel or .playlist file")

def download_command(args: argparse.Namespace) -> None:
    ytm_toplevel = find_ytm_directory()
    if args.url.startswith('https://www.youtube.com/playlist?list='):
        download_playlist(ytm_toplevel, args.url)
    else:
        # we assume it's a channel if it's not a playlist
        download_channel(ytm_toplevel, args.url)

def main():
    parser = argparse.ArgumentParser(prog=None, description='yt_manager')
    subparsers = parser.add_subparsers()

    parser_init = subparsers.add_parser('init', help='initialize a folder for yt_manager')
    parser_init.add_argument('path', type=Path, help='path to folder managed by yt_manager', default=Path.cwd(), nargs='?')
    parser_init.set_defaults(func=init_command)

    parser_pull = subparsers.add_parser('pull', help='pull a channel or playlist')
    parser_pull.add_argument('path', type=Path, help='path to channel or playlist folder', default=Path.cwd(), nargs='?')
    parser_pull.set_defaults(func=pull_command)

    parser_download = subparsers.add_parser('download', help='download a channel, playlist or single track')
    parser_download.add_argument('url', type=str, help='url for a channel, playlist or single track')
    parser_download.set_defaults(func=download_command)

    args = parser.parse_args()
    args.func(args)
