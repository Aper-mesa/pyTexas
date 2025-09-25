from random import choice  # For choosing the host
from random import shuffle  # For shuffling the deck of cards

import card  # Import the Card class for creating card instances
import config  # Import configuration with card type/rank definitions
import player  # Import the two player class for creating player instances
import pygame as g
from pygame_networking import Server

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
    def __init__(self, screen, data):
        self.screen = screen
        self.players = data[0]  # 房间中的所有人，从房主创房那边直接传递过来
        self.activePlayers = self.players  # 在打牌的人，弃牌了就不在这了，初始和players一样
        self.numPlayers = len(self.players)  # Total number of players in the room
        self.minBet = data[1]  # Minimum initial bet required
        self.initBet = data[2]
        self.banker = choice(self.players)  # 首次随机选一个作为庄家
        self.order = Round(self.players, self.banker)  # Manages turn order for the round
        self.betPool = 0  # Total accumulated bets in the current round
        print(self.initBet)

    def chipIn(self, player, bet):
        """Process a player's bet and add it to the pool

        Args:
            player: Player instance placing the bet
            bet: Amount the player wants to bet

        Returns:
            bool: True if bet is successful, False if insufficient funds
        """
        playerInGame = self.activePlayers[player]  # Get player's in-game state

        # Check if player has enough remaining bet capacity
        if playerInGame.currentBet < bet:
            return False

        # Deduct bet from player's available amount and add to pool
        playerInGame.currentBet -= bet
        self.betPool += bet
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

    def run(self):
        return None, None