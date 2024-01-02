# DMX imports
from dmx import DMXInterface, DMXUniverse
import dmx.constants
from typing import List

class Lights:
    DMX_MAX_ADDRESS = dmx.constants.DMX_MAX_ADDRESS
    DMX_MAX_VALUE = 255
    
    def __init__(self):
        self.interface = DMXInterface("FT232R")
        self.frame = [0] * Lights.DMX_MAX_ADDRESS
        #universe = DMXUniverse()

    def setFrame(self, frame):
        self.frame=frame

    # TODO: Weird API
    def setList(self, list):
        self.frame = [0] * Lights.DMX_MAX_ADDRESS
        for light in list:
            self.frame[light] = Lights.DMX_MAX_VALUE


    def write(self):
        # Set frame and send update
        self.interface.set_frame(self.frame)
        self.interface.send_update()

    def off(self):
        frame = [0] * Lights.DMX_MAX_ADDRESS
        self.interface.set_frame(frame)
        self.interface.send_update()