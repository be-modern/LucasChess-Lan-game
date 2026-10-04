# -*- coding: utf-8 -*-
"""Dialogs used to set up a game over the local network."""

import os
import random
import socket

from PySide6 import QtCore, QtWidgets

from Code.LAN import DEFAULT_TCP_PORT, tr as _
from Code.LAN import chat, discovery, net
from Code.QT import Colocacion, Controles, Iconos, QTMessages

try:
    from Code.QT import LCDialog
except ImportError:  # pragma: no cover - very old builds
    LCDialog = None


def _icon():
    """Icon for the LAN dialogs (never fails)."""
    for name in ("Link", "Connected", "HumanHuman", "Play"):
        try:
            return getattr(Iconos, name)()
        except Exception:
            continue
    return QtWidgets.QApplication.style().standardIcon(
        QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon
    )


#: Python side references to the live connections.
#:
#: The dialogs are created with ``WA_DeleteOnClose``, so Qt deletes them (and
#: every child object) as soon as they are closed.  A connection must therefore
#: be re-parented to the main window while the dialog is still alive, and a
#: python reference must be kept as well.
_KEEP_ALIVE = []


def keep_alive(link):
    if not any(kept is link for kept in _KEEP_ALIVE):
        _KEEP_ALIVE.append(link)
    return link


def release(link):
    for kept in list(_KEEP_ALIVE):
        if kept is link:
            _KEEP_ALIVE.remove(kept)
    return link


def default_player_name():
    """A sensible default for the player name."""
    try:
        name = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    except Exception:
        name = ""
    if not name:
        try:
            name = socket.gethostname()
        except Exception:
            name = ""
    return name or _("Player")


class WWaiting(QtWidgets.QDialog):
    """Small modal dialog shown while we wait for the opponent."""

    def __init__(self, owner, texto, with_cancel=True, chat_room=None):
        super().__init__(owner)
        self.setWindowTitle(_("Local network game"))
        self.setWindowIcon(_icon())
        self.setModal(True)

        self.lb = Controles.LB(self, texto)
        self.lb.set_wrap()
        self.lb.minimum_width(360)
        # let the user select the address and read it out to the opponent
        self.lb.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        # a busy bar: waiting is clearly not the same as stuck
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(8)
        self.progress.setStyleSheet(
            "QProgressBar { border: none; background-color: #e0e0e0; border-radius: 2px; }"
            "QProgressBar::chunk { background-color: #4caf50; border-radius: 2px; }"
        )

        layout = Colocacion.V().control(self.lb).espacio(6).control(self.progress).espacio(10)

        # waiting for the opponent does not mean being unable to talk
        self.chat_room = chat_room
        self.chat_panel = None
        if chat_room is not None:
            self.chat_panel = chat.ChatPanel(self, min_height=110)
            self.chat_panel.sendRequested.connect(self._send_chat)
            chat_room.messageReceived.connect(self.chat_panel.add_message)
            layout.control(
                Controles.GB(
                    self,
                    _("Chat with everybody on the network"),
                    Colocacion.V().control(self.chat_panel),
                )
            )
            layout.espacio(8)

        if with_cancel:
            self.bt_cancel = Controles.PB(self, _("Cancel"), self.reject, plano=False)
            layout.control(self.bt_cancel)
        layout.margen(12)
        self.setLayout(layout)
        self.adjustSize()

    def _send_chat(self, text):
        if not text or self.chat_room is None:
            return
        self.chat_room.send(text)
        if self.chat_panel is not None:
            self.chat_panel.add_message(self.chat_room.my_name, text, own=True)

    def closeEvent(self, event):
        if self.chat_room is not None and self.chat_panel is not None:
            try:
                self.chat_room.messageReceived.disconnect(self.chat_panel.add_message)
            except Exception:
                pass
        super().closeEvent(event)


