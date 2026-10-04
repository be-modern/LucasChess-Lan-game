# -*- coding: utf-8 -*-
"""Injection of the LAN option into the Play menu.

``install(module)`` is called with the already executed ``Code.Menus.PlayMenu``
module; it adds a new option that starts a game over the local network.
"""

from Code.LAN import tr as _


def _lan_option_icon():
    try:
        from Code.QT import Iconos

        for name in ("Link", "Connected", "HumanHuman"):
            func = getattr(Iconos, name, None)
            if func is not None:
                icon = func()
                if icon is not None:
                    return icon
    except Exception:
        pass
    return None


def install(play_menu_module):
    cls = getattr(play_menu_module, "PlayMenu", None)
    if cls is None or getattr(cls, "_lan_installed", False):
        return False
    cls._lan_installed = True

    original_add_options = cls.add_options

    def add_options(self):
        original_add_options(self)
        try:
            self.new("lan", _("Play on the local network (LAN)"), _lan_option_icon())
        except Exception:
            pass

    def lan(self):
        from Code.LAN.wizard import play_lan

        play_lan(self.procesador)

    cls.add_options = add_options
    cls.lan = lan
    return True
