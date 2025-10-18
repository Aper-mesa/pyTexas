from random import choice  # For choosing the host
from random import shuffle  # For shuffling the deck of cards

import pygame
import imgui
from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT, glClearColor

import card  # Import the Card class for creating card instances
import config  # Import configuration with card type/rank definitions


class CardPool:
    """Represents a pool/deck of playing cards used in the game.
    Manages card creation, shuffling, and distribution.
    """

    def __init__(self):
        """Initialize a new card pool with a full set of shuffled cards"""
        self.cards = []  # List to hold all cards in the pool

        # Create a complete set of cards by combining all types and numbers
        # Iterate through all possible card types (suits) from configuration
        for cardType in config.CARD_TYPE_MAP:
            # Iterate through all possible card numbers (ranks) from configuration
            for cardNumber in range(2, 15):
                # Create a new Card instance and add to the pool
                self.cards.append(card.Card(cardType, cardNumber))

        # Shuffle the cards to randomize their order
        shuffle(self.cards)

    def __iter__(self):
        """Make the CardPool iterable.

        Returns:
            An iterator over the cards in the pool
        """
        return iter(self.cards)

    def __next__(self):
        """Get the next card from the pool (by removing and returning it).
        Implements iterator protocol for sequential card drawing.
        """
        return self.cards.pop()

    def __len__(self):
        """Get the current number of cards remaining in the pool.

        Returns:
            Integer count of remaining cards
        """
        return len(self.cards)

    def getNextCard(self):
        """Draw the next card from the pool (removes and returns it).

        Returns:
            The next Card instance from the pool
        """
        return self.cards.pop()

    def getTopThreeCards(self):
        """Get the first three cards from the pool without removing them.

        Returns:
            A list containing the first three Card instances
        """
        return self.cards[:3]


from typing import List, Dict, Optional, Iterable


