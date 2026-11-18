#!/usr/bin/env python3
"""Build the browser version into build/web/ with pygbag (https://pygame-web.github.io).

Needs pygame, pygbag (python3 -m pip install pygbag) and ffmpeg on PATH (or FFMPEG=/path):
pygbag converts the .wav sounds to .ogg for the browser with it.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ)
ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
if not ffmpeg:
    sys.exit("ffmpeg not found (set FFMPEG=/path/to/ffmpeg)")
env["PATH"] = os.path.dirname(os.path.abspath(ffmpeg)) + os.pathsep + env.get("PATH", "")
subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "Grid Chess", "--app_name", "gridchess",
                "--icon", "assets/icon.png", "."], cwd=ROOT, env=env, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("build/web ready: upload index.html, gridchess.apk, gridchess.tar.gz and favicon.png")
