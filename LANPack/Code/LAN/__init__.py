# -*- coding: utf-8 -*-
"""
LucasChessR - LAN extension pack
================================

Adds "play a game against another person over the local network" to any
original LucasChessR installation.

The pack is purely additive: no original file is modified.  The only file that
is *shadowed* is ``Code/Menus/PlayMenu.py`` which does not exist in the
official binary distribution (it only ships ``PlayMenu.pyc``).  That new file
simply loads the original compiled module and then adds one extra menu entry.
"""

import builtins

from Code.LAN.protocol import DEFAULT_TCP_PORT, DEFAULT_UDP_PORT, PROTO_VERSION  # noqa: F401

VERSION = "1.0.0"

__all__ = ["VERSION", "DEFAULT_TCP_PORT", "DEFAULT_UDP_PORT", "tr"]


def tr(text):
    """Translation helper.

    LucasChess installs the ``_()`` function as a builtin when the translation
    is loaded.  We resolve it at call time so that importing this package never
    depends on the translation being ready.
    """
    func = getattr(builtins, "_", None)
    if callable(func):
        try:
            return func(text)
        except Exception:
            return text
    return text
