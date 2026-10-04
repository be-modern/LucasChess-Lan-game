# -*- coding: utf-8 -*-
"""Chat for the LAN extension.

Two different chats are provided:

* :class:`LanChatRoom` — a room for everybody that has the LAN dialog open on
  the local network (messages are broadcast over UDP, nobody has to be
  connected to a game);
* :class:`ChatWindow` — a small private window used during a game, the
  messages travel over the already established TCP connection.

Both use the very same :class:`ChatPanel` widget.
"""

import time
import uuid

from PySide6 import QtCore, QtNetwork, QtWidgets

from Code.LAN import protocol as P
from Code.LAN import tr as _
from Code.QT import Colocacion, Controles, Iconos

# ------------------------------------------------------------------ palette
# Lifted from the original application stylesheets (found in Code.QT), so the
# extension does not look foreign next to the rest of the program.
COLOR_BG = "#F2F2EC"          # QGroupBox background of the original
COLOR_ACCENT = "#1e749c"      # accent buttons of the original
COLOR_ACCENT_DARK = "#155A78"
COLOR_OWN = "#D6E9F8"         # bubble of my own messages
COLOR_OTHER = "#F0F0EA"       # bubble of the rival messages
COLOR_SYS = "#808080"
COLOR_BORDER = "#C8C4B8"
COLOR_HISTORY = "#FDFDF8"


def accent_button_style():
    """QSS that makes a button look like the accent buttons of the original."""
    return (
        "QPushButton { background-color: %s; color: white; border: none;"
        " border-radius: 6px; font-weight: bold; padding: 3px 14px; }"
        "QPushButton:pressed { background-color: %s; }"
        "QPushButton:disabled { background-color: #9DB9C6; }"
    ) % (COLOR_ACCENT, COLOR_ACCENT_DARK)


def history_style():
    """QSS for the message history: warm paper, thin rounded border."""
    return (
        "QTextEdit { background-color: %s; border: 1px solid %s; border-radius: 4px; }"
    ) % (COLOR_HISTORY, COLOR_BORDER)


def _icon():
    """An icon for the chat windows (never fails)."""
    for name in ("Speak", "Comments", "Link", "Connected", "HumanHuman", "Play"):
        try:
            return getattr(Iconos, name)()
        except Exception:
            continue
    return QtWidgets.QApplication.style().standardIcon(
        QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation
    )


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ChatPanel(QtWidgets.QWidget):
    """Message history + one line to type + a send button."""

    #: emitted with the text the user wants to send
    sendRequested = QtCore.Signal(str)
    #: emitted when the user wants to switch docked / floating
    toggleRequested = QtCore.Signal()

    def __init__(self, parent=None, send_label=None, min_height=130, with_toggle=False):
        super().__init__(parent)

        self.history = QtWidgets.QTextEdit(self)
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(min_height)
        self.history.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self.history.setStyleSheet(history_style())

        self.edit = Controles.ED(self, "")
        self.edit.setPlaceholderText(_("Write a message and press Enter"))
        self.edit.returnPressed.connect(self.send)

        self.button = Controles.PB(self, send_label or _("Send"), self.send, plano=False)
        self.button.setStyleSheet(accent_button_style())

        layout = Colocacion.V()
        if with_toggle:
            # a small header: title on the left, dock/float switch on the right
            self.lb_title = Controles.LB(self, "")
            self.lb_title.setStyleSheet("font-weight: bold; color: #555250;")
            self.bt_toggle = Controles.PB(self, _("Float"), self.toggleRequested.emit, plano=True)
            self.bt_toggle.setToolTip(_("Show the chat in its own window / back in the board"))
            layout.otro(Colocacion.H().control(self.lb_title).relleno().control(self.bt_toggle))

        line = Colocacion.H().control(self.edit).control(self.button)
        layout.control(self.history).otro(line).margen(0)
        self.setLayout(layout)

    def set_title(self, text):
        """Title shown in the header (only present when with_toggle=True)."""
        if getattr(self, "lb_title", None) is not None:
            self.lb_title.setText(text)

    def set_toggle_label(self, floating):
        """Update the button: it offers the *other* mode."""
        if getattr(self, "bt_toggle", None) is not None:
            self.bt_toggle.set_text(_("Dock") if floating else _("Float"))

    # ------------------------------------------------------------------ send
    def send(self):
        text = self.edit.texto().strip()
        if not text:
            return
        self.edit.set_text("")
        self.sendRequested.emit(text)

    # --------------------------------------------------------------- display
    def add_message(self, name, text, own=False):
        """Append a chat bubble.

        My own messages (``own=True``) are shown on the right in blue, the
        rival's on the left in beige; the name and the time go in a small gray
        line above the text.  Only the HTML subset understood by QTextEdit is
        used (tables with bgcolor).
        """
        stamp = time.strftime("%H:%M")
        name = str(name or "")
        body = ""
        if name:
            body += '<font color="%s" size="2">%s &middot; %s</font><br/>' % (
                COLOR_SYS, _escape(name), stamp)
        body += _escape(text).replace("\n", "<br/>")
        color = COLOR_OWN if own else COLOR_OTHER
        if own:
            cells = '<td width="25%%"></td><td bgcolor="%s" align="right">%s</td>' % (color, body)
        else:
            cells = '<td bgcolor="%s" align="left">%s</td><td width="25%%"></td>' % (color, body)
        self.history.append(
            '<table width="100%%" cellspacing="0" cellpadding="4"><tr>%s</tr></table>' % cells
        )
        self._scroll_down()

    def add_system(self, text):
        self.history.append(
            '<center><font color="%s"><i>%s</i></font></center>' % (COLOR_SYS, _escape(text))
        )
        self._scroll_down()

    def clear(self):
        self.history.clear()

    def _scroll_down(self):
        cursor = self.history.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.history.setTextCursor(cursor)
        self.history.ensureCursorVisible()


