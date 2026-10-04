# -*- coding: utf-8 -*-
"""Hook: add the "Play on the local network" entry to the Play menu.

This file loads the original compiled module (``PlayMenu.pyc``) and then adds
one option to the menu.  No original file of the program is modified.
"""

import os
import sys

# --------------------------------------------------------------------------
# 1. run the original module so that this file is a perfect replacement
# --------------------------------------------------------------------------
_pyc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PlayMenu.pyc")
if os.path.isfile(_pyc):
    import importlib.machinery

    _loader = importlib.machinery.SourcelessFileLoader(__name__, _pyc)
    _loader.exec_module(sys.modules[__name__])

# --------------------------------------------------------------------------
# 2. add the LAN option
# --------------------------------------------------------------------------
try:
    from Code.LAN.hook import install as _lan_install

    _lan_install(sys.modules[__name__])
except Exception:
    pass