class Round:
    """
    Texas Hold'em turn-order helper.

    Assumptions:
      - `players` is the clockwise seat order.
      - `dealer` (BTN) is an element of `players`.
      - No fold/leave tracking here (pure order only).
    """

    def __init__(self, players, dealer):
        if not players or dealer not in players:
            raise ValueError("players must be non-empty and contain dealer")

        self.players = list(players)
        self.dealer = dealer

        # Cache common seat lookups
        self._n = len(self.players)
        self._idx = {p: i for i, p in enumerate(self.players)}

        # Compute and cache static positions for the hand
        self._pos_map: Dict[str, object] = self._computePositions()

        # Optional iteration state (only if you want to step through a street)
        self._street: Optional[str] = None
        self._order: List = []
        self._cursor: int = 0

    def positions(self):
        """
        Returns a mapping of named positions for this hand.
        Keys present depend on player count.

        For 2 players:
          - BTN (also SB) and BB

        For 3+ players:
          - BTN, SB, BB, then a list for early/middle/late seats:
            'UTG' (first seat left of BB), followed by the rest clockwise.
        """
        return dict(self._pos_map)

    def streetOrder(self, street: str):
        """
        Return action order for a given street: 'preflop' | 'flop' | 'turn' | 'river'
        (Flop/Turn/River share postflop rules.)

        Rules:
          - Heads-up:
              preflop: BTN(SB) -> BB
              postflop: BB -> BTN
          - 3+ players:
              preflop: starts left of BB, ends on BB
              postflop: starts left of BTN, ends on BTN
        """
        street = street.lower()
        if street not in ("preflop", "flop", "turn", "river"):
            raise ValueError("street must be one of: preflop, flop, turn, river")

        n = self._n
        BTN = self._pos_map["BTN"]

        if n == 2:
            SB = BTN  # In heads-up, BTN is SB
            BB = self._pos_map["BB"]
            if street == "preflop":
                return [SB, BB]
            else:
                return [BB, SB]

        # n >= 3
        SB = self._pos_map["SB"]
        BB = self._pos_map["BB"]

        if street == "preflop":
            # Start left of BB, wrap around to BB (BB acts last preflop)
            start = self._leftOf(BB)
            order = self._ringFrom(start)
            # Ensure BB is last (ring_from already includes everyone once)
            return order
        else:
            # Postflop streets start left of BTN, BTN acts last
            start = self._leftOf(BTN)
            order = self._ringFrom(start)
            return order

    def setStreet(self, street: str):
        """Prepare internal iterator for a given street."""
        self._street = street
        self._order = self.streetOrder(street)
        self._cursor = 0

    def current(self):
        """Current actor for the prepared street (via set_street)."""
        if not self._order:
            return None
        return self._order[self._cursor]

    def advance(self):
        """Advance to next actor and return them (one loop only)."""
        if not self._order:
            return None
        self._cursor = (self._cursor + 1) % len(self._order)
        return self._order[self._cursor]

    def __iter__(self) -> Iterable:
        """Iterate once through the prepared street order (doesn't modify cursor)."""
        return iter(list(self._order))

    def _computePositions(self) -> Dict[str, object]:
        """
        Compute positional map based on dealer.
        """
        n = self._n
        BTN = self.dealer
        BTN_i = self._idx[BTN]

        def seat(i):  # helper to fetch player by absolute index with wrap
            return self.players[i % n]

        pos = {"BTN": BTN}

        if n == 2:
            # Heads-up: BTN is SB; the other player is BB.
            BB = seat(BTN_i + 1)
            pos["SB"] = BTN
            pos["BB"] = BB
            return pos

        # 3+ players
        SB = seat(BTN_i + 1)
        BB = seat(BTN_i + 2)
        pos["SB"] = SB
        pos["BB"] = BB

        # Build UTG and the remaining seats (everything left of BB through back to BTN)
        ring_from_utg = self._ringFrom(self._leftOf(BB))
        # ring_from_utg ends at BTN; first element is UTG
        if ring_from_utg:
            pos["UTG"] = ring_from_utg[0]
            # You can inspect the rest via street_order; we don't name all (UTG+1, HJ, CO) here.
        return pos

    def _leftOf(self, player):
        """Next clockwise seat."""
        i = self._idx[player]
        return self.players[(i + 1) % self._n]

    def _ringFrom(self, starter) -> List:
        """Return a single full clockwise loop starting from `starter`."""
        s = self._idx[starter]
        return self.players[s:] + self.players[:s]

    @classmethod
    def createNextRound(cls, previous_round):
        """
        Create a new round with the given previous round.
        """
        players = previous_round.players
        current_dealer = previous_round.dealer
        current_index = previous_round._idx[current_dealer]
        next_index = (current_index + 1) % len(players)
        new_dealer = players[next_index]
        return cls(players, new_dealer)


