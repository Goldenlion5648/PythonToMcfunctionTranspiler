import itertools as it
import os
import sys
sys.path.insert(0, r'C:\Users\cobou\Documents\Curse\Minecraft\Instances\CommandCreations1_19_2\python_helpers')
from helper_functions import *
import helper_functions
setup = OutputFile("setup")
helper_update = OutputFile("update")
helper_functions.UPDATE_JSON_FILE = f"{os.path.dirname(__file__)}\\..\\..\\..\\minecraft\\tags\\functions\\tick.json"

class Tags(Enum):
    # CARD_OUTLINE_TAG = "card_outline"

    def __str__(self):
        return str(self.value)