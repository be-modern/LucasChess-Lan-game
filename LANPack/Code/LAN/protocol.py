# -*- coding: utf-8 -*-
"""Wire protocol used between the two LucasChess instances.

Messages are JSON objects, one per line, encoded in UTF-8.  Using a line
oriented protocol keeps the framing trivial and makes the extension usable
even between different LucasChessR builds.
"""

import json

PROTO_NAME = "LucasChessLAN"
PROTO_VERSION = 1

SEP = b"\n"

#: TCP port used by default when hosting a game.
DEFAULT_TCP_PORT = 46217
#: UDP port used to advertise / discover games on the local network.
DEFAULT_UDP_PORT = 46218

# message types
HELLO = "hello"
CONFIG = "config"
MOVE = "move"
RESIGN = "resign"
DRAW_OFFER = "draw_offer"
DRAW_ACCEPT = "draw_accept"
DRAW_DECLINE = "draw_decline"
CHAT = "chat"
BYE = "bye"
ADVERTISE = "advertise"  # UDP only


def encode(msg):
    """dict -> bytes (with the trailing separator)."""
    return (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")


def decode(chunk):
    """bytes -> (list_of_messages, remaining_bytes)."""
    messages = []
    while True:
        pos = chunk.find(SEP)
        if pos < 0:
            break
        raw, chunk = chunk[:pos], chunk[pos + 1:]
        raw = raw.strip()
        if not raw:
            continue
        try:
            messages.append(json.loads(raw.decode("utf-8")))
        except Exception:
            # a malformed frame never breaks the game
            continue
    return messages, chunk


def msg_hello(name):
    return {"t": HELLO, "name": name, "v": PROTO_VERSION}


def msg_config(white, black, minutes, seconds, timed, you_white):
    return {
        "t": CONFIG,
        "white": white,
        "black": black,
        "minutes": minutes,
        "seconds": seconds,
        "timed": timed,
        "you_white": you_white,
    }


def msg_move(uci):
    return {"t": MOVE, "uci": uci}


def msg_resign():
    return {"t": RESIGN}


def msg_draw_offer():
    return {"t": DRAW_OFFER}


def msg_draw_accept():
    return {"t": DRAW_ACCEPT}


def msg_draw_decline():
    return {"t": DRAW_DECLINE}


def msg_chat(text, name=""):
    """A chat message.  ``name`` is needed for the broadcast chat room."""
    msg = {"t": CHAT, "text": text}
    if name:
        msg["name"] = name
    return msg


def msg_bye():
    return {"t": BYE}


def msg_advertise(game_id, name, port):
    return {"t": ADVERTISE, "id": game_id, "name": name, "port": port}
