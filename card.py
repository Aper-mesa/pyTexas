import config  # Import configuration module containing card definitions and rankings
from collections import Counter  # Used for counting occurrences of card ranks
from itertools import combinations  # Used for generating card combinations


class Card:
    """Playing card class representing a single playing card with its properties and methods"""

    def __init__(self, cardNumber, cardType):
        """Initialize a playing card instance

        Args:
            cardNumber: The numeric value/rank of the card
            cardType: The suit of the card
        """
        self.cardNumber = cardNumber  # Store the card's numeric value
        self.cardType = cardType  # Store the card's suit

    def getCardInfo(self):
        """Retrieve the card's information

        Returns:
            A tuple containing the card's number and suit
        """
        return self.cardNumber, self.cardType

    def __str__(self):
        """Return a string representation of the card
        Returns:
            str: A string representation of the card(cardNumber, cardType)
        """
        return f"{self.cardNumber}_{self.cardType}"


    @classmethod
    def createCard(cls, cardNumber, cardType):
        """Factory method to create a Card instance with validation

        Args:
            cardNumber: The numeric value/rank of the card
            cardType: The suit of the card

        Returns:
            An instance of the Card class

        Raises:
            IndexError: When the card number or type is invalid
        """
        # Validate card number
        if cardNumber not in config.CARD_NUMBER_RANK_MAP:
            raise IndexError("Invalid card number")
        # Validate card type/suit
        if cardType not in config.CARD_TYPE_MAP:
            raise IndexError("Invalid card type")
        # Create and return Card instance
        return cls(config.CARD_TYPE_MAP[cardType], cardNumber)

    @classmethod
    def getPattens(cls, cards):
        """Analyze the best possible hand from a set of cards

        Evaluates all possible 5-card combinations from the given cards
        and determines the highest ranking hand

        Args:
            cards: A list of Card instances

        Returns:
            A tuple containing the best hand name and its sorted ranks
        """
        # Initialize best hand as "High Card" (lowest ranking)
        best_hand = ("High Card", [0])

        # Generate all possible 5-card combinations
        for combo in combinations(cards, 5):
            # Extract and sort ranks in descending order
            ranks = sorted([c.rank for c in combo], reverse=True)
            # Extract suit information
            suits = [c.cardType for c in combo]
            # Get unique ranks for straight and pair checking
            unique_ranks = set(ranks)

            # Check if all cards are the same suit (flush)
            is_flush = len(set(suits)) == 1
            # Check if ranks form a sequence (straight)
            is_straight = len(unique_ranks) == 5 and max(ranks) - min(ranks) == 4

            # Special case: Ace-low straight (A-2-3-4-5)
            if {14, 2, 3, 4, 5} == unique_ranks:
                is_straight = True
                ranks = [5, 4, 3, 2, 1]  # Reorder for proper comparison

            # Count occurrences of each rank
            count = Counter(ranks)
            # Sort counts in descending order for hand ranking
            counts = sorted(count.values(), reverse=True)

            # Determine the hand ranking for current combination
            if is_flush and ranks == [14, 13, 12, 11, 10]:
                # Highest possible hand: Royal Flush
                hand = ("Royal Flush", ranks)
            elif is_flush and is_straight:
                # Straight Flush (second highest)
                hand = ("Straight Flush", ranks)
            elif counts == [4, 1]:
                # Four of a kind
                hand = ("Four of a Kind", ranks)
            elif counts == [3, 2]:
                # Full house (three of a kind plus a pair)
                hand = ("Full House", ranks)
            elif is_flush:
                # Flush (all same suit, not a straight)
                hand = ("Flush", ranks)
            elif is_straight:
                # Straight (sequence, not same suit)
                hand = ("Straight", ranks)
            elif counts == [3, 1, 1]:
                # Three of a kind
                hand = ("Three of a Kind", ranks)
            elif counts == [2, 2, 1]:
                # Two pairs
                hand = ("Two Pair", ranks)
            elif counts == [2, 1, 1, 1]:
                # One pair
                hand = ("One Pair", ranks)
            else:
                # High card (no other combination)
                hand = ("High Card", ranks)

            # Compare current hand with best hand found so far
            # First compare hand rankings, then specific card ranks if tied
            if config.HAND_RANKINGS[hand[0]] > config.HAND_RANKINGS[best_hand[0]] or (
                    config.HAND_RANKINGS[hand[0]] == config.HAND_RANKINGS[best_hand[0]] and hand[1] > best_hand[1]
            ):
                best_hand = hand

        # Return the highest ranking hand found
        return best_hand