from enum import Enum, auto
from rich import print

class GameMode(Enum):
    PVP = '1'
    PVE = '2'
    AVA = '3'
    
MAX_HAND_SIZE = 7
BOARD_SIZE = 3