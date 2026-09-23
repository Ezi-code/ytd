#!/usr/bin/env python3
"""YouTube downloader CLI — MP4 to Videos, MP3 to Music, with playlist support."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yt_dlp
from yt_dlp.utils import format_bytes

__version__ = "0.1.2a"

_GITHUB_REPO = "ezi-code/ytd"
_GIT_URL = f"git+https://github.com/{_GITHUB_REPO}"


def _speed_opts() -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "concurrent_fragment_downloads": 16,
        "http_chunk_size": 10 * 1024 * 1024,
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
            "-s",
            "16",
            "-k",
            "1M",
            "--file-allocation=none",
            "--allow-overwrite=true",
            "--continue=true",
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

_BAR_WIDTH = 25
_PROGRESS_THROTTLE = 0.1


def _format_speed(speed: Optional[float]) -> str:
    if not speed:
        return "--/s"
    return f"{format_bytes(speed)}/s"


def _format_eta(eta: Optional[float]) -> str:
    if eta is None:
        return "--"
    try:
        eta = int(eta)
    except (TypeError, ValueError):
        return "--"
    minutes, seconds = divmod(eta, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:d}:{seconds:02d}"


def _render_bar(prefix: str, fraction: float, detail: str) -> None:
    fraction = max(0.0, min(1.0, fraction or 0.0))
    filled: int = int(fraction * _BAR_WIDTH)
    bar: str = "#" * filled + "-" * (_BAR_WIDTH - filled)
    sys.stdout.write(f"\r{prefix}: [{bar}] {fraction * 100:5.1f}% {detail}")
    sys.stdout.flush()


def _make_progress_hook(label: str = "Downloading") -> Callable[[Dict[str, Any]], None]:
    """Single-line progress bar hook; handles playlists via filename changes."""
    state: Dict[str, Any] = {"filename": None, "last": 0.0}

    def hook(d: Dict[str, Any]) -> None:
        status: Optional[str] = d.get("status")
        if status == "downloading":
            filename: Optional[str] = d.get("filename")
            if filename != state["filename"]:
                if state["filename"] is not None:
                    sys.stdout.write("\n")
                title: str = str(
                    ((d.get("info_dict") or {}).get("title")) or filename or "file"
                )
                if len(title) > 60:
                    title = title[:57] + "..."
                sys.stdout.write(f"{label}: {title}\n")
                state["filename"] = filename
                state["last"] = 0.0
            downloaded: int = d.get("downloaded_bytes") or 0
            total: Optional[int] = d.get("total_bytes") or d.get("total_bytes_estimate")
            now: float = time.monotonic()
            if total:
                fraction: float = downloaded / total
                if now - state["last"] < _PROGRESS_THROTTLE and fraction < 1.0:
                    return
                state["last"] = now
                detail: str = (
                    f"{format_bytes(downloaded)}/{format_bytes(total)} "
                    f"at {_format_speed(d.get('speed'))} "
                    f"ETA {_format_eta(d.get('eta'))}"
                )
                _render_bar(label, fraction, detail)
            else:
                if now - state["last"] < _PROGRESS_THROTTLE:
                    return
                state["last"] = now
                frag_idx: Optional[int] = d.get("fragment_index")
                frag_count: Optional[int] = d.get("fragment_count")
                if frag_idx is not None and frag_count:
                    _render_bar(
                        label,
                        frag_idx / frag_count,
                        f"fragment {frag_idx}/{frag_count} "
                        f"{format_bytes(downloaded)} "
                        f"at {_format_speed(d.get('speed'))}",
                    )
                else:
                    _render_bar(
                        label,
                        0.0,
                        f"{format_bytes(downloaded)} "
                        f"at {_format_speed(d.get('speed'))}",
                    )
        elif status == "finished":
            total = d.get("total_bytes") or d.get("downloaded_bytes")
            if total:
                _render_bar(
                    label,
                    1.0,
                    f"{format_bytes(total)}/{format_bytes(total)}",
                )
            sys.stdout.write("\nDownload complete.\n")
            sys.stdout.flush()
            state["filename"] = None
            state["last"] = 0.0
        elif status == "error":
            sys.stdout.write("\n")
            sys.stdout.flush()
            state["filename"] = None

    return hook


def _make_postprocessor_hook(
    start_msg: str, done_msg: str
) -> Callable[[Dict[str, Any]], None]:
    """Announce conversion/merge stages; ignore bookkeeping PPs."""

    def hook(d: Dict[str, Any]) -> None:
        pp: str = str(d.get("postprocessor") or "")
        if pp and not (
            "ExtractAudio" in pp
            or "Merger" in pp
            or "Converter" in pp
            or "Remuxer" in pp
        ):
            return
        status: Optional[str] = d.get("status")
        if status == "started":
            sys.stdout.write(f"{start_msg}...\n")
            sys.stdout.flush()
        elif status == "finished":
            sys.stdout.write(f"{done_msg}\n")
            sys.stdout.flush()

    return hook


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
        "quiet": True,
        "verbose": False,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "192",
            }
        ],
        "progress_hooks": [_make_progress_hook()],
        "postprocessor_hooks": [
            _make_postprocessor_hook(
                f"Converting to {codec.upper()}", "Conversion complete."
            )
        ],
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
        print(f"Error: {e!s}")
        traceback.print_exc()


def _download_mp4(
    url: str,
    output_dir: Optional[str] = None,
    playlist_opts: Optional[Dict[str, Any]] = None,
) -> None:
    output_path: Path = Path(output_dir) if output_dir else _get_videos_dir()
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "quiet": True,
        "verbose": False,
        "no_warnings": True,
        "noprogress": True,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "progress_hooks": [_make_progress_hook()],
        "postprocessor_hooks": [
            _make_postprocessor_hook("Merging formats", "Merge complete.")
        ],
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
        print(f"Error: {e!s}")
        traceback.print_exc()


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


def _build_update_command() -> List[str]:
    uv: Optional[str] = shutil.which("uv")
    if uv:
        return [uv, "tool", "install", "--force", "--refresh", _GIT_URL]
    return [sys.executable, "-m", "pip", "install", "--force-reinstall", _GIT_URL]


def run_update() -> int:
    """Reinstall ytd from the latest GitHub main branch. Returns exit code."""
    cmd: List[str] = _build_update_command()
    print(f"Updating ytd to the latest version from GitHub ({_GITHUB_REPO})...")
    try:
        result: subprocess.CompletedProcess = subprocess.run(cmd, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Update failed: {e}. Try manually: {' '.join(cmd)}")
        return 1
    if result.returncode == 0:
        print("Update completed successfully!")
    else:
        print(
            f"Update failed (exit code {result.returncode}). "
            f"Try manually: {' '.join(cmd)}"
        )
    return result.returncode


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
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="YouTube video or playlist URL",
    )
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
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update ytd to the latest version from GitHub and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
    if args.update:
        raise SystemExit(run_update())
    if not args.url:
        parser.error("the following arguments are required: url")
    playlist_opts: Optional[Dict[str, Any]] = _build_playlist_opts(args)
    download_youtube(args.url, args.format, args.codec, args.output_dir, playlist_opts)


if __name__ == "__main__":
    main()
