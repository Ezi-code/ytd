# ytdown

[![PyPI version](https://img.shields.io/pypi/v/ytdown)](https://pypi.org/project/ytdown/)
[![Python versions](https://img.shields.io/pypi/pyversions/ytdown)](https://pypi.org/project/ytdown/)
[![CI](https://github.com/ezra/ytdown/actions/workflows/ci.yml/badge.svg)](https://github.com/ezra/ytdown/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/ytdown)](https://github.com/ezra/ytdown/blob/main/LICENSE)

A cross-platform YouTube downloader CLI that saves **MP3** files to your **Music** folder and **MP4** files to your **Videos / Movies** folder — with full playlist support.

## Usage

```bash
ytd <url> [mp4|mp3] [codec] [options]
```

### Basic examples

| Command                                           | Action                                     |
|---------------------------------------------------|--------------------------------------------|
| `ytd https://youtube.com/watch?v=abc123`          | Download as MP4 (default)                  |
| `ytd https://youtube.com/watch?v=abc123 mp4`      | Download as MP4                            |
| `ytd https://youtube.com/watch?v=abc123 mp3`      | Download as MP3                            |
| `ytd https://youtube.com/watch?v=abc123 mp3 flac` | Download as FLAC audio                     |
| `ytd https://youtube.com/watch?v=abc123 mp3 aac`  | Download as AAC audio                      |

Output filenames follow the video title: `%(title)s.mp4` / `%(title)s.%(ext)s`.

### Playlist options

| Option                    | Description                                           |
|---------------------------|-------------------------------------------------------|
| `--no-playlist`           | Download only the video, skip the playlist            |
| `--playlist-start N`      | Start at playlist index N (1-based)                   |
| `--playlist-end N`        | End at playlist index N (1-based)                     |
| `--max-downloads N`       | Stop after N downloads                                |

```bash
ytd https://youtube.com/playlist?list=... mp3 --playlist-start 3 --playlist-end 10
ytd https://youtube.com/watch?v=abc123 mp4 --no-playlist
ytd https://youtube.com/playlist?list=... mp4 --max-downloads 5
```

### Override output directory

```bash
ytd https://youtube.com/watch?v=abc123 mp4 -o ~/Desktop
ytd https://youtube.com/watch?v=abc123 mp3 -o "./my songs"
```

## Installation

### Prerequisites

- Python 3.14+
- [FFmpeg](https://ffmpeg.org/) (required for MP3 extraction; MP4 works without it)
- [aria2](https://github.com/aria2/aria2) (optional — enables multi-connection downloads for significantly faster speeds)

  | OS      | Install command                            |
  |---------|--------------------------------------------|
  | Linux   | `sudo apt install aria2`                   |
  | macOS   | `brew install aria2`                       |
  | Windows | `winget install aria2`                     |

  Without aria2, downloads still benefit from parallel fragment fetching. With aria2, large files get an additional speed boost via 16 concurrent connections per server.

### Via `uv` (recommended)

```bash
uv tool install git+https://github.com/ezra/ytdown
```

Or from a local copy:

```bash
git clone https://github.com/ezra/ytdown
cd ytdown
uv tool install -e .
```

Now `ytd` is available globally.

### Via `pip`

```bash
pip install ytdown
```

### Via `pip` (editable, for development)

```bash
git clone https://github.com/ezra/ytdown
cd ytdown
pip install -e .
```

## Cross-platform folder mapping

ytdown detects your operating system and uses the platform-standard media directories:

| OS      | MP3 target              | MP4 target              |
|---------|-------------------------|-------------------------|
| Linux   | `~/Music` (or `$XDG_MUSIC_DIR`) | `~/Videos` (or `$XDG_VIDEOS_DIR`) |
| macOS   | `~/Music`               | `~/Movies`              |
| Windows | `~/Music`               | `~/Videos`              |

On **Linux**, `~/.config/user-dirs.dirs` is respected if present, so custom XDG directory configurations (`XDG_MUSIC_DIR`, `XDG_VIDEOS_DIR`) are picked up automatically.

Target directories are created on first use if they do not exist.

## Dependencies

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — the actual download engine
- FFmpeg (external) — needed only for MP3/Audio extraction
- aria2 (external, optional) — multi-connection downloader for faster speeds

## Development

```bash
git clone https://github.com/ezra/ytdown
cd ytdown
uv sync
```

Edit `ytd.py` — the CLI entry point is `ytd:main` (registered via `[project.scripts]` in `pyproject.toml`).

### Reinstall after changes

If installed with `uv tool install -e .`, changes are picked up automatically. Otherwise:

```bash
uv tool install --reinstall .
```

## How it works

`ytd` wraps [yt-dlp](https://github.com/yt-dlp/yt-dlp) with sensible defaults:

- **MP4**: downloads the best video + best audio stream and merges them into a single `.mp4` file.
- **MP3**: downloads the best available audio stream and re-encodes it to MP3 at 192 kbps via FFmpeg.

## License

MIT
