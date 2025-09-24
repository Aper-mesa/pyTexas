import os
import config  # Import configuration module with constants
import tools  # Import utility tools module


class Player:
    """Represents a player in the game with user account information and balance"""

    def __init__(self, userName, password, ip, money=config.INIT_MONEY):
        """Initialize a Player instance

        Args:
            userName: Player's username
            password: Player's password
            money: Initial balance, defaults to value from config
        """
        self.userName = userName  # Store username
        self.password = password  # Store password
        self.money = money  # Store player's balance (in-game currency)
        self.ip = ip

    def __str__(self):
        """Return string representation of the player"""
        return self.userName

    def storeData(self):
        """Save player data to a JSON file with hashed credentials

        Stores the user's information securely by hashing username and password
        before saving to the filesystem
        """
        # Hash the username for secure storage/filenaming
        nameHash = tools.nameToHash(self.userName)
        # Hash the password for secure storage
        pwdHash = tools.pwdToHash(self.password)

        # Create full path to user's data file
        path = os.path.join(config.USER_DATA_PATH, nameHash + ".json")

        # Ensure the user data directory exists
        tools.createPathIfNotExist(config.USER_DATA_PATH)

        # Prepare data dictionary with hashed credentials and balance
        data = {
            "userName": self.userName,
            "password": pwdHash,
            "ip": self.ip,
            "money": self.money
        }

        # Save data to JSON file
        tools.setJsonData(path, data)

    @classmethod
    def create(cls, username, password, ip):
        """Factory method to create or authenticate a Player

        Creates a new player if they don't exist, or authenticates and loads
        an existing player if they do.

        Args:
            username: Player's username
            password: Player's password

        Returns:
            Player instance

        Raises:
            RuntimeError: If password is invalid for existing user
            :param ip: local ip address
        """
        # Hash username to find/create data file
        nameHash = tools.nameToHash(username)
        path = os.path.join(config.USER_DATA_PATH, nameHash + ".json")

        # Check if user already exists
        if not os.path.exists(path):
            # Create new player if no existing data
            print('Creating new player account')
            return cls(username, password, ip)
        else:
            # Load existing user data
            data = tools.getJsonData(path)
            # Hash provided password for comparison
            pwd = tools.pwdToHash(password)
            storedPwd = data["password"]
            ip = data["ip"]

            # Verify password matches stored hash
            if storedPwd != pwd:
                return False

            # Return player instance with loaded data
            # Note: Original code uses default money - might want to use data["money"] here
            return cls(username, password, ip, money=data["money"])

    def getJSONData(self):
        nameHash = tools.nameToHash(self.userName)
        path = os.path.join(config.USER_DATA_PATH, nameHash + ".json")
        data = tools.getJsonData(path)
        return data

    def setIP(self, ip):
        self.ip = ip
        self.storeData()
        print('IP address has been updated')

    def getIP(self):
        return self.ip

class PlayerInGame:
    """Represents a player who is actively participating in a game session.
    Extends the base Player class with game-specific attributes like hand cards.
    """

    def __init__(self, player, ip, bet):
        """Initialize a PlayerInGame instance from a base Player object

        Args:
            player: A Player instance containing user account information and balance
            bet: Initial balance, defaults to value from each game session
        """
        self.player = player# Reference to the base Player object (contains account/money data)
        self.ip = ip
        self.handCards = []  # List to hold the player's current cards in their hand during the game
        self.currentBet = bet