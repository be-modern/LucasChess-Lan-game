# -*- coding: utf-8 -*-
"""Game manager for a LAN game.

It inherits from the original ``ManagerPlayHuman`` (human vs human on the same
computer) and simply replaces "the other human sitting next to you" with "the
other LucasChess over the network":

* when it is our turn the board behaves exactly as usual;
* when it is the rival's turn the board is locked and we wait for the move;
* every local move is sent to the rival, every received move is replayed
  through the standard dispatcher so that clocks, arrows, sounds and PGN keep
  working exactly like in a normal game.
"""

from Code.Base.Constantes import (
    RESULT_DRAW,
    RESULT_WIN_BLACK,
    RESULT_WIN_WHITE,
    ST_ENDGAME,
    ST_PLAYING,
    TB_DRAW,
    TB_REINIT,
    TB_RESIGN,
    TB_TAKEBACK,
    TERMINATION_DRAW_AGREEMENT,
    TERMINATION_RESIGN,
)
from Code.LAN import tr as _
from Code.PlayHuman.ManagerPlayHuman import ManagerPlayHuman
from Code.QT import QTMessages
from Code.Z import Adjournments


class ManagerPlayLAN(ManagerPlayHuman):
    def __init__(self, procesador):
        super().__init__(procesador)
        self.lan = None
        self.lan_is_white = True
        self.lan_rival_name = ""
        self._lan_applying_remote = False
        self._lan_chat = None
        self._lan_my_name = ""

    # ------------------------------------------------------------------ setup
    def set_link(self, link, is_white, rival_name=""):
        self.lan = link
        self.lan_is_white = bool(is_white)
        self.lan_rival_name = rival_name
        link.moveReceived.connect(self.lan_move)
        link.resignReceived.connect(self.lan_resign)
        link.drawOfferReceived.connect(self.lan_draw_offer)
        link.drawAccepted.connect(self.lan_draw_accepted)
        link.drawDeclined.connect(self.lan_draw_declined)
        link.chatReceived.connect(self.lan_chat)
        link.byeReceived.connect(self.lan_rival_left)
        link.disconnected.connect(self.lan_disconnected)

    def start(self, dic_var):
        link = dic_var.get("LAN_LINK")
        is_white = bool(dic_var.get("LAN_IS_WHITE", True))
        rival = dic_var.get("LAN_RIVAL", "")
        if link is not None:
            self.set_link(link, is_white, rival)
        super().start(dic_var)
        # a LAN game has no takeback and no "restart": both would desync
        self.with_takeback = False
        self.pon_toolbar()
        try:
            self.board.set_side_bottom(self.lan_is_white)
        except Exception:
            pass
        self._lan_my_name = (dic_var.get("WHITE") if is_white else dic_var.get("BLACK")) or ""
        self.open_chat_window()

    # ------------------------------------------------------------------ chat
    def chat_window(self):
        """The chat of this game: docked at the left of the board by default."""
        if self._lan_chat is None:
            from Code.LAN import chat

            rival = self.lan_rival_name or _("Opponent")
            dock = chat.ChatDock(self.main_window, _("Chat with %s") % rival)
            dock.panel.sendRequested.connect(self.lan_send_chat)
            self._lan_chat = dock
        return self._lan_chat

    def open_chat_window(self):
        """Show the chat without ever covering the board."""
        try:
            self.chat_window().show()
        except Exception:
            pass

    def lan_send_chat(self, text):
        if not text or self.lan is None:
            return
        self.lan.send_chat(text, self._lan_my_name)
        if self._lan_chat is not None:
            self._lan_chat.panel.add_message(self._lan_my_name or _("You"), text, own=True)

    def lan_chat(self, text):
        """A message written by the rival."""
        try:
            dock = self.chat_window()
            dock.panel.add_message(self.lan_rival_name or _("Opponent"), text)
            dock.show()
        except Exception:
            pass

    def _close_chat_window(self):
        dock = self._lan_chat
        self._lan_chat = None
        if dock is None:
            return
        try:
            dock.panel.sendRequested.disconnect(self.lan_send_chat)
        except Exception:
            pass
        # takes the panel out of the board layout again
        try:
            dock.destroy()
        except Exception:
            pass

    # ---------------------------------------------------------------- toolbar
    def set_toolbar(self, li_options):
        li_options = [k for k in li_options if k not in (TB_TAKEBACK, TB_REINIT)]
        super().set_toolbar(li_options)

    def takeback(self):
        QTMessages.message(self.main_window, _("Takeback is not available in a network game"))

    def reiniciar(self, to_ask=True):
        QTMessages.message(self.main_window, _("Restart is not available in a network game"))

    # ------------------------------------------------------------------ turns
    def is_my_turn(self):
        try:
            return self.game.is_white() == self.lan_is_white
        except Exception:
            return False

    def play_human(self, is_white):
        if is_white == self.lan_is_white:
            # our turn: normal behaviour
            super().play_human(is_white)
            return
        # rival's turn: keep the clocks running but lock the board
        tc = self.tc_white if is_white else self.tc_black
        try:
            tc.start()
        except Exception:
            pass
        self.pon_toolbar()
        try:
            self.board.set_side_bottom(self.lan_is_white)
        except Exception:
            pass
        self.is_human_side_white = is_white
        self.human_is_playing = False
        self.stop_human()

    # ------------------------------------------------------------------ moves
    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        remote = self._lan_applying_remote
        if not remote:
            if self.state != ST_PLAYING or not self.is_my_turn():
                return False
            ok = super().player_has_moved_dispatcher(from_sq, to_sq, promotion)
            if ok and self.lan is not None:
                uci = from_sq + to_sq + (promotion.lower() if promotion else "")
                self.lan.send_move(uci)
            return ok
        return super().player_has_moved_dispatcher(from_sq, to_sq, promotion)

    def lan_move(self, uci):
        """A move arrived from the rival."""
        uci = (uci or "").strip()
        if len(uci) < 4:
            return
        if self.state != ST_PLAYING:
            return
        if self.is_my_turn():
            return  # not the rival's turn, ignore
        from_sq, to_sq, promotion = uci[:2], uci[2:4], uci[4:5]
        previous = self.human_is_playing
        self.human_is_playing = True
        self._lan_applying_remote = True
        try:
            self.player_has_moved_dispatcher(from_sq, to_sq, promotion)
        finally:
            self._lan_applying_remote = False
            self.human_is_playing = previous

    # ---------------------------------------------------------------- results
    def finish_lan_game(self):
        if self.state == ST_ENDGAME:
            return
        try:
            self.autosave()
        except Exception:
            pass
        try:
            self.show_result()
        except Exception:
            pass
        try:
            self.set_end_game(False)
        except Exception:
            pass

    def run_action(self, key):
        if key == TB_RESIGN:
            self.lan_resign_local()
            return
        if key == TB_DRAW:
            self.lan_draw_offer_local()
            return
        super().run_action(key)

    def lan_resign_local(self):
        if self.state == ST_ENDGAME:
            return
        if not QTMessages.pregunta(self.main_window, _("Do you want to resign?")):
            return
        if self.lan is not None:
            self.lan.send_resign()
        try:
            self.game.set_termination(
                TERMINATION_RESIGN, RESULT_WIN_BLACK if self.lan_is_white else RESULT_WIN_WHITE
            )
        except Exception:
            pass
        self.finish_lan_game()

    def lan_resign(self):
        """The rival resigned."""
        if self.state == ST_ENDGAME:
            return
        try:
            self.game.set_termination(
                TERMINATION_RESIGN, RESULT_WIN_WHITE if self.lan_is_white else RESULT_WIN_BLACK
            )
        except Exception:
            pass
        self.finish_lan_game()

    def lan_draw_offer_local(self):
        if self.state == ST_ENDGAME:
            return
        if self.lan is not None:
            self.lan.send_draw_offer()
        QTMessages.message(self.main_window, _("Draw offered, waiting for the answer"))

    def lan_draw_offer(self):
        """The rival offers a draw."""
        if self.state == ST_ENDGAME:
            return
        rival = self.lan_rival_name or _("Opponent")
        if QTMessages.pregunta(self.main_window, _("%s offers a draw. Do you accept?") % rival):
            if self.lan is not None:
                self.lan.send_draw_accept()
            self.lan_apply_draw()
        else:
            if self.lan is not None:
                self.lan.send_draw_decline()

    def lan_draw_accepted(self):
        QTMessages.message(self.main_window, _("Draw accepted"))
        self.lan_apply_draw()

    def lan_draw_declined(self):
        QTMessages.message(self.main_window, _("Draw declined"))

    def lan_apply_draw(self):
        if self.state == ST_ENDGAME:
            return
        try:
            jg = self.game.last_jg()
            if jg is not None:
                jg.is_draw_agreement = True
        except Exception:
            pass
        try:
            self.game.set_termination(TERMINATION_DRAW_AGREEMENT, RESULT_DRAW)
        except Exception:
            pass
        self.finish_lan_game()

    # ------------------------------------------------------------ disconnection
    def lan_rival_left(self):
        self.lan_disconnected()

    def lan_adjourn(self):
        """Store the current game as an adjournment (no question asked).

        The rival is gone, but the game is worth keeping: it is saved exactly
        like the original "adjourn" command does, so it can be resumed later
        from the adjournments menu (locally, against an engine, ...).
        """
        if self.state == ST_ENDGAME:
            return False
        try:
            dic = self.save_state()
        except Exception:
            return False

        white = getattr(self, "white", "") or ""
        black = getattr(self, "black", "") or ""
        if not white or not black:
            try:
                white = self.game.get_tag("WHITE") or white
                black = self.game.get_tag("BLACK") or black
            except Exception:
                pass
        label = "%s. %s - %s" % (_("Local network game"), white, black)

        # End the game the way the original code does, *without* asking
        # anything and *without* showing the result.  It is important to do it
        # before storing: the original ``finalizar()`` returns immediately when
        # the state is already ST_ENDGAME, and then the toolbar is never
        # updated - leaving the player locked on the board with no way out.
        self._end_game_silently()

        saved = False
        try:
            with Adjournments.Adjournments() as adj:
                adj.add(self.game_type, dic, label)
            saved = True
        except Exception:
            saved = False
        return saved

    def _end_game_silently(self):
        """Stop the clocks and turn the toolbar into its "game over" state."""
        try:
            if self.timed and self.main_window is not None:
                self.main_window.stop_clock()
                self.show_clocks()
        except Exception:
            pass
        self.state = ST_ENDGAME
        try:
            self.game.set_unknown()
        except Exception:
            pass
        try:
            self.set_end_game(self.with_takeback)
        except Exception:
            pass
        try:
            self.autosave()
        except Exception:
            pass

    def lan_disconnected(self):
        if self.state == ST_ENDGAME:
            return
        self.lan_close(say_bye=False)
        if self.lan_adjourn():
            QTMessages.message(
                self.main_window,
                _("The connection with your opponent has been lost.")
                + "\n\n"
                + _("The game has been adjourned: you can resume it from the adjournments menu."),
            )
        else:
            QTMessages.message_error(
                self.main_window, _("The connection with your opponent has been lost")
            )
        self.finish_lan_game()

    # ------------------------------------------------------------------ closing
    def lan_close(self, say_bye=True):
        link = self.lan
        self.lan = None
        self._close_chat_window()
        if link is None:
            return
        try:
            link.moveReceived.disconnect(self.lan_move)
            link.resignReceived.disconnect(self.lan_resign)
            link.drawOfferReceived.disconnect(self.lan_draw_offer)
            link.drawAccepted.disconnect(self.lan_draw_accepted)
            link.drawDeclined.disconnect(self.lan_draw_declined)
            link.chatReceived.disconnect(self.lan_chat)
            link.byeReceived.disconnect(self.lan_rival_left)
            link.disconnected.disconnect(self.lan_disconnected)
        except Exception:
            pass
        try:
            link.close(say_bye=say_bye)
        except Exception:
            pass

    def finalizar(self):
        self.lan_close()
        super().finalizar()

    def close(self):
        self.lan_close()
        super().close()
