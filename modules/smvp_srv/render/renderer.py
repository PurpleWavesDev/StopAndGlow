from enum import Enum
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib

from ..data import Sequence
from ..hw import Calibration

from .scene import *
from .bsdf import *

pi_by_2 = np.pi/2
pi_times_2 = np.pi*2

@ti.data_oriented
class Renderer:
    def __init__(self, bsdf=BSDF(), resolution=[1920, 1080]):
        self._bsdf = bsdf
        self._scene = Scene()
        self._buffer = ti.field(tib.pixvec)
        ti.root.dense(ti.ij, (resolution[1], resolution[0])).place(self._buffer)
        
    def getScene(self):
        return self._scene

    ## Rendering    
    def initRender(self, samples=10):  
        # Reset buffer
        self._buffer.fill(0.0)
    
    def reset(self):
        self._scene.clear()
    
    def sample(self) -> bool:
        for lgt in self._scene.getSunLights():
            u, v = 0.5, 0.5
            if len(lgt.direction) == 3:
                u = math.asin(lgt.direction[2]) / np.pi + 0.5
                xy_length = math.sqrt(lgt.direction[0]**2 + lgt.direction[1]**2)
                if xy_length > 0:
                    v = math.acos(lgt.direction[1]/xy_length)/pi_times_2 if lgt.direction[0] < 0 else 1-math.acos(lgt.direction[1]/xy_length)/pi_times_2
            else:
                u, v = lgt.direction
            self.sampleSun(u, v, lgt.spread, lgt.power, lgt.color)
        
        for lgt in self._scene.getPointLights():
            self.samplePoint(lgt.position, lgt.size, lgt.power, lgt.color)
        
        for lgt in self._scene.getSpotLights():
            self.sampleSpot()
        
        for lgt in self._scene.getAreaLights():
            self.sampleArea()
            
        self.sampleHdri()
    
    def get(self):
        return self._buffer.to_numpy()
    
    def getBuffer(self):
        return self._buffer

    ## Sample kernels
    @ti.kernel
    def sampleSun(self, u: ti.f32, v: ti.f32, spread: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        
        for y, x in self._buffer:
            self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor
    
    @ti.kernel
    def samplePoint(self, pos: tib.pixvec, size: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        width = self._buffer.shape[0]
        height_offset = 0.5 # TODO!
        
        for y, x in self._buffer:
            # Calculate vector to pixel: We assume the canvas is 1m wide and centered
            # Canvas is flat for now
            pix2pos = pos - ti.Vector([x/width - 0.5, 0, y/width - height_offset], dt=ti.f32)
            squared_length = pos[0]**2 + pos[1]**2 + pos[2]**2
            dir = tm.normalize(pix2pos)
            # Calculate angle
            u = tm.asin(dir[2]) / tm.pi + 0.5
            v = 0.5
            xy_length = tm.sqrt(dir[0]**2 + dir[1]**2)
            if xy_length > 0:
                v = tm.acos(dir[1]/xy_length)/pi_times_2 if dir[0] < 0 else 1-tm.acos(dir[1]/xy_length)/pi_times_2
            self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor * 1/squared_length
    
    @ti.kernel
    def sampleSpot(self):
        pass
    
    @ti.kernel
    def sampleArea(self):
        pass
    
    @ti.kernel
    def sampleHdri(self):
        pass
