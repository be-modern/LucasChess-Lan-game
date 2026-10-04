# -*- coding: utf-8 -*-
"""TCP transport for a LAN game.

Everything is built on top of Qt sockets, so no thread is needed: the
LucasChess event loop drives the communication and the Qt signals are emitted
in the GUI thread, which is exactly what the game manager needs.
"""

from PySide6 import QtCore, QtNetwork

from Code.LAN import protocol as P


class LanLink(QtCore.QObject):
    """A bidirectional, message oriented connection with the opponent."""

    # --- signals emitted when something arrives from the other side ---------
    helloReceived = QtCore.Signal(object)
    configReceived = QtCore.Signal(object)
    moveReceived = QtCore.Signal(str)
    resignReceived = QtCore.Signal()
    drawOfferReceived = QtCore.Signal()
    drawAccepted = QtCore.Signal()
    drawDeclined = QtCore.Signal()
    chatReceived = QtCore.Signal(str)
    byeReceived = QtCore.Signal()
    disconnected = QtCore.Signal()

    def __init__(self, socket, parent=None):
        super().__init__(parent)
        self.socket = socket
        self.buffer = b""
        self.rival_name = ""
        self._closed = False

        socket.setParent(self)
        socket.readyRead.connect(self._on_ready_read)
        socket.disconnected.connect(self._on_disconnected)
        try:
            socket.errorOccurred.connect(self._on_error)
        except Exception:
            pass

    # ------------------------------------------------------------------ info
    def is_connected(self):
        try:
            return self.socket.state() == QtNetwork.QAbstractSocket.SocketState.ConnectedState
        except Exception:
            return False

    def peer_address(self):
        try:
            return self.socket.peerAddress().toString()
        except Exception:
            return ""

    # ------------------------------------------------------------------ send
    def send(self, msg):
        if self._closed:
            return False
        try:
            if not self.is_connected():
                return False
            self.socket.write(P.encode(msg))
            self.socket.flush()
            return True
        except Exception:
            return False

    def send_hello(self, name):
        return self.send(P.msg_hello(name))

    def send_config(self, white, black, minutes, seconds, timed, you_white):
        return self.send(P.msg_config(white, black, minutes, seconds, timed, you_white))

    def send_move(self, uci):
        return self.send(P.msg_move(uci))

    def send_resign(self):
        return self.send(P.msg_resign())

    def send_draw_offer(self):
        return self.send(P.msg_draw_offer())

    def send_draw_accept(self):
        return self.send(P.msg_draw_accept())

    def send_draw_decline(self):
        return self.send(P.msg_draw_decline())

    def send_chat(self, text, name=""):
        return self.send(P.msg_chat(text, name))

    # ----------------------------------------------------------------- close
    def close(self, say_bye=True):
        if self._closed:
            return
        self._closed = True
        if say_bye:
            try:
                if self.is_connected():
                    self.socket.write(P.encode(P.msg_bye()))
                    self.socket.flush()
            except Exception:
                pass
        try:
            self.socket.disconnected.disconnect(self._on_disconnected)
        except Exception:
            pass
        try:
            if self.is_connected():
                self.socket.disconnectFromHost()
            self.socket.close()
        except Exception:
            pass

    # ----------------------------------------------------------------- slots
    def _on_ready_read(self):
        try:
            data = bytes(self.socket.readAll())
        except Exception:
            return
        if not data:
            return
        self.buffer += data
        messages, self.buffer = P.decode(self.buffer)
        for msg in messages:
            self.dispatch(msg)

    def dispatch(self, msg):
        if not isinstance(msg, dict):
            return
        kind = msg.get("t")
        if kind == P.MOVE:
            self.moveReceived.emit(str(msg.get("uci", "")))
        elif kind == P.RESIGN:
            self.resignReceived.emit()
        elif kind == P.DRAW_OFFER:
            self.drawOfferReceived.emit()
        elif kind == P.DRAW_ACCEPT:
            self.drawAccepted.emit()
        elif kind == P.DRAW_DECLINE:
            self.drawDeclined.emit()
        elif kind == P.CHAT:
            self.chatReceived.emit(str(msg.get("text", "")))
        elif kind == P.BYE:
            self.byeReceived.emit()
        elif kind == P.HELLO:
            self.rival_name = str(msg.get("name", ""))
            self.helloReceived.emit(msg)
        elif kind == P.CONFIG:
            self.configReceived.emit(msg)

    def _on_disconnected(self):
        self.disconnected.emit()

    def _on_error(self, *args):
        # A socket error always ends up as a disconnection for us.
        pass


class LanServer(QtCore.QObject):
    """Tiny wrapper around QTcpServer that emits ready to use LanLink objects."""

    clientConnected = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = QtNetwork.QTcpServer(self)
        self.server.newConnection.connect(self._on_new_connection)

    def listen(self, port, host=None):
        address = host if host is not None else QtNetwork.QHostAddress.Any
        return self.server.listen(address, port)

    def error_string(self):
        try:
            return self.server.errorString()
        except Exception:
            return ""

    def port(self):
        try:
            return self.server.serverPort()
        except Exception:
            return 0

    def close(self):
        try:
            self.server.close()
        except Exception:
            pass

    def _on_new_connection(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                return
            # only one game per host
            self.server.close()
            self.clientConnected.emit(LanLink(socket, self))


def connect_to_host(host, port, parent=None):
    """Create a LanLink and start an asynchronous connection to *host*."""
    socket = QtNetwork.QTcpSocket()
    link = LanLink(socket, parent)
    socket.connectToHost(host, port)
    return link
