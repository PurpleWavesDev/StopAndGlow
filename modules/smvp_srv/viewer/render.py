import logging as log
import numpy as np
import math
import cv2 as cv
import taichi as ti

from ..data import *
from .viewer import *
from ..render.scene import *


class RenderViewer(Viewer):
    name = "sequence"
    
    def __init__(self):
        self.render_mode = 0
    
    def setRenderer(self, renderer):
        # Set sequence and reset to current render mode
        self.renderer = renderer

    # Render settings
    def setResolution(self, resolution):
        self.resolution = resolution
    
    def getModes(self) -> list:
        return ["Directional", "Point"]

    def setMode(self, mode):
        self.render_mode = mode
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(with_exposure=True, is_linear=True, needs_coords=True)

    def setCoords(self, u, v):
        self.renderer.reset()
        match self.render_mode:
            case 0: # Directional Light
                self.renderer.getScene().addSun(LightData(direction=[u, v], power=1000))
            case 1: # Point Light
                #self.renderer.getScene().addLight()
                pass
        self.renderer.initRender()
        self.renderer.sample()
    
    #def keypressEvent(self, event_key):
    #    seq_length = len(self.sequence) if self.render_mode == 1 else len(self.sequence.getDataSequence(self.data_keys[self.data_idx]))
    #    data_length = len(self.data_keys)
    #    
    #    if event_key in ['a']:
    #        self.idx = self.idx = (seq_length + self.idx - 1) % seq_length
    #    elif event_key in ['d']:
    #        self.idx = (self.idx + 1) % seq_length
    #    elif self.render_mode == 2 and data_length > 0:
    #        if event_key in ['s']:
    #            self.data_idx = self.data_idx = (data_length + self.data_idx - 1) % data_length
    #            self.idx = 0
    #        elif event_key in ['w']:
    #            self.data_idx = (self.data_idx + 1) % data_length
    #            self.idx = 0
    #    
    #    # Set image depending on render mode
    #    if self.render_mode == 1:
    #        self.scaled_buf = self.sequence.get(self.idx).rescale(self.resolution)
    #    elif self.render_mode == 2 and data_length > 0:
    #        self.scaled_buf = self.sequence.getDataSequence(self.data_keys[self.data_idx]).get(self.idx).rescale(self.resolution)

    # Rendering
    def render(self, buffer, time_frame):
        buffer.from_numpy(self.renderer.get()) # TODO: getBuffer and copy directly