class WLanGame(LCDialog.LCDialog if LCDialog else QtWidgets.QDialog):
    """Setup dialog: create a game (host) or join one (client)."""

    MODE_HOST = "H"
    MODE_JOIN = "J"

    def __init__(self, main_window):
        if LCDialog:
            super().__init__(main_window, _("Play on the local network"), _icon(), "lanplay")
        else:  # pragma: no cover
            super().__init__(main_window)

        self.link = None
        self.dic = None
        self.server = None
        self.discovery = discovery.LanDiscovery(self)
        self.discovery.changed.connect(self.refresh_hosts)
        self._hosts = []

        # --- chat room (everybody with this dialog open) ------------------
        self.chat_room = chat.LanChatRoom(self)
        self.chat_panel = chat.ChatPanel(self, min_height=110)
        self.chat_panel.sendRequested.connect(self._send_room_chat)
        self.chat_room.messageReceived.connect(self.chat_panel.add_message)

        self.setWindowTitle(_("Play on the local network"))

        # --- identity -----------------------------------------------------
        self.ed_name = Controles.ED(self, default_player_name())
        self.ed_name.textChanged.connect(self._update_chat_name)

        # --- mode ---------------------------------------------------------
        self.cb_mode = Controles.CB(
            self,
            [(_("Create a game (this computer waits for an opponent)"), self.MODE_HOST),
             (_("Join a game created on another computer"), self.MODE_JOIN)],
            self.MODE_HOST,
        )
        self.cb_mode.currentIndexChanged.connect(self.refresh_ui)

        # --- host options ---------------------------------------------------
        self.sb_port = Controles.SB(self, DEFAULT_TCP_PORT, 1024, 65535)
        self.cb_color = Controles.CB(
            self,
            [(_("White"), "W"), (_("Black"), "B"), (_("Random"), "R")],
            "W",
        )
        self.lb_ip = Controles.LB(self, self._ip_text())
        self.bt_copy_ip = Controles.PB(self, _("Copy"), self.copy_ip, plano=True)
        self.bt_copy_ip.setToolTip(_("Copy the IP address of this computer"))

        # --- join options ---------------------------------------------------
        self.lw_hosts = QtWidgets.QListWidget(self)
        self.lw_hosts.itemSelectionChanged.connect(self.host_selected)
        self.lw_hosts.itemDoubleClicked.connect(lambda _item: self.accept())
        self.bt_refresh = Controles.PB(self, _("Search again"), self.start_scan, plano=False)
        self.ed_ip = Controles.ED(self, "")
        self.ed_ip.setPlaceholderText(_("IP address of the other computer"))
        self.sb_port2 = Controles.SB(self, DEFAULT_TCP_PORT, 1024, 65535)

        # --- time control ----------------------------------------------------
        # a network game usually has a clock, so it is enabled by default
        self.chb_time = Controles.CHB(self, _("Limit time"), True)
        self.chb_time.clicked.connect(self.refresh_ui)
        self.sb_minutes = Controles.SB(self, 5, 1, 180)
        self.sb_seconds = Controles.SB(self, 3, 0, 60)

        # --- buttons ---------------------------------------------------------
        self.bt_accept = Controles.PB(self, _("Accept"), self.accept, plano=False)
        self.bt_accept.setStyleSheet(chat.accent_button_style())
        self.bt_cancel = Controles.PB(self, _("Cancel"), self.cancelar, plano=True)

        self._build_layout()
        self.refresh_ui()
        self.restore_video_ext()
        self._start_chat()

    def restore_video_ext(self):
        try:
            self.restore_video()
        except Exception:
            pass

    def save_video_ext(self):
        try:
            self.save_video()
        except Exception:
            pass

    # ---------------------------------------------------------------- layout
    def _build_layout(self):
        ly_name = Colocacion.H().control(Controles.LB(self, _("Your name") + ": ")).control(self.ed_name)

        gb_identity = Controles.GB(
            self,
            _("Identity"),
            Colocacion.V().otro(ly_name).control(self.cb_mode),
        )

        gb_join = Controles.GB(
            self,
            _("Games found on the network"),
            Colocacion.V()
            .control(self.lw_hosts)
            .otro(Colocacion.H().control(self.bt_refresh).relleno())
            .otro(Colocacion.H().control(Controles.LB(self, _("Address") + ": ")).control(self.ed_ip)
                  .control(Controles.LB(self, _("Port") + ": ")).control(self.sb_port2)),
        )

        gb_host = Controles.GB(
            self,
            _("Game created on this computer"),
            Colocacion.V()
            .otro(Colocacion.H().control(Controles.LB(self, _("Port") + ": ")).control(self.sb_port).relleno())
            .otro(Colocacion.H().control(Controles.LB(self, _("You play with") + ": ")).control(self.cb_color).relleno())
            .otro(Colocacion.H().control(self.lb_ip).control(self.bt_copy_ip).relleno()),
        )
        self.gb_host = gb_host
        self.gb_join = gb_join

        gb_time = Controles.GB(
            self,
            _("Time"),
            Colocacion.V()
            .control(self.chb_time)
            .otro(Colocacion.H().control(Controles.LB(self, _("Minutes") + ": ")).control(self.sb_minutes)
                  .control(Controles.LB(self, _("Seconds added per move") + ": ")).control(self.sb_seconds)
                  .relleno()),
        )

        gb_chat = Controles.GB(
            self,
            _("Chat with everybody on the network"),
            Colocacion.V().control(self.chat_panel),
        )

        ly_buttons = Colocacion.H().relleno().control(self.bt_accept).control(self.bt_cancel)

        layout = (
            Colocacion.V()
            .control(gb_identity)
            .control(gb_host)
            .control(gb_join)
            .control(gb_time)
            .control(gb_chat)
            .otro(ly_buttons)
            .margen(10)
        )
        self.setLayout(layout)

    # ------------------------------------------------------------------ chat
    def _update_chat_name(self):
        self.chat_room.my_name = self.ed_name.texto().strip() or _("Player")

    def _start_chat(self):
        self._update_chat_name()
        self.chat_room.start(self.chat_room.my_name)
        self.chat_panel.add_system(_("You are in the chat room of the local network"))

    def _send_room_chat(self, text):
        if not text:
            return
        self._update_chat_name()
        self.chat_room.send(text)
        self.chat_panel.add_message(self.chat_room.my_name, text, own=True)

    def _ip_text(self):
        ips = discovery.local_addresses()
        if ips:
            return _("IP of this computer") + ": " + ", ".join(ips[:3])
        return _("IP of this computer") + ": ?"

    def copy_ip(self):
        ips = discovery.local_addresses()
        if not ips:
            return
        QtWidgets.QApplication.clipboard().setText(ips[0])
        self.bt_copy_ip.set_text(_("Copied!"))
        QtCore.QTimer.singleShot(1500, lambda: self.bt_copy_ip.set_text(_("Copy")))

    # ------------------------------------------------------------------ slots
    def refresh_ui(self, *args):
        host = self.cb_mode.valor() == self.MODE_HOST
        self.gb_host.setVisible(host)
        self.gb_join.setVisible(not host)
        with_time = self.chb_time.isChecked()
        self.sb_minutes.setEnabled(with_time)
        self.sb_seconds.setEnabled(with_time)
        if not host:
            if self.discovery.mode != discovery.LanDiscovery.MODE_CLIENT:
                self.start_scan()
        else:
            self.discovery.stop()
        self.adjustSize()

    def start_scan(self):
        self.discovery.start_scan()

    def host_selected(self):
        row = self.lw_hosts.currentRow()
        if 0 <= row < len(self._hosts):
            ip, port, _name = self._hosts[row]
            self.ed_ip.set_text(ip)
            self.sb_port2.set_value(port)

    def refresh_hosts(self):
        self._hosts = self.discovery.game_list()
        self.lw_hosts.clear()
        for ip, port, name in self._hosts:
            self.lw_hosts.addItem("%s  (%s:%d)" % (name, ip, port))
        if self._hosts and self.lw_hosts.currentRow() < 0:
            self.lw_hosts.setCurrentRow(0)
            self.host_selected()

    # ------------------------------------------------------------- ownership
    def _adopt(self, link):
        """Take the connection out of this dialog before Qt deletes it.

        ``LCDialog`` sets ``WA_DeleteOnClose``: when the dialog is closed Qt
        destroys it together with all its children.  The server (and therefore
        the link) is a child of the dialog, so the link has to be re-parented
        to the main window while the dialog is still alive.
        """
        parent = None
        try:
            parent = self.parent()
        except Exception:
            parent = None
        try:
            link.setParent(parent)  # None simply detaches it from the dialog
        except Exception:
            pass
        return keep_alive(link)

    # -------------------------------------------------------------- accept
    def time_control(self):
        if self.chb_time.isChecked():
            return True, self.sb_minutes.value(), self.sb_seconds.value()
        return False, 0, 0

    def accept(self):
        name = self.ed_name.texto().strip() or _("Player")
        if self.cb_mode.valor() == self.MODE_HOST:
            ok = self.do_host(name)
        else:
            ok = self.do_join(name)
        if not ok:
            return
        self.chat_room.stop()
        self.save_video_ext()
        super().accept()

    def cancelar(self):
        self.save_video_ext()
        self.reject()

    def _config_dic(self, my_name, rival_name, minutes, seconds, timed, i_am_white):
        white = my_name if i_am_white else rival_name
        black = rival_name if i_am_white else my_name
        if white and white == black:
            # two players with the same name confuse the original game code
            # (the clocks do not even show up), so tell them apart
            if i_am_white:
                black = "%s (2)" % black
            else:
                white = "%s (2)" % white
        return {
            "WHITE": white,
            "BLACK": black,
            "WITHTIME": timed,
            "MINUTES": minutes,
            "SECONDS": seconds,
            # the original human vs human dialog always provides these two
            "ACTIVATE_EBOARD": False,
            "AUTO_ROTATE": False,
            "LAN_IS_WHITE": i_am_white,
            "LAN_RIVAL": rival_name,
            "LAN_LINK": self.link,
        }

    # ------------------------------------------------------------- host mode
    def do_host(self, name):
        port = self.sb_port.value()
        self.server = net.LanServer(self)
        if not self.server.listen(port):
            QTMessages.message_error(
                self,
                "%s\n%s" % (_("Unable to open port %d on this computer") % port, self.server.error_string()),
            )
            self.server = None
            return False

        timed, minutes, seconds = self.time_control()
        color = self.cb_color.valor()
        if color == "R":
            i_am_white = random.randint(0, 1) == 0
        else:
            i_am_white = color == "W"
        self._host_i_am_white = i_am_white
        self._host_config_sent = False

        self.discovery.start_advertise(name, port)

        waiter = WWaiting(
            self,
            "%s<br/><b><tt>%s</tt></b>"
            % ((_("Waiting for an opponent on port %d...") % port), self._ip_text()),
            chat_room=self.chat_room,
        )
        self.server.clientConnected.connect(lambda link: self._host_connected(link, waiter))
        ok = waiter.exec() == QtWidgets.QDialog.DialogCode.Accepted and self.link is not None
        if not ok:
            if self.server:
                self.server.close()
            self.server = None
            self.discovery.stop()
            if self.link is not None:
                self.link.close(say_bye=False)
                self.link = None
            return False

        self.discovery.stop()
        rival = self.link.rival_name or _("Opponent")
        self.dic = self._config_dic(name, rival, minutes, seconds, timed, i_am_white)
        return True

    def _host_connected(self, link, waiter):
        self.link = self._adopt(link)
        link.helloReceived.connect(lambda _msg: self._host_send_config(waiter))
        link.disconnected.connect(waiter.reject)

    def _host_send_config(self, waiter):
        if getattr(self, "_host_config_sent", False):
            return
        self._host_config_sent = True
        timed, minutes, seconds = self.time_control()
        i_am_white = self._host_i_am_white
        my_name = self.ed_name.texto().strip() or _("Player")
        rival = self.link.rival_name or _("Opponent")
        white = my_name if i_am_white else rival
        black = rival if i_am_white else my_name
        self.link.send_config(white, black, minutes, seconds, timed, not i_am_white)
        waiter.accept()

    # ------------------------------------------------------------ client mode
    def do_join(self, name):
        ip = self.ed_ip.texto().strip()
        if not ip:
            QTMessages.message_error(self, _("You must indicate the address of the other computer"))
            return False
        port = self.sb_port2.value()

        self.discovery.stop()
        link = net.connect_to_host(ip, port, self)
        self.link = self._adopt(link)

        waiter = WWaiting(
            self,
            _("Connecting with %s...") % ("<b><tt>%s:%d</tt></b>" % (ip, port)),
            chat_room=self.chat_room,
        )
        self._client_config = None
        link.configReceived.connect(lambda msg: self._client_got_config(msg, waiter))
        link.disconnected.connect(waiter.reject)
        try:
            link.socket.errorOccurred.connect(lambda _err: waiter.reject())
        except Exception:
            pass

        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(15000)
        timer.timeout.connect(waiter.reject)
        timer.start()

        # the greeting is sent as soon as the socket is really connected
        link.socket.connected.connect(lambda: link.send_hello(name))

        ok = waiter.exec() == QtWidgets.QDialog.DialogCode.Accepted and self._client_config is not None
        timer.stop()
        if not ok:
            link.close(say_bye=False)
            self.link = None
            return False

        cfg = self._client_config
        i_am_white = bool(cfg.get("you_white", True))
        rival = cfg.get("black") if i_am_white else cfg.get("white")
        self.dic = self._config_dic(
            name,
            rival or _("Opponent"),
            int(cfg.get("minutes", 0)),
            int(cfg.get("seconds", 0)),
            bool(cfg.get("timed", False)),
            i_am_white,
        )
        return True

    def _client_got_config(self, msg, waiter):
        self._client_config = msg
        waiter.accept()

    # ---------------------------------------------------------------- closing
    def reject(self):
        self.discovery.stop()
        self.chat_room.stop()
        super().reject()


def play_lan(procesador):
    """Show the wizard and, when a connection is established, start the game."""
    main_window = procesador.main_window
    w = WLanGame(main_window)
    if w.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    link = w.link
    dic = w.dic
    if link is None or dic is None:
        return None

    # the link already belongs to the main window (see WLanGame._adopt); only a
    # python reference is needed so it is not garbage collected during the game
    keep_alive(link)

    from Code.LAN.manager import ManagerPlayLAN

    manager = ManagerPlayLAN(procesador)
    manager.start(dic)
    return manager
