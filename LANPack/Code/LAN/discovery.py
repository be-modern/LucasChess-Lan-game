# -*- coding: utf-8 -*-
"""Automatic discovery of games on the local network (UDP broadcast).

Hosts advertise themselves once per second, clients listen and keep a small
list of the games seen during the last few seconds.  Manual connection (host
name / IP + port) is always available as a fallback.
"""

import uuid

from PySide6 import QtCore, QtNetwork

from Code.LAN import protocol as P

# how long a discovered game stays in the list without being refreshed
ALIVE_SECONDS = 5


def _any_address():
    return QtNetwork.QHostAddress.Any


def _broadcast_address():
    return QtNetwork.QHostAddress.Broadcast


def local_addresses():
    """IPv4 addresses of this computer (useful to tell the host its own IP)."""
    out = []
    try:
        for address in QtNetwork.QNetworkInterface.allAddresses():
            if address.protocol() != QtNetwork.QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                continue
            txt = address.toString()
            if txt.startswith("127."):
                continue
            out.append(txt)
    except Exception:
        pass
    return out


class LanDiscovery(QtCore.QObject):
    """Advertise a game (host mode) or scan for games (client mode)."""

    changed = QtCore.Signal()

    MODE_NONE = "none"
    MODE_HOST = "host"
    MODE_CLIENT = "client"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_id = uuid.uuid4().hex
        self.mode = self.MODE_NONE
        self.udp = QtNetwork.QUdpSocket(self)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer)
        self.games = {}  # key "ip:port" -> {name, ip, port, ts}
        self.advertise_name = ""
        self.advertise_port = 0
        self._bound = False

    # ------------------------------------------------------------------ bind
    def _bind(self):
        if self._bound:
            return True
        flags = QtNetwork.QUdpSocket.BindFlag.ShareAddress | QtNetwork.QUdpSocket.BindFlag.ReuseAddressHint
        ok = self.udp.bind(_any_address(), P.DEFAULT_UDP_PORT, flags)
        if not ok:
            # second try without any flag (some systems are more restrictive)
            ok = self.udp.bind(_any_address(), P.DEFAULT_UDP_PORT)
        if ok:
            self.udp.readyRead.connect(self._on_ready_read)
            self._bound = True
        return ok

    # ------------------------------------------------------------------ host
    def start_advertise(self, name, port):
        self.stop()
        self.mode = self.MODE_HOST
        self.advertise_name = name
        self.advertise_port = port
        self._bind()
        self._advertise()
        self.timer.start()

    # ---------------------------------------------------------------- client
    def start_scan(self):
        self.stop()
        self.mode = self.MODE_CLIENT
        self.games = {}
        self._bind()
        self.timer.start()
        self.changed.emit()

    def stop(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        self.mode = self.MODE_NONE
        for data in list(self.games.values()):
            data["ts"] = 0
        self.games = {}

    # ----------------------------------------------------------------- utils
    def game_list(self):
        """[(ip, port, name)] sorted by name."""
        out = [(d["ip"], d["port"], d["name"]) for d in self.games.values()]
        out.sort(key=lambda x: x[2].lower())
        return out

    def _advertise(self):
        try:
            data = P.encode(P.msg_advertise(self.game_id, self.advertise_name, self.advertise_port))
            self.udp.writeDatagram(data, _broadcast_address(), P.DEFAULT_UDP_PORT)
        except Exception:
            pass

    # ----------------------------------------------------------------- slots
    def _on_timer(self):
        if self.mode == self.MODE_HOST:
            self._advertise()
        elif self.mode == self.MODE_CLIENT:
            self._purge()

    def _purge(self):
        now = QtCore.QDateTime.currentMSecsSinceEpoch()
        before = len(self.games)
        for key in list(self.games.keys()):
            if now - self.games[key]["ts"] > ALIVE_SECONDS * 1000:
                del self.games[key]
        if len(self.games) != before:
            self.changed.emit()

    def _on_ready_read(self):
        while self.udp.hasPendingDatagrams():
            try:
                datagram = self.udp.receiveDatagram()
            except Exception:
                return
            data = bytes(datagram.data())
            sender = datagram.senderAddress()
            if sender is None:
                continue
            ip = sender.toString()
            try:
                ip = ip.replace("::ffff:", "")
            except Exception:
                pass
            messages, _rest = P.decode(data)
            for msg in messages:
                if not isinstance(msg, dict) or msg.get("t") != P.ADVERTISE:
                    continue
                if msg.get("id") == self.game_id:
                    continue  # our own advertisement
                try:
                    port = int(msg.get("port", P.DEFAULT_TCP_PORT))
                except Exception:
                    port = P.DEFAULT_TCP_PORT
                key = "%s:%d" % (ip, port)
                self.games[key] = {
                    "ip": ip,
                    "port": port,
                    "name": str(msg.get("name", "")) or ip,
                    "ts": QtCore.QDateTime.currentMSecsSinceEpoch(),
                }
                self.changed.emit()
