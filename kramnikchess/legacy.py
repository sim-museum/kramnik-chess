"""Data saved under the app's former name, moved once to Kramnik chess's own places (2026-10-28 rename).

A player who used the app before the rename keeps their rating history, adjourned game, book memory and settings:
at start-up each old location is moved (or, for Qt settings, copied) to the new one, but only when the new one does
not exist yet. This module is the only place the former name appears; it can go once no old installs are left.
"""
import os
import shutil

FORMER = "chessIQ"               # the former name, used here only to find data saved under it


def _move(old, new):
    if os.path.exists(old) and not os.path.exists(new):
        os.makedirs(os.path.dirname(new), exist_ok=True)
        shutil.move(old, new)


def migrate():
    home = os.path.expanduser("~")
    if not os.environ.get("KRAMNIK_HOME"):
        _move(os.path.join(home, ".local", "share", FORMER), os.path.join(home, ".local", "share", "kramnikChess"))
    _move(os.path.join(home, ".config", FORMER.lower(), "bookmem.json"),
          os.path.join(home, ".config", "kramnikChess", "bookmem.json"))
    from PyQt6.QtCore import QSettings
    old, new = QSettings("sim-museum", FORMER), QSettings("sim-museum", "kramnikChess")
    if old.allKeys() and not new.allKeys():
        for k in old.allKeys():
            new.setValue(k, old.value(k))
        new.sync()
