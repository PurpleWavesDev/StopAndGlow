# DMX imports
from dmx import DMXInterface, DMXUniverse
import dmx.constants
from typing import List

from src.imgdata import *

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

    def setLights(self, light_dict, channel=-1):
        for id, light in light_dict.items():
            if channel == -1:
                self.frame[id] = light.RGB2Gray().asDomain(ImgDomain.Lin).asInt().get()[0][0]
            else:
                self.frame[id] = light.asDomain(ImgDomain.Lin).asInt().get()[0][0][channel]
        

    def write(self):
        # Set frame and send update
        self._interface.set_frame(self.frame)
        self._interface.send_update()

    def off(self):
        frame = [0] * DMX_MAX_ADDRESS
        self._interface.set_frame(frame)
        self._interface.send_update()