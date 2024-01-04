# DMX imports
from dmx import DMXInterface, DMXUniverse
import dmx.constants
from typing import List

DMX_MAX_ADDRESS = dmx.constants.DMX_MAX_ADDRESS
DMX_MAX_VALUE = 255

class Lights:
    def __init__(self):
        self._interface = DMXInterface("FT232R")
        self.frame = [0] * DMX_MAX_ADDRESS
        #universe = DMXUniverse()
    
    def reset(self):
        self.frame = [0] * DMX_MAX_ADDRESS
        
    def setFrame(self, frame):
        self.frame=frame

    def setSingle(self, id, value):
        self.frame[id] = value
        
    def setList(self, list, value=DMX_MAX_VALUE):
        self.reset()
        for light in list:
            self.frame[light] = value

    def setDict(self, dict):
        self.reset()
        for id, val in dict:
            self.frame[id] = val
        

    def write(self):
        # Set frame and send update
        self._interface.set_frame(self.frame)
        self._interface.send_update()

    def off(self):
        frame = [0] * DMX_MAX_ADDRESS
        self._interface.set_frame(frame)
        self._interface.send_update()