# DMX imports
from dmx import DMXInterface, DMXUniverse
from dmx.constants import DMX_MAX_ADDRESS
from typing import List

class Lights:
    def __init__(self):
        self.interface = DMXInterface("FT232R")
        self.frame = [0] * DMX_MAX_ADDRESS
        #universe = DMXUniverse()

    # TODO: Weird API
    def setList(self, list):
        self.frame = [0] * DMX_MAX_ADDRESS
        for light in list:
            self.frame[light] = 255


    def write(self):
        # Set frame and send update
        self.interface.set_frame(self.frame)
        self.interface.send_update()