class Room:
    """Manages a game room where players participate in rounds, place bets, and compete.
    Handles game state, player interactions, betting pools, and round progression.
    """

    def __init__(self, data):
        self.players = data[0]  # 房间中的所有人，从房主创房那边直接传递过来
        self.activePlayers = self.players  # 在打牌的人，弃牌了就不在这了，初始和players一样
        self.numPlayers = len(self.players)
        self.minBet = data[1]  # 最小下注数额
        self.initBet = data[2]  # 所有人的入局赌注数额
        self.banker = choice(self.players)  # 首次随机选一个作为庄家
        self.order = Round(self.players, self.banker)  # Manages turn order for the round
        self.betPool = 0  # Total accumulated bets in the current round
        self.lastChip = 0
        self.cards = CardPool()
        self.publicCardPool = [None] * 5

    def getDealerAndTwoPartners(self):
        positions = self.order.positions()
        ret = {}
        for position in positions:
            if position in ("BB", "SB", "BTN"):
                player = positions[position]
                ip = player.steam_id
                ret[ip] = position
        return ret

    def chipIn(self, player, bet):
        """Process a player's bet and add it to the pool

        Args:
            player: Player instance placing the bet.
            bet: Amount the player wants to bet

        Returns:
            bool: True if bet is successful, False if insufficient funds
        """
        playerInGame = self.activePlayers[player]  # Get player's in-game state

        if bet < self.lastChip:
            return False

        # Check if player has enough remaining bet capacity
        if playerInGame.currentBet < bet:
            return False

        # Deduct bet from player's available amount and add to pool
        playerInGame.currentBet -= bet
        self.betPool += bet
        self.lastChip = bet
        return True

    def deliverCards(self):
        self.order.setStreet("flop")
        for i in range(2):
            for player in self.order:
                card = self.cards.getNextCard()
                player.handCards.append(card)

    def addCardToPublicPool(self):
        if not None in self.publicCardPool:
            return False
        place = self.publicCardPool.index(None)
        card = self.cards.getNextCard()
        self.publicCardPool[place] = card
        return True

    def endOfRound(self):
        """Handle the end of a round, determine the winner, and distribute winnings

        Returns:
            bool: True if round ends successfully, False if multiple players remain
        """
        # Round can only end if one player remains
        if len(self.activePlayers.values()) > 1:
            return False

        # Get the remaining player as winner
        winnerKey = list(self.activePlayers.keys())[0]
        winner = self.activePlayers[winnerKey]

        # Update winner's money: deduct unused bet capacity, add total pool
        winner.player.money += self.betPool
        winner.player.storeData()  # Save updated balance to storage

        # Reset winner's hand for next round
        winner.handCards = []
        return True

    def playerQuitRound(self, p):
        """Handle a player quitting the current round

        Args:
            p: PlayerInGame instance quitting the round

        Returns:
            bool: True if player is successfully removed
        """
        # Remove player from current round
        self.activePlayers.pop(p)

        # Deduct their committed bet from their balance
        p.player.money -= p.currentBet
        p.player.storeData()  # Save updated balance

        # Reset their hand
        p.handCards = []

    def newRound(self):
        """Initialize a new round, resetting game state while keeping room players"""
        self.activePlayers = self.players

        # Advance to next round order (likely rotating turns)
        self.order = Round.createNextRound(self.order)
        self.betPool = 0  # Clear the betting pool
        self.banker = self.order.positions()["BTN"]  # Update host to button position (likely dealer)
        self.cards = CardPool()


