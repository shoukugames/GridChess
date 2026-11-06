"""Locate bundled files both from source and inside a PyInstaller build."""
import os
import sys


def root():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def asset(*parts):
    return os.path.join(root(), "assets", *parts)