class ChatWindow(QtWidgets.QWidget):
    """A small, modeless window holding a :class:`ChatPanel`."""

    def __init__(self, parent=None, title="", panel=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setWindowTitle(title)
        self.setWindowIcon(_icon())
        self.panel = panel if panel is not None else ChatPanel(self)
        if panel is not None:
            self.panel.setParent(self)
        self.panel.show()
        self.setLayout(Colocacion.V().control(self.panel).margen(6))
        self.resize(380, 300)

    def set_title(self, title):
        self.setWindowTitle(title)

    def show_up(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        # "closing" only hides it: it is shown again with the next message
        self.hide()
        event.ignore()


class ChatDock(QtCore.QObject):
    """The chat of a game: docked at the left of the board, or floating.

    LucasChess' main window is a ``QDialog`` and not a ``QMainWindow``, so
    there is no ``QDockWidget`` available: in docked mode the panel is simply
    inserted on the left of the layout that holds the board.  If that layout
    cannot be found, it quietly falls back to a floating window.
    """

    DOCKED = "docked"
    FLOATING = "floating"

    def __init__(self, main_window, title, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.title = title
        self.mode = self.DOCKED  # never covers the board by default
        self.window = None
        self._layout = None
        self.panel = ChatPanel(None, min_height=120, with_toggle=True)
        self.panel.set_toggle_label(False)
        self.panel.set_title(title)
        self.panel.toggleRequested.connect(self.toggle)

    # ----------------------------------------------------------------- mode
    def toggle(self):
        self.set_mode(self.FLOATING if self.mode == self.DOCKED else self.DOCKED)

    def set_mode(self, mode):
        if mode == self.mode:
            self.show()
            return
        self._release()
        self.mode = mode
        self.show()

    def is_floating(self):
        return self.mode == self.FLOATING

    def show(self):
        if self.mode == self.FLOATING:
            self._show_floating()
        else:
            self._show_docked()
        self.panel.set_toggle_label(self.mode == self.FLOATING)

    def set_title(self, title):
        self.title = title
        self.panel.set_title(title)
        if self.window is not None:
            self.window.set_title(title)

    def destroy(self):
        self._release()
        if self.window is not None:
            try:
                self.window.deleteLater()
            except Exception:
                pass
            self.window = None
        try:
            self.panel.deleteLater()
        except Exception:
            pass

    # --------------------------------------------------------------- layout
    @staticmethod
    def _is_horizontal(box):
        return isinstance(box, QtWidgets.QBoxLayout) and box.direction() in (
            QtWidgets.QBoxLayout.Direction.LeftToRight,
            QtWidgets.QBoxLayout.Direction.RightToLeft,
        )

    def _target_layout(self):
        mw = self.main_window
        if mw is None:
            return None
        try:
            lay = mw.layout()
        except Exception:
            return None
        if lay is None:
            return None
        if self._is_horizontal(lay):
            return lay
        # vertical layout: use the first horizontal box found one level down
        try:
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item is None:
                    continue
                child = item.layout()
                if self._is_horizontal(child):
                    return child
        except Exception:
            pass
        return None

    def _show_docked(self):
        lay = self._target_layout()
        if lay is None:
            # no suitable place: show it as a window instead of doing nothing
            self.mode = self.FLOATING
            self._show_floating()
            return
        self._layout = lay
        # bounded width: enough to chat, never wide enough to squash the board
        self.panel.setMinimumWidth(240)
        self.panel.setMaximumWidth(300)
        try:
            lay.insertWidget(0, self.panel)
        except Exception:
            self._layout = None
            self.mode = self.FLOATING
            self._show_floating()
            return
        self.panel.show()

    def _show_floating(self):
        if self.window is None:
            self.window = ChatWindow(self.main_window, self.title, panel=self.panel)
        else:
            self.window.set_title(self.title)
        self.panel.setMinimumWidth(0)
        self.panel.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
        self.window.show_up()

    def _release(self):
        """Take the panel out of wherever it is, keeping it alive."""
        if self._layout is not None:
            try:
                self._layout.removeWidget(self.panel)
            except Exception:
                pass
            self._layout = None
        if self.window is not None:
            try:
                self.window.hide()
            except Exception:
                pass
        try:
            self.panel.setParent(None)
        except Exception:
            pass


class LanChatRoom(QtCore.QObject):
    """Chat room shared by everybody on the local network (UDP broadcast).

    It uses the same UDP port as the game discovery; both simply ignore the
    datagrams they do not understand.
    """

    #: (name, text) of a message written by somebody else
    messageReceived = QtCore.Signal(str, str)
    #: name of somebody who is in the room
    peerSeen = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.my_id = uuid.uuid4().hex
        self.my_name = ""
        self.udp = QtNetwork.QUdpSocket(self)
        self._bound = False

    # ----------------------------------------------------------------- start
    def start(self, name):
        self.my_name = name or ""
        if not self._bound:
            flags = (
                QtNetwork.QUdpSocket.BindFlag.ShareAddress
                | QtNetwork.QUdpSocket.BindFlag.ReuseAddressHint
            )
            ok = self.udp.bind(
                QtNetwork.QHostAddress.Any, P.DEFAULT_UDP_PORT, flags
            )
            if not ok:
                ok = self.udp.bind(QtNetwork.QHostAddress.Any, P.DEFAULT_UDP_PORT)
            if ok:
                self.udp.readyRead.connect(self._on_ready_read)
                self._bound = True

    def stop(self):
        try:
            self.udp.readyRead.disconnect(self._on_ready_read)
        except Exception:
            pass
        try:
            self.udp.close()
        except Exception:
            pass
        self._bound = False

    # ------------------------------------------------------------------ send
    def send(self, text):
        text = (text or "").strip()
        if not text:
            return
        msg = P.msg_chat(text, self.my_name)
        msg["id"] = self.my_id
        try:
            self.udp.writeDatagram(
                P.encode(msg), QtNetwork.QHostAddress.Broadcast, P.DEFAULT_UDP_PORT
            )
        except Exception:
            pass

    # ----------------------------------------------------------------- slots
    def _on_ready_read(self):
        while self.udp.hasPendingDatagrams():
            try:
                datagram = self.udp.receiveDatagram()
            except Exception:
                return
            sender = datagram.senderAddress()
            ip = sender.toString().replace("::ffff:", "") if sender is not None else ""
            messages, _rest = P.decode(bytes(datagram.data()))
            for msg in messages:
                if not isinstance(msg, dict) or msg.get("t") != P.CHAT:
                    continue
                if msg.get("id") == self.my_id:
                    continue  # our own message
                name = str(msg.get("name", "")).strip() or ip
                text = str(msg.get("text", ""))
                self.peerSeen.emit(name)
                self.messageReceived.emit(name, text)
