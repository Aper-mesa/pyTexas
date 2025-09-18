import card  # Import the Card class for creating card instances
import config  # Import configuration with card type/rank definitions
from random import shuffle  # For shuffling the deck of cards


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