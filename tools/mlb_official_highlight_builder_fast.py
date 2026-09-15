#!/usr/bin/env python3
import sys
import mlb_official_highlight_builder as base


def stream_media(url, dest):
    # Pull only the opening seconds needed for the short reel instead of
    # downloading an entire MLB highlight asset before trimming it.
    base.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-rw_timeout", "20000000",
        "-t", "6.5", "-i", url,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(dest)
    ])


base.download_media = stream_media

if __name__ == "__main__":
    base.main()
