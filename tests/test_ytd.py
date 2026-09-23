import argparse
import io
import platform
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from ytd import (
    _VALID_AUDIO_CODECS,
    _build_playlist_opts,
    _download_mp3,
    _download_mp4,
    _format_eta,
    _format_speed,
    _get_music_dir,
    _get_videos_dir,
    _make_postprocessor_hook,
    _make_progress_hook,
    _speed_opts,
    download_youtube,
)


class TestConstants(unittest.TestCase):
    def test_valid_audio_codecs(self):
        expected = {"mp3", "aac", "flac", "opus", "m4a", "wav", "best"}
        self.assertEqual(_VALID_AUDIO_CODECS, expected)


class TestSpeedOpts(unittest.TestCase):
    @patch.object(shutil, "which", return_value=None)
    def test_without_aria2(self, mock_which):
        opts = _speed_opts()
        self.assertEqual(opts["concurrent_fragment_downloads"], 16)
        self.assertEqual(opts["socket_timeout"], 30)
        self.assertEqual(opts["retries"], 10)
        self.assertEqual(opts["fragment_retries"], 10)
        self.assertEqual(opts["http_chunk_size"], 10 * 1024 * 1024)
        self.assertNotIn("external_downloader", opts)

    def test_speed_opt_numerics_are_ints(self):
        # Regression test: yt-dlp's Python API expects ints (bytes) for
        # these options. A CLI-style string like "10M" reaches
        # downloader/http.py `chunk_size * 0.95` and raises
        # "can't multiply sequence by non-int of type 'float'".
        opts = _speed_opts()
        for key in (
            "concurrent_fragment_downloads",
            "http_chunk_size",
            "socket_timeout",
            "retries",
            "fragment_retries",
        ):
            self.assertIsInstance(
                opts[key], int, f"{key} must be int, got {opts[key]!r}"
            )

    @patch.object(shutil, "which", return_value="/usr/bin/aria2c")
    def test_with_aria2(self, mock_which):
        opts = _speed_opts()
        self.assertEqual(opts["external_downloader"], "aria2c")
        self.assertIn("-x", opts["external_downloader_args"])
        self.assertIn("-s", opts["external_downloader_args"])
        self.assertIn("16", opts["external_downloader_args"])
        self.assertIn("--file-allocation=none", opts["external_downloader_args"])


class TestGetMusicDir(unittest.TestCase):
    @patch.object(platform, "system", return_value="Linux")
    @patch.object(Path, "exists", return_value=False)
    def test_linux_default(self, mock_exists, mock_system):
        expected = Path.home() / "Music"
        self.assertEqual(_get_music_dir(), expected)

    @patch.object(platform, "system", return_value="Linux")
    def test_linux_xdg(self, mock_system):
        mock_xdg = MagicMock()
        mock_xdg.exists.return_value = True
        mock_xdg.read_text.return_value = 'XDG_MUSIC_DIR="$HOME/Music"\n'
        with patch.object(Path, "__truediv__", return_value=mock_xdg):
            result = _get_music_dir()
            self.assertEqual(result, Path.home() / "Music")

    @patch.object(platform, "system", return_value="Darwin")
    def test_macos(self, mock_system):
        expected = Path.home() / "Music"
        self.assertEqual(_get_music_dir(), expected)

    @patch.object(platform, "system", return_value="Windows")
    def test_windows(self, mock_system):
        expected = Path.home() / "Music"
        self.assertEqual(_get_music_dir(), expected)


class TestGetVideosDir(unittest.TestCase):
    @patch.object(platform, "system", return_value="Linux")
    @patch.object(Path, "exists", return_value=False)
    def test_linux_default(self, mock_exists, mock_system):
        expected = Path.home() / "Videos"
        self.assertEqual(_get_videos_dir(), expected)

    @patch.object(platform, "system", return_value="Darwin")
    def test_macos(self, mock_system):
        expected = Path.home() / "Movies"
        self.assertEqual(_get_videos_dir(), expected)

    @patch.object(platform, "system", return_value="Windows")
    def test_windows(self, mock_system):
        expected = Path.home() / "Videos"
        self.assertEqual(_get_videos_dir(), expected)


