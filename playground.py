# This file is for developer testing, will be deleted when the project is finished
import pygame
import pygame_gui as gui
from round import Room, PlayScreen
# import player
#
# if __name__ == '__main__':
#     p = player.Player.create("Anod", "1234")
#     print(p.userName)

# import round, player
# import random
#
# players = [player.Player("A", "123"), player.Player("B", "456"), player.Player("C", "789")]
# round = round.Round(players, players[0])
# round.setStreet("preflop")
# for player in round:
#     print(player)

pygame.init()

screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
manager = gui.UIManager((screen.get_size()), starting_language='zh', theme_path='themes/in_game_theme.json',
                        translation_directory_paths=['languages'])

ui = PlayScreen(screen, manager)

