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
        self.setMode(0)
    
    def setRenderer(self, renderer):
        # Set sequence and reset to current render mode
        self.renderer = renderer

    # Render settings
    def setResolution(self, resolution):
        self.resolution = resolution
    
    def getModes(self) -> list:
        return ["Directional", "Point", "HDRI"]

    def setMode(self, mode):
        self.render_mode = mode
        self.u = None
        self.v = None
        self.y_pos = -0.3
        self.y_changed = True
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(with_exposure=True, is_linear=True, needs_coords=True, req_inputs=True if mode == 1 else False)

    def setCoords(self, u, v):
        # Only reset render if coordinates have changed
        if u != self.u or v != self.v or self.y_changed:
            self.u = u
            self.v = v
            self.y_changed = False
            self.renderer.reset()
            
            match self.render_mode:
                case 0: # Directional Light
                    # Range -1 to +1
                    if u > 1:
                        u = 1 - u%1
                        v += 1
                    elif u < -1:
                        u = -(u%1)
                        v += 1
                    v -= math.floor(v) * 2 if v > 0 else math.ceil(v) * 2
                    if self.renderer.getBsdfCoordSys() == CoordSys.ZVec:
                        u, v = LightPosition.FromLatLong([u, v], True).getZVecNorm()
                    self.renderer.getScene().addSun(LightData(direction=[u, v], power=10))
                case 1: # Point Light
                    self.renderer.getScene().addPoint(LightData(position=[v*0.5, self.y_pos, u*0.5 * 9/16], power=100))
                case 2: # HDRI
                    self.renderer.getScene().setHdriData(rotation=v*0.5+1, power=200)
                    
            self.renderer.initRender(hdri_samples=500 if self.render_mode==2 else 0)
            
    def inputs(self, window, time_frame):
        if window.is_pressed('w'):
            self.y_pos += 0.3 * time_frame
            self.y_changed = True
        elif window.is_pressed('s'):
            self.y_pos -= 0.3 * time_frame
            self.y_changed = True

    # Rendering
    def render(self, buffer, time_frame):
        self.renderer.sample()
        tib.copyToPixarr(buffer, self.renderer.getBuffer()) # TODO: Pass buffer to renderer instead of copying multiple times