class TestBuildPlaylistOpts(unittest.TestCase):
    def test_no_args(self):
        args = argparse.Namespace(
            no_playlist=False,
            playlist_start=None,
            playlist_end=None,
            max_downloads=None,
        )
        self.assertIsNone(_build_playlist_opts(args))

    def test_no_playlist(self):
        args = argparse.Namespace(
            no_playlist=True,
            playlist_start=None,
            playlist_end=None,
            max_downloads=None,
        )
        self.assertEqual(_build_playlist_opts(args), {"noplaylist": True})

    def test_playlist_start(self):
        args = argparse.Namespace(
            no_playlist=False,
            playlist_start=3,
            playlist_end=None,
            max_downloads=None,
        )
        self.assertEqual(_build_playlist_opts(args), {"playliststart": 3})

    def test_playlist_end(self):
        args = argparse.Namespace(
            no_playlist=False,
            playlist_start=None,
            playlist_end=10,
            max_downloads=None,
        )
        self.assertEqual(_build_playlist_opts(args), {"playlistend": 10})

    def test_max_downloads(self):
        args = argparse.Namespace(
            no_playlist=False,
            playlist_start=None,
            playlist_end=None,
            max_downloads=5,
        )
        self.assertEqual(_build_playlist_opts(args), {"max_downloads": 5})

    def test_all_options(self):
        args = argparse.Namespace(
            no_playlist=True,
            playlist_start=1,
            playlist_end=5,
            max_downloads=5,
        )
        expected = {
            "noplaylist": True,
            "playliststart": 1,
            "playlistend": 5,
            "max_downloads": 5,
        }
        self.assertEqual(_build_playlist_opts(args), expected)


class TestDownloadYoutubeRouting(unittest.TestCase):
    @patch("ytd._download_mp3")
    def test_routes_to_mp3(self, mock_mp3):
        download_youtube("http://example.com", "mp3", codec="flac")
        mock_mp3.assert_called_once_with("http://example.com", "flac", None, None)

    @patch("ytd._download_mp3")
    def test_routes_to_mp3_default_codec(self, mock_mp3):
        download_youtube("http://example.com", "mp3")
        mock_mp3.assert_called_once_with("http://example.com", "mp3", None, None)

    @patch("ytd._download_mp4")
    def test_routes_to_mp4(self, mock_mp4):
        download_youtube("http://example.com", "mp4")
        mock_mp4.assert_called_once_with("http://example.com", None, None)

    @patch("ytd._download_mp4")
    def test_routes_to_mp4_default(self, mock_mp4):
        download_youtube("http://example.com")
        mock_mp4.assert_called_once_with("http://example.com", None, None)

    def test_invalid_format(self):
        with patch("builtins.print") as mock_print:
            download_youtube("http://example.com", "avi")
            mock_print.assert_called_once_with("Invalid format. Use 'mp4' or 'mp3'.")

    @patch("ytd._download_mp4")
    def test_passes_output_dir(self, mock_mp4):
        download_youtube("http://example.com", "mp4", output_dir="/custom/path")
        mock_mp4.assert_called_once_with("http://example.com", "/custom/path", None)

    @patch("ytd._download_mp3")
    def test_passes_playlist_opts(self, mock_mp3):
        playlist_opts = {"playliststart": 1, "playlistend": 5}
        download_youtube("http://example.com", "mp3", playlist_opts=playlist_opts)
        mock_mp3.assert_called_once_with(
            "http://example.com", "mp3", None, playlist_opts
        )


class TestDownloadMp3(unittest.TestCase):
    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_codec_ffmpeg_maps_to_mp3(
        self, mock_ydl, mock_speed, mock_music_dir, mock_mkdir
    ):
        _download_mp3("http://example.com", codec="ffmpeg")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertEqual(ydl_opts["postprocessors"][0]["preferredcodec"], "mp3")

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_invalid_codec_falls_back_to_mp3(
        self, mock_ydl, mock_speed, mock_music_dir, mock_mkdir
    ):
        _download_mp3("http://example.com", codec="wma")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertEqual(ydl_opts["postprocessors"][0]["preferredcodec"], "mp3")

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_custom_codec(self, mock_ydl, mock_speed, mock_music_dir, mock_mkdir):
        _download_mp3("http://example.com", codec="flac")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertEqual(ydl_opts["postprocessors"][0]["preferredcodec"], "flac")

    @patch("pathlib.Path.mkdir")
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_custom_output_dir(self, mock_ydl, mock_speed, mock_mkdir):
        _download_mp3("http://example.com", output_dir="/custom/path")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertIn("/custom/path", ydl_opts["outtmpl"])

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_playlist_opts_merged(
        self, mock_ydl, mock_speed, mock_music_dir, mock_mkdir
    ):
        _download_mp3(
            "http://example.com",
            playlist_opts={"playliststart": 2, "playlistend": 5},
        )
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertEqual(ydl_opts["playliststart"], 2)
        self.assertEqual(ydl_opts["playlistend"], 5)

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("yt_dlp.YoutubeDL")
    def test_passes_int_http_chunk_size(self, mock_ydl, mock_music_dir, mock_mkdir):
        # Uses the real _speed_opts (not mocked to {}) so a string
        # http_chunk_size regression is caught here.
        _download_mp3("http://example.com")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertIsInstance(ydl_opts["http_chunk_size"], int)

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("yt_dlp.YoutubeDL")
    def test_no_conflicting_quality_args(self, mock_ydl, mock_music_dir, mock_mkdir):
        # preferredquality "192" already sets -b:a 192k via
        # FFmpegExtractAudio; a global "-q:a 0" (VBR scale) conflicts.
        _download_mp3("http://example.com")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertNotIn("postprocessor_args", ydl_opts)


