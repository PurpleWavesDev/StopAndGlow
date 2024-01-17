# DMX imports
from dmx import DMXInterface, DMXUniverse
import dmx.constants
from typing import List

from src.imgdata import *

DMX_MAX_ADDRESS = dmx.constants.DMX_MAX_ADDRESS
DMX_MAX_VALUE = 255

class Lights:
    def __init__(self):
        self._interface = None
        self.frame = [0] * DMX_MAX_ADDRESS

    def getInterface(self):
        if self._interface is None:
            self._interface = DMXInterface("FT232R")
        return self._interface
    
    def reset(self):
        self.frame = [0] * DMX_MAX_ADDRESS
        
    def setFrame(self, frame):
        self.frame=frame

    def setSingle(self, id, value):
        self.frame[id] = value
        
    def setList(self, list, value: int=DMX_MAX_VALUE):
        self.reset()
        for light in list:
            self.frame[light] = value

    def setLights(self, light_dict, channel=-1, exp_corr=0.5):
        for id, light in light_dict.items():
            if len(light.get().shape) == 2: # Single channel buffer
                self.frame[id] = int(light.asDomain(ImgDomain.Lin).asInt().get()[0][0]*exp_corr)
            elif channel == -1:
                self.frame[id] = int(light.RGB2Gray().asDomain(ImgDomain.Lin).asInt().get()[0][0]*exp_corr)
            else:
                self.frame[id] = int(light.asDomain(ImgDomain.Lin).asInt().get()[0][0][channel]*exp_corr)
        

    def write(self):
        # Set frame and send update
        self.getInterface().set_frame(self.frame)
        self.getInterface().send_update()

    def off(self):
        frame = [0] * DMX_MAX_ADDRESS
        self.getInterface().set_frame(frame)
        self.getInterface().send_update()