class PlayScreen:
    def __init__(self, screen, impl, room, localPlayer):
        self.screen = screen
        self.impl = impl  # 保持变量名一致性，renderer 即 impl
        self.clock = pygame.time.Clock()
        self.screen_width, self.screen_height = screen.get_size()

        self.room = room
        self.player = localPlayer

    def run(self):
        while True:
            # --- 事件处理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "STATE_QUIT"
                self.impl.process_event(event)

            # --- ImGui 新一帧 ---
            self.impl.process_inputs()
            imgui.new_frame()

            # --- 绘制所有UI元素 ---
            self.draw_ui()

            # --- 渲染 ---
            # 仿照 Login.py，使用 OpenGL 清屏，解决画面残留问题
            # 设置清屏颜色 (R, G, B, A)，这里将 (20, 20, 20) 转换到 0-1 范围
            glClearColor(20 / 255.0, 20 / 255.0, 20 / 255.0, 1.0)
            # 执行清屏
            glClear(GL_COLOR_BUFFER_BIT)

            imgui.render()
            self.impl.render(imgui.get_draw_data())
            pygame.display.flip()

            self.clock.tick(60)

    def draw_ui(self):
        """在每一帧绘制所有 ImGui 界面元素"""
        # 创建一个覆盖全屏的、不可交互的背景窗口
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(self.screen_width, self.screen_height)
        imgui.begin(
            "PlayScreenBackground",
            flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE |
                  imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE |
                  imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
        )

        # 调用各个部分的绘制函数
        self._draw_players_list()
        self._draw_info_display()
        self._draw_public_cards()
        self._draw_player_hand()
        self._draw_action_buttons()

        imgui.end()

    def _draw_players_list(self):
        """绘制左上角的玩家列表"""
        container_width = self.screen_width * 0.25
        container_height = self.screen_height * 0.5

        imgui.set_next_window_position(20, 20)
        imgui.set_next_window_size(container_width, container_height)

        imgui.begin("Players", flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE)

        imgui.text("Players in Room")
        imgui.separator()

        players = self.room.activePlayers
        positions = self.room.getDealerAndTwoPartners()

        for player in players:
            player_info = f"{player.username} | Chips: {player.money}"
            player_id_str = str(player.steam_id)

            if player_id_str in positions:
                player_info = f"({positions[player_id_str]}) {player_info}"

            imgui.text(player_info)
            imgui.spacing()

        imgui.end()

    def _draw_info_display(self):
        """绘制右上角的个人筹码和总奖池信息"""
        info_width = self.screen_width * 0.2
        info_height = 80

        imgui.set_next_window_position(self.screen_width - info_width - 20, 20)
        imgui.set_next_window_size(info_width, info_height)

        imgui.begin("Game Info", flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_TITLE_BAR)

        chips_text = f"Your Chips: {self.player.money} $"
        pot_text = f"Total Pot: {self.room.betPool} $"

        imgui.text(chips_text)
        imgui.text(pot_text)

        imgui.end()

    def _draw_public_cards(self):
        """绘制桌子中间的公共牌"""
        card_width = 64
        card_height = int(card_width * 1.4)
        spacing = 12
        num_cards = 5

        total_width = (card_width * num_cards) + (spacing * (num_cards - 1))
        start_x = (self.screen_width - total_width) / 2
        y = (self.screen_height - card_height) / 2

        public_cards = self.room.publicCardPool

        # 创建一个无边框、无背景的窗口来容纳这些牌，以便精确定位
        imgui.set_next_window_position(start_x, y)
        imgui.set_next_window_size(total_width * 1.2, card_height * 2)
        imgui.begin("PublicCardsContainer",
                    flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BACKGROUND | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE)

        for i in range(num_cards):
            if i > 0:
                imgui.same_line(spacing=spacing)

            imgui.begin_child(f"public_card_{i}", width=card_width, height=card_height, border=True)

            card_text = "?"
            if i < len(public_cards) and public_cards[i]:
                card_text = str(public_cards[i])

            text_width, text_height = imgui.calc_text_size(card_text)
            imgui.set_cursor_pos(((card_width - text_width) / 2, (card_height - text_height) / 2))
            imgui.text(card_text)

            imgui.end_child()

        imgui.end()

    def _draw_player_hand(self):
        """绘制屏幕下方的玩家手牌"""
        slot_width = 70
        slot_height = int(slot_width * 1.4)
        spacing = 12
        num_cards = 2

        total_width = (slot_width * num_cards) + spacing
        start_x = (self.screen_width - total_width) / 2
        start_y = self.screen_height - slot_height - 80  # 向上移动一点为按钮留空间

        imgui.set_next_window_position(start_x, start_y)
        imgui.set_next_window_size(total_width * 1.2, slot_height * 2)
        imgui.begin("PlayerHandContainer",
                    flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BACKGROUND | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE)

        for i in range(num_cards):
            if i > 0:
                imgui.same_line(spacing=spacing)

            imgui.begin_child(f"hand_card_{i}", width=slot_width, height=slot_height, border=True)

            card_text = "*"
            if i < len(self.player.handCards) and self.player.handCards[i]:
                card_text = str(self.player.handCards[i])

            text_width, text_height = imgui.calc_text_size(card_text)
            imgui.set_cursor_pos(((slot_width - text_width) / 2, (slot_height - text_height) / 2))
            imgui.text(card_text)

            imgui.end_child()

        imgui.end()

    def _draw_action_buttons(self):
        """绘制右下角的操作按钮"""
        button_width = 100
        button_height = 40
        spacing = 15

        # 使用一个窗口容器来组织按钮，方便定位
        actions_width = (button_width * 4) + (spacing * 3)
        actions_height = button_height
        start_x = self.screen_width - actions_width - 20
        start_y = self.screen_height - actions_height - 20

        imgui.set_next_window_position(start_x, start_y)
        imgui.set_next_window_size(actions_width * 1.2, actions_height * 2)
        imgui.begin("Actions",
                    flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BACKGROUND | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE)

        if imgui.button("Call", width=button_width, height=button_height):
            print("Action: Call")

        imgui.same_line(spacing=spacing)
        if imgui.button("Raise", width=button_width, height=button_height):
            print("Action: Raise")

        imgui.same_line(spacing=spacing)
        if imgui.button("All-in", width=button_width, height=button_height):
            print("Action: All-in")

        imgui.same_line(spacing=spacing)
        if imgui.button("Fold", width=button_width, height=button_height):
            print("Action: Fold")

        imgui.end()