class TestDownloadMp4(unittest.TestCase):
    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_videos_dir", return_value=Path("/fake/Videos"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_default_path(self, mock_ydl, mock_speed, mock_videos_dir, mock_mkdir):
        _download_mp4("http://example.com")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertIn("/fake/Videos", ydl_opts["outtmpl"])
        self.assertEqual(ydl_opts["format"], "bv*+ba/b")

    @patch("pathlib.Path.mkdir")
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_custom_output_dir(self, mock_ydl, mock_speed, mock_mkdir):
        _download_mp4("http://example.com", output_dir="/custom/path")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertIn("/custom/path", ydl_opts["outtmpl"])

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_videos_dir", return_value=Path("/fake/Videos"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_playlist_opts_merged(
        self, mock_ydl, mock_speed, mock_videos_dir, mock_mkdir
    ):
        _download_mp4(
            "http://example.com",
            playlist_opts={"max_downloads": 3},
        )
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertEqual(ydl_opts["max_downloads"], 3)


class TestQuietProgressOpts(unittest.TestCase):
    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_music_dir", return_value=Path("/fake/Music"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_mp3_uses_quiet_progress_hooks(
        self, mock_ydl, mock_speed, mock_music_dir, mock_mkdir
    ):
        _download_mp3("http://example.com")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertTrue(ydl_opts["quiet"])
        self.assertTrue(ydl_opts["noprogress"])
        self.assertTrue(ydl_opts["progress_hooks"])
        self.assertTrue(ydl_opts["postprocessor_hooks"])

    @patch("pathlib.Path.mkdir")
    @patch("ytd._get_videos_dir", return_value=Path("/fake/Videos"))
    @patch("ytd._speed_opts", return_value={})
    @patch("yt_dlp.YoutubeDL")
    def test_mp4_uses_quiet_progress_hooks(
        self, mock_ydl, mock_speed, mock_videos_dir, mock_mkdir
    ):
        _download_mp4("http://example.com")
        ydl_opts = mock_ydl.call_args[0][0]
        self.assertTrue(ydl_opts["quiet"])
        self.assertTrue(ydl_opts["noprogress"])
        self.assertTrue(ydl_opts["progress_hooks"])
        self.assertTrue(ydl_opts["postprocessor_hooks"])


class TestProgressHook(unittest.TestCase):
    def test_downloading_renders_bar(self):
        hook = _make_progress_hook()
        buf = io.StringIO()
        with redirect_stdout(buf):
            hook(
                {
                    "status": "downloading",
                    "filename": "/tmp/a.mp3",
                    "downloaded_bytes": 5 * 1024 * 1024,
                    "total_bytes": 10 * 1024 * 1024,
                    "speed": 1024 * 1024,
                    "eta": 5,
                    "info_dict": {"title": "Some Video"},
                }
            )
        out = buf.getvalue()
        self.assertIn("Downloading: Some Video", out)
        self.assertIn("50.0%", out)

    def test_downloading_unknown_total(self):
        hook = _make_progress_hook()
        buf = io.StringIO()
        with redirect_stdout(buf):
            hook(
                {
                    "status": "downloading",
                    "filename": "/tmp/a.mp3",
                    "downloaded_bytes": 1024,
                    "total_bytes": None,
                    "total_bytes_estimate": None,
                    "speed": None,
                    "eta": None,
                    "info_dict": {},
                }
            )
        self.assertIn("Downloading", buf.getvalue())

    def test_finished_and_error(self):
        hook = _make_progress_hook()
        buf = io.StringIO()
        with redirect_stdout(buf):
            hook({"status": "finished", "filename": "/tmp/a.mp3"})
            hook({"status": "error", "filename": "/tmp/a.mp3"})
        self.assertIn("Download complete.", buf.getvalue())

    def test_format_helpers(self):
        self.assertEqual(_format_speed(None), "--/s")
        self.assertIn("/s", _format_speed(1024))
        self.assertEqual(_format_eta(None), "--")
        self.assertEqual(_format_eta(65), "1:05")


class TestPostprocessorHook(unittest.TestCase):
    def test_announces_ffmpeg_pp(self):
        hook = _make_postprocessor_hook("Converting to MP3", "Conversion complete.")
        buf = io.StringIO()
        with redirect_stdout(buf):
            hook({"status": "started", "postprocessor": "FFmpegExtractAudio"})
            hook({"status": "finished", "postprocessor": "FFmpegExtractAudio"})
        out = buf.getvalue()
        self.assertIn("Converting to MP3...", out)
        self.assertIn("Conversion complete.", out)

    def test_ignores_bookkeeping_pp(self):
        hook = _make_postprocessor_hook("Converting to MP3", "Conversion complete.")
        buf = io.StringIO()
        with redirect_stdout(buf):
            hook({"status": "started", "postprocessor": "MoveFiles"})
            hook({"status": "finished", "postprocessor": "MoveFiles"})
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
