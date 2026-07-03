#!/usr/bin/env python3
"""YouTube downloader CLI — MP4 to Videos, MP3 to Music, with playlist support."""

import argparse
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yt_dlp


def _speed_opts() -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "concurrent_fragment_downloads": 10,
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
    }
    aria2c: Optional[str] = shutil.which("aria2c")
    if aria2c:
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = [
            "-x",
            "16",
            "-k",
            "1M",
            "--min-split-size",
            "1M",
            "--max-connection-per-server",
            "16",
        ]
    return opts


def _get_music_dir() -> Path:
    system: str = platform.system()
    if system == "Linux":
        xdg_config: Path = Path.home() / ".config" / "user-dirs.dirs"
        if xdg_config.exists():
            for line in xdg_config.read_text().splitlines():
                if line.startswith("XDG_MUSIC_DIR="):
                    val: str = line.split("=", 1)[1].strip().strip('"').strip("'")
                    val = os.path.expandvars(val)
                    return Path(val)
        return Path.home() / "Music"
    elif system == "Darwin":
        return Path.home() / "Music"
    elif system == "Windows":
        return Path.home() / "Music"
    return Path.home() / "Music"


def _get_videos_dir() -> Path:
    system: str = platform.system()
    if system == "Linux":
        xdg_config: Path = Path.home() / ".config" / "user-dirs.dirs"
        if xdg_config.exists():
            for line in xdg_config.read_text().splitlines():
                if line.startswith("XDG_VIDEOS_DIR="):
                    val: str = line.split("=", 1)[1].strip().strip('"').strip("'")
                    val = os.path.expandvars(val)
                    return Path(val)
        return Path.home() / "Videos"
    elif system == "Darwin":
        return Path.home() / "Movies"
    elif system == "Windows":
        return Path.home() / "Videos"
    return Path.home() / "Videos"


_VALID_AUDIO_CODECS: set = {"mp3", "aac", "flac", "opus", "m4a", "wav", "best"}


def _download_mp3(
    url: str,
    codec: str = "mp3",
    output_dir: Optional[str] = None,
    playlist_opts: Optional[Dict[str, Any]] = None,
) -> None:
    if codec == "ffmpeg":
        codec = "mp3"
    if codec not in _VALID_AUDIO_CODECS:
        print(f"Invalid audio codec '{codec}'. Using 'mp3'.")
        codec = "mp3"

    output_path: Path = Path(output_dir) if output_dir else _get_music_dir()
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": True,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "192",
            }
        ],
        "postprocessor_args": ["-q:a", "0"],
        **_speed_opts(),
    }
    if playlist_opts:
        ydl_opts.update(playlist_opts)

    print(f"Downloading as {codec.upper()}: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download completed successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")


def _download_mp4(
    url: str,
    output_dir: Optional[str] = None,
    playlist_opts: Optional[Dict[str, Any]] = None,
) -> None:
    output_path: Path = Path(output_dir) if output_dir else _get_videos_dir()
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": True,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        **_speed_opts(),
    }
    if playlist_opts:
        ydl_opts.update(playlist_opts)

    print(f"Downloading as MP4: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download completed successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")


def download_youtube(
    url: str,
    format_type: str = "mp4",
    codec: Optional[str] = None,
    output_dir: Optional[str] = None,
    playlist_opts: Optional[Dict[str, Any]] = None,
) -> None:
    if format_type.lower() == "mp3":
        _download_mp3(url, codec or "mp3", output_dir, playlist_opts)
    elif format_type.lower() == "mp4":
        _download_mp4(url, output_dir, playlist_opts)
    else:
        print("Invalid format. Use 'mp4' or 'mp3'.")


def _build_playlist_opts(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    opts: Dict[str, Any] = {}
    if args.no_playlist:
        opts["noplaylist"] = True
    if args.playlist_start is not None:
        opts["playliststart"] = args.playlist_start
    if args.playlist_end is not None:
        opts["playlistend"] = args.playlist_end
    if args.max_downloads is not None:
        opts["max_downloads"] = args.max_downloads
    return opts or None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ytd",
        description="Download YouTube videos as MP4 (Videos) or MP3 (Music).",
    )
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument(
        "format",
        nargs="?",
        default="mp4",
        choices=["mp4", "mp3"],
        help="Output format (default: mp4)",
    )
    parser.add_argument(
        "codec",
        nargs="?",
        default=None,
        help="Audio codec for MP3 downloads: mp3, aac, flac, opus, m4a, wav, best (default: mp3)",
    )

    playlist = parser.add_argument_group("playlist options")
    playlist.add_argument(
        "--no-playlist",
        action="store_true",
        help="Download only the video, not the whole playlist",
    )
    playlist.add_argument(
        "--playlist-start",
        type=int,
        metavar="N",
        help="Playlist video to start at (1-indexed)",
    )
    playlist.add_argument(
        "--playlist-end",
        type=int,
        metavar="N",
        help="Playlist video to end at (1-indexed)",
    )
    playlist.add_argument(
        "--max-downloads",
        type=int,
        metavar="N",
        help="Abort after N downloads",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        help="Custom output directory (overrides default Music/Videos folder)",
    )

    args: argparse.Namespace = parser.parse_args()
    playlist_opts: Optional[Dict[str, Any]] = _build_playlist_opts(args)
    download_youtube(args.url, args.format, args.codec, args.output_dir, playlist_opts)


if __name__ == "__main__":
    main()
