# This file is for developer testing, will be deleted when the project is finished

# import player
#
# if __name__ == '__main__':
#     p = player.Player.create("Anod", "1234")
#     print(p.userName)

import round, player
import random

players = [player.Player("A", "123"), player.Player("B", "456"), player.Player("C", "789")]
round = round.Round(players, players[0])
round.setStreet("preflop")
for player in round:
    print(player)