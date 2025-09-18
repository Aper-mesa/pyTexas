# Player configs
INIT_MONEY = 10000
USER_DATA_PATH = "./data"


# Card configs
CARD_NUMBER_RANK_MAP = {  # Ranks of the card number
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "T": 10, "J": 11,
    "Q": 12, "K": 13, "A": 14
}

CARD_TYPE_MAP = {"Spade", "Heart", "Club", "Diamond"}    # Card types

HAND_RANKINGS = {   # Pattern
    "Royal Flush": 10,
    "Straight Flush": 9,
    "Four of a Kind": 8,
    "Full House": 7,
    "Flush": 6,
    "Straight": 5,
    "Three of a Kind": 4,
    "Two Pair": 3,
    "One Pair": 2,
    "High Card": 1
